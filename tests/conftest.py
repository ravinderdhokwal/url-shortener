import os

# Must be set before importing application modules. pydantic-settings prefers
# process env over `.env`, so this keeps tests off the developer's Postgres URL.
os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"
os.environ.setdefault("ENVIRONMENT", "test")

from collections.abc import AsyncIterator
from datetime import timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from url_shortener.app import create_app
from url_shortener.db.base import Base
from url_shortener.db.session import get_db
from url_shortener.models import URLModel


@event.listens_for(URLModel, "load")
def _sqlite_restore_expires_at_tzinfo(target, _context):
    """SQLite drops tzinfo; Postgres TIMESTAMPTZ does not. Re-attach UTC for tests."""
    expires_at = target.expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        target.expires_at = expires_at.replace(tzinfo=timezone.utc)

@pytest.fixture
async def engine():
    test_engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield test_engine
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest.fixture
def session_factory(engine):
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest.fixture
async def db_session(session_factory) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


@pytest.fixture
async def client(session_factory) -> AsyncIterator[AsyncClient]:
    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
