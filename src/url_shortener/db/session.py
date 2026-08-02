from curses import echo
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from url_shortener.core.config import settings

async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo = settings.IS_DEV_ENV
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session