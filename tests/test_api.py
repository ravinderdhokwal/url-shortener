from datetime import datetime, timedelta, timezone

import pytest

from url_shortener.core.config import settings
from url_shortener.models import URLModel
from url_shortener.utils.message_utils import Messages


async def _create_url(client, original_url: str = "https://example.com/very/long/path"):
    response = await client.post(
        f"{settings.API_VERSION_PREFIX}/url",
        json={"original_url": original_url},
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_health_ok(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}


@pytest.mark.asyncio
async def test_create_short_url(client):
    body = await _create_url(client)
    assert body["original_url"] == "https://example.com/very/long/path"
    assert body["is_active"] is True
    assert isinstance(body["short_code"], str)
    assert len(body["short_code"]) == settings.DEFAULT_SHORT_CODE_LENGTH


@pytest.mark.asyncio
async def test_create_short_url_rejects_short_original(client):
    response = await client.post(
        f"{settings.API_VERSION_PREFIX}/url",
        json={"original_url": "short"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_short_url_conflict(client):
    first = await _create_url(client, "https://example.com/duplicate")
    response = await client.post(
        f"{settings.API_VERSION_PREFIX}/url",
        json={"original_url": "https://example.com/duplicate"},
    )
    assert response.status_code == 409
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"] == "ConflictError"
    assert payload["message"] == Messages.SHORT_URL_ALREADY_EXISTS
    assert payload["data"]["short_code"] == first["short_code"]
    assert payload["data"]["original_url"] == first["original_url"]


@pytest.mark.asyncio
async def test_list_urls_empty(client):
    response = await client.get(f"{settings.API_VERSION_PREFIX}/url")
    assert response.status_code == 404
    payload = response.json()
    assert payload["error"] == "NotFoundError"
    assert payload["message"] == Messages.NO_SHORT_URL_IN_DB


@pytest.mark.asyncio
async def test_list_urls(client):
    created = await _create_url(client, "https://example.com/listed")
    response = await client.get(f"{settings.API_VERSION_PREFIX}/url")
    assert response.status_code == 200
    rows = response.json()
    assert any(row["short_code"] == created["short_code"] for row in rows)


@pytest.mark.asyncio
async def test_redirect_found(client):
    created = await _create_url(client, "https://example.com/destination")
    response = await client.get(
        f"/{created['short_code']}",
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com/destination"


@pytest.mark.asyncio
async def test_redirect_unknown_short_code(client):
    response = await client.get("/noSuch1", follow_redirects=False)
    assert response.status_code == 404
    payload = response.json()
    assert payload["error"] == "NotFoundError"
    assert payload["message"] == Messages.NO_SHORT_CODE


@pytest.mark.asyncio
async def test_redirect_inactive(client, session_factory):
    async with session_factory() as session:
        session.add(
            URLModel(
                short_code="deadurl",
                original_url="https://example.com/inactive",
                is_active=False,
            )
        )
        await session.commit()

    response = await client.get("/deadurl", follow_redirects=False)
    assert response.status_code == 410
    payload = response.json()
    assert payload["error"] == "ResourceInactiveError"
    assert payload["message"] == Messages.SHORT_URL_INACTIVE


@pytest.mark.asyncio
async def test_redirect_expired(client, session_factory):
    async with session_factory() as session:
        session.add(
            URLModel(
                short_code="oldcode",
                original_url="https://example.com/expired",
                expires_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            )
        )
        await session.commit()

    response = await client.get("/oldcode", follow_redirects=False)
    assert response.status_code == 410
    payload = response.json()
    assert payload["error"] == "ResourceInactiveError"
    assert payload["message"] == Messages.SHORT_URL_EXPIRED
