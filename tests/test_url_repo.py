from datetime import datetime, timezone

import pytest

from url_shortener.models import URLModel
from url_shortener.repos import url_repo
from url_shortener.schemas.url_schema import URLRequestSchema


@pytest.mark.asyncio
async def test_save_and_fetch_by_short_code(db_session):
    saved = await url_repo.save_url(
        db_session,
        URLRequestSchema(original_url="https://example.com/alpha"),
        "abc1234",
    )
    await db_session.commit()

    found = await url_repo.fetch_original_url_using_short_code(db_session, "abc1234")
    assert found is not None
    assert found.id == saved.id
    assert found.original_url == "https://example.com/alpha"
    assert found.is_active is True
    assert found.expires_at is None


@pytest.mark.asyncio
async def test_check_original_url_existence(db_session):
    await url_repo.save_url(
        db_session,
        URLRequestSchema(original_url="https://example.com/exists"),
        "exist01",
    )
    await db_session.commit()

    hit = await url_repo.check_original_url_existence(
        db_session, "https://example.com/exists"
    )
    miss = await url_repo.check_original_url_existence(
        db_session, "https://example.com/missing"
    )
    assert hit is not None
    assert hit.short_code == "exist01"
    assert miss is None


@pytest.mark.asyncio
async def test_fetch_all_urls_from_db(db_session):
    assert await url_repo.fetch_all_urls_from_db(db_session) == []

    await url_repo.save_url(
        db_session,
        URLRequestSchema(original_url="https://example.com/one"),
        "one0001",
    )
    await url_repo.save_url(
        db_session,
        URLRequestSchema(original_url="https://example.com/two"),
        "two0002",
    )
    await db_session.commit()

    rows = await url_repo.fetch_all_urls_from_db(db_session)
    codes = {row.short_code for row in rows}
    assert codes == {"one0001", "two0002"}


@pytest.mark.asyncio
async def test_save_url_persists_inactive_and_expiry_defaults(db_session):
    db_session.add(
        URLModel(
            short_code="inact01",
            original_url="https://example.com/inactive",
            is_active=False,
            expires_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
        )
    )
    await db_session.commit()

    row = await url_repo.fetch_original_url_using_short_code(db_session, "inact01")
    assert row is not None
    assert row.is_active is False
    assert row.expires_at is not None
