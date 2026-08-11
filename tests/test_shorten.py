from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.db import repository as db
from app.cache.redis_cache import url_cache
from app.models.schemas import ShortenRequest
from app.services import url_service

API_KEY = {"id": 1, "key": "sk_live_test", "rate_limit_per_minute": 60, "is_active": True}


@pytest.fixture(autouse=True)
def patch_cache(monkeypatch):
    monkeypatch.setattr(url_cache, "set_url", AsyncMock())
    monkeypatch.setattr(url_cache, "delete_url", AsyncMock())


async def test_rejects_invalid_url():
    body = ShortenRequest(url="not-a-url")
    with pytest.raises(HTTPException) as exc:
        await url_service.create_short_url(body, API_KEY)
    assert exc.value.status_code == 400


async def test_generates_base62_code_for_new_url(monkeypatch):
    monkeypatch.setattr(db, "next_url_id", AsyncMock(return_value=238328))
    insert_mock = AsyncMock()
    monkeypatch.setattr(db, "insert_url_with_id", insert_mock)

    body = ShortenRequest(url="https://example.com")
    result = await url_service.create_short_url(body, API_KEY)

    assert result.code == "baaa"
    assert result.short_url.endswith("/baaa")
    insert_mock.assert_awaited_once()


async def test_custom_alias_success(monkeypatch):
    monkeypatch.setattr(db, "get_url_by_code", AsyncMock(return_value=None))
    insert_mock = AsyncMock()
    monkeypatch.setattr(db, "insert_url", insert_mock)

    body = ShortenRequest(url="https://example.com", custom_alias="my-link")
    result = await url_service.create_short_url(body, API_KEY)

    assert result.code == "my-link"
    insert_mock.assert_awaited_once()


async def test_custom_alias_already_taken(monkeypatch):
    monkeypatch.setattr(db, "get_url_by_code", AsyncMock(return_value={"code": "my-link"}))

    body = ShortenRequest(url="https://example.com", custom_alias="my-link")
    with pytest.raises(HTTPException) as exc:
        await url_service.create_short_url(body, API_KEY)
    assert exc.value.status_code == 409


async def test_custom_alias_rejects_bad_format():
    body = ShortenRequest(url="https://example.com", custom_alias="a!")
    with pytest.raises(HTTPException) as exc:
        await url_service.create_short_url(body, API_KEY)
    assert exc.value.status_code == 400


async def test_expires_in_hours_sets_expiry(monkeypatch):
    monkeypatch.setattr(db, "next_url_id", AsyncMock(return_value=238328))
    monkeypatch.setattr(db, "insert_url_with_id", AsyncMock())

    body = ShortenRequest(url="https://example.com", expires_in_hours=1)
    result = await url_service.create_short_url(body, API_KEY)

    assert result.expires_at is not None
