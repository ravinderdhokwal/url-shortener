from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from url_shortener.core.exceptions import (
    ConflictError,
    InternalServerError,
    NotFoundError,
    ResourceInactiveError,
)
from url_shortener.models import URLModel
from url_shortener.schemas.url_schema import URLRequestSchema
from url_shortener.services import url_service
from url_shortener.utils.message_utils import Messages


def _url(
    *,
    original_url: str = "https://example.com/path",
    short_code: str = "abc1234",
    is_active: bool = True,
    expires_at: datetime | None = None,
) -> URLModel:
    return URLModel(
        short_code=short_code,
        original_url=original_url,
        is_active=is_active,
        expires_at=expires_at,
    )


@pytest.mark.asyncio
async def test_fetch_all_url_returns_rows():
    rows = [_url()]
    with patch(
        "url_shortener.services.url_service.url_repo.fetch_all_urls_from_db",
        new=AsyncMock(return_value=rows),
    ):
        result = await url_service.fetch_all_url(MagicMock())
    assert result == rows


@pytest.mark.asyncio
async def test_fetch_all_url_raises_when_empty():
    with patch(
        "url_shortener.services.url_service.url_repo.fetch_all_urls_from_db",
        new=AsyncMock(return_value=[]),
    ):
        with pytest.raises(NotFoundError) as exc:
            await url_service.fetch_all_url(MagicMock())
    assert exc.value.message == Messages.NO_SHORT_URL_IN_DB
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_resolve_original_url_success():
    row = _url()
    with patch(
        "url_shortener.services.url_service.url_repo.fetch_original_url_using_short_code",
        new=AsyncMock(return_value=row),
    ):
        result = await url_service.resolve_original_url(MagicMock(), "abc1234")
    assert result == row.original_url


@pytest.mark.asyncio
async def test_resolve_original_url_missing():
    with patch(
        "url_shortener.services.url_service.url_repo.fetch_original_url_using_short_code",
        new=AsyncMock(return_value=None),
    ):
        with pytest.raises(NotFoundError) as exc:
            await url_service.resolve_original_url(MagicMock(), "missing")
    assert exc.value.message == Messages.NO_SHORT_CODE


@pytest.mark.asyncio
async def test_resolve_original_url_inactive():
    with patch(
        "url_shortener.services.url_service.url_repo.fetch_original_url_using_short_code",
        new=AsyncMock(return_value=_url(is_active=False)),
    ):
        with pytest.raises(ResourceInactiveError) as exc:
            await url_service.resolve_original_url(MagicMock(), "abc1234")
    assert exc.value.message == Messages.SHORT_URL_INACTIVE
    assert exc.value.status_code == 410


@pytest.mark.asyncio
async def test_resolve_original_url_expired():
    expired = datetime.now(timezone.utc) - timedelta(hours=1)
    with patch(
        "url_shortener.services.url_service.url_repo.fetch_original_url_using_short_code",
        new=AsyncMock(return_value=_url(expires_at=expired)),
    ):
        with pytest.raises(ResourceInactiveError) as exc:
            await url_service.resolve_original_url(MagicMock(), "abc1234")
    assert exc.value.message == Messages.SHORT_URL_EXPIRED


@pytest.mark.asyncio
async def test_resolve_original_url_future_expiry_is_allowed():
    future = datetime.now(timezone.utc) + timedelta(days=1)
    row = _url(expires_at=future)
    with patch(
        "url_shortener.services.url_service.url_repo.fetch_original_url_using_short_code",
        new=AsyncMock(return_value=row),
    ):
        result = await url_service.resolve_original_url(MagicMock(), "abc1234")
    assert result == row.original_url


@pytest.mark.asyncio
async def test_generate_short_url_creates_when_original_is_new():
    created = _url()
    db = MagicMock()
    db.rollback = AsyncMock()
    with (
        patch(
            "url_shortener.services.url_service.url_repo.check_original_url_existence",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "url_shortener.services.url_service.generate_short_code",
            return_value="newcode",
        ),
        patch(
            "url_shortener.services.url_service.url_repo.save_url",
            new=AsyncMock(return_value=created),
        ) as save,
    ):
        result = await url_service.generate_short_url(
            db, URLRequestSchema(original_url="https://example.com/path")
        )
    assert result is created
    save.assert_awaited_once()
    db.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_generate_short_url_conflict_when_original_exists():
    existing = _url()
    with patch(
        "url_shortener.services.url_service.url_repo.check_original_url_existence",
        new=AsyncMock(return_value=existing),
    ):
        with pytest.raises(ConflictError) as exc:
            await url_service.generate_short_url(
                MagicMock(),
                URLRequestSchema(original_url=existing.original_url),
            )
    assert exc.value.status_code == 409
    assert exc.value.message == Messages.SHORT_URL_ALREADY_EXISTS
    assert exc.value.data["short_code"] == existing.short_code
    assert exc.value.data["original_url"] == existing.original_url


@pytest.mark.asyncio
async def test_generate_short_url_retries_after_collision():
    created = _url(short_code="second1")
    db = MagicMock()
    db.rollback = AsyncMock()
    save = AsyncMock(side_effect=[Exception("unique violation"), created])
    with (
        patch(
            "url_shortener.services.url_service.url_repo.check_original_url_existence",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "url_shortener.services.url_service.generate_short_code",
            side_effect=["first01", "second1"],
        ),
        patch(
            "url_shortener.services.url_service.url_repo.save_url",
            new=save,
        ),
    ):
        result = await url_service.generate_short_url(
            db, URLRequestSchema(original_url="https://example.com/path")
        )
    assert result is created
    assert save.await_count == 2
    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_short_url_raises_after_retry_budget():
    db = MagicMock()
    db.rollback = AsyncMock()
    retries = url_service._MAX_GENERATION_RETRIES
    with (
        patch(
            "url_shortener.services.url_service.url_repo.check_original_url_existence",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "url_shortener.services.url_service.generate_short_code",
            return_value="collide",
        ),
        patch(
            "url_shortener.services.url_service.url_repo.save_url",
            new=AsyncMock(side_effect=Exception("unique violation")),
        ),
    ):
        with pytest.raises(InternalServerError) as exc:
            await url_service.generate_short_url(
                db, URLRequestSchema(original_url="https://example.com/path")
            )
    assert exc.value.message == Messages.COULD_NOT_GENERATE_SHORT_URL
    assert exc.value.status_code == 500
    assert db.rollback.await_count == retries
