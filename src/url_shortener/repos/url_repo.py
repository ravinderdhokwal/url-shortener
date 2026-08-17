from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from url_shortener.models import URLModel
from url_shortener.schemas.url_schema import URLCreate


async def fetch_all_urls_from_db(db: AsyncSession) -> List[URLModel]:
    result = await db.execute(select(URLModel))
    return list(result.scalars().all())

async def save_url(db: AsyncSession, url_in: URLCreate, short_code: str) -> URLModel:
    """
    Insert a new URL row with the given short_code.

    Deliberately takes `short_code` as an explicit parameter rather than
    generating it here. This keeps the repo a thin, single-purpose data
    access layer: it knows how to talk to Postgres, nothing about how
    codes are generated or what to do if one collides. That decision
    belongs one layer up, in the service.

    IMPORTANT: this function does NOT catch IntegrityError. If short_code
    collides with an existing row, the unique constraint on
    `urls.short_code` will cause asyncpg to raise, which SQLAlchemy wraps
    as sqlalchemy.exc.IntegrityError. We deliberately let it propagate —
    catching it here would hide the failure from the retry loop in the
    service layer that needs to know "insert failed, try a new code."
    """
    url_object = URLModel(
        short_code = short_code,
        original_url = url_in.original_url,
    )

    db.add(url_object)
    await db.flush()
    # refresh() re-fetches DB-generated fields (id, created_at, etc.)
    # so the returned object matches exactly what's now in the row.
    await db.refresh(url_object)

    return url_object