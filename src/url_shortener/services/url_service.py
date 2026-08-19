from datetime import datetime, timezone
import logging
from typing import List
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from url_shortener.core.config import settings
from url_shortener.core.exceptions import ConflictError, InternalServerError, NotFoundError, ResourceInactiveError
from url_shortener.models import URLModel
from url_shortener.repos import url_repo
from url_shortener.schemas.url_schema import URLRequestSchema, URLResponseSchema
from url_shortener.utils.message_utils import Messages
from url_shortener.utils.short_code_utils import generate_short_code

logger = logging.getLogger()

_MAX_GENERATION_RETRIES = settings.MAX_SHORT_CODE_GENERATION_ATTEMPTS

async def fetch_all_url(db: AsyncSession) -> List[URLModel]:
    all_url_objects = await url_repo.fetch_all_urls_from_db(db)
    if not all_url_objects:
        raise NotFoundError(Messages.NO_SHORT_URL_IN_DB)
    
    return all_url_objects

async def resolve_original_url(db: AsyncSession, short_code: str) -> str:
    url_object = await url_repo.fetch_original_url_using_short_code(db, short_code)

    if not url_object:
        raise NotFoundError(Messages.NO_SHORT_CODE)
    
    if not url_object.is_active:
        raise ResourceInactiveError(Messages.SHORT_URL_INACTIVE)
    
    if url_object.expires_at and url_object.expires_at < datetime.now(timezone.utc):
        raise ResourceInactiveError(Messages.SHORT_URL_EXPIRED)
    
    return url_object.original_url

async def generate_short_url(db: AsyncSession, url_in: URLRequestSchema) -> URLModel:

    short_url_already_exists = await url_repo.check_original_url_existence(db, url_in.original_url)
    if short_url_already_exists:
        raise ConflictError(
            Messages.SHORT_URL_ALREADY_EXISTS,
            data=URLResponseSchema.model_validate(short_url_already_exists).model_dump()
        )

    for attempt in range(_MAX_GENERATION_RETRIES):
        candidate_short_code = generate_short_code()

        try:
            return await url_repo.save_url(db, url_in, candidate_short_code)
        
        except:
            await db.rollback()
            logger.warning(
                "Short code collision on attempt %d/%d (code=%s)",
                attempt,
                _MAX_GENERATION_RETRIES,
                candidate_short_code
            )

    # We exhausted all retries. At our measured collision rate (~14 per
    # 10M inserts, i.e. ~0.00014%), hitting 3 collisions in a row for the
    # same request is astronomically unlikely — if we get here, something
    # is probably structurally wrong (e.g. DB issue), not just bad luck.

    logger.error("Failed to generate a unique short code after %d attempts", _MAX_GENERATION_RETRIES)

    raise InternalServerError(Messages.COULD_NOT_GENERATE_SHORT_URL)