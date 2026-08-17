import logging
from typing import List
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from url_shortener.core.config import settings
from url_shortener.models import URLModel
from url_shortener.repos import url_repo
from url_shortener.schemas.url_schema import URLCreate
from url_shortener.utils.short_code_utils import short_code_generator

logger = logging.getLogger()

MAX_GENERATION_RETRIES = settings.MAX_SHORT_CODE_GENERATION_ATTEMPTS

async def fetch_all_url(db: AsyncSession) -> List[URLModel]:
    try:
        return await url_repo.fetch_all_urls_from_db(db)
    except Exception as exc:
        logger.error("FETCHING FAILED", exc_info=exc)

async def generate_short_url(db: AsyncSession, url_in: URLCreate) -> URLModel:
    """
    Generate a unique short code and persist the URL.

    This is the "insert, and if it collides, retry with a new random
    code" pattern — the core of Approach A.

    Why we don't pre-check with a SELECT before inserting:
    Suppose we did `SELECT ... WHERE short_code = X` first, saw no row,
    and only then inserted. Between the SELECT and the INSERT, a
    *different concurrent request* could insert the same code. Now
    both requests believe the code is free, and one of them will hit a
    constraint violation anyway — except now we've done an extra
    round-trip for nothing, and we still need this exact retry logic
    to handle the failure. The unique constraint at the DB level is the
    only thing that can *atomically* guarantee no two rows share a
    short_code, because Postgres serializes the actual write. So the
    right approach is: attempt the insert, let Postgres be the single
    source of truth on collision, and catch the specific error it
    raises when a collision occurs.
    """

    last_exception: IntegrityError | None = None

    for attempt in range(MAX_GENERATION_RETRIES):
        candidate_short_code = short_code_generator()

        try:
            return await url_repo.save_url(db, url_in, candidate_short_code)
        
        except IntegrityError as e:
            # A collision on short_code raised this. Roll back the failed
            # transaction so the AsyncSession is usable again — after a
            # failed commit, the session sits in an "aborted transaction"
            # state until explicitly rolled back. Without this, the next
            # attempt's db.add()/commit() would immediately fail too,
            # for an unrelated reason (session state, not a new collision).
            await db.rollback()
            last_exception = e

            logger.warning(
                "Short code collision on attempt %d/%d (code=%s)",
                attempt,
                MAX_GENERATION_RETRIES,
                candidate_short_code,
            )
            # loop continues -> generate a fresh random candidate and retry

    # We exhausted all retries. At our measured collision rate (~14 per
    # 10M inserts, i.e. ~0.00014%), hitting 3 collisions in a row for the
    # same request is astronomically unlikely — if we get here, something
    # is probably structurally wrong (e.g. DB issue), not just bad luck.

    logger.error(
        "Failed to generate a unique short code after %d attempts",
        MAX_GENERATION_RETRIES,
    )

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Could not generate a unique short code, please try again.",
    ) from last_exception