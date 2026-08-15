from sqlalchemy.ext.asyncio import AsyncSession

from url_shortener.models import URLModel
from url_shortener.schemas.url_schema import URLCreate


async def create_short_code(db: AsyncSession, url_in: URLCreate):
    url_object = URLModel(
        original_url = url_in.original_url
    )

    db.add(url_object)
    await db.commit()