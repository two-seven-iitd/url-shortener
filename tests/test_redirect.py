from datetime import datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.cache.redis_cache import url_cache
from app.db import repository as db
from app.services import url_service


async def test_cache_hit_never_touches_db(monkeypatch):
    monkeypatch.setattr(url_cache, "get_url", AsyncMock(return_value="https://example.com"))
    db_mock = AsyncMock()
    monkeypatch.setattr(db, "get_url_by_code", db_mock)

    result = await url_service.resolve_code("abcd")

    assert result == "https://example.com"
    db_mock.assert_not_awaited()


async def test_cache_miss_falls_back_to_db_and_repopulates_cache(monkeypatch):
    monkeypatch.setattr(url_cache, "get_url", AsyncMock(return_value=None))
    set_mock = AsyncMock()
    monkeypatch.setattr(url_cache, "set_url", set_mock)
    monkeypatch.setattr(
        db,
        "get_url_by_code",
        AsyncMock(return_value={
            "original_url": "https://example.com",
            "expires_at": None,
            "is_active": True,
        }),
    )

    result = await url_service.resolve_code("abcd")

    assert result == "https://example.com"
    set_mock.assert_awaited_once_with("abcd", "https://example.com", ttl=86400)


async def test_unknown_code_returns_404(monkeypatch):
    monkeypatch.setattr(url_cache, "get_url", AsyncMock(return_value=None))
    monkeypatch.setattr(db, "get_url_by_code", AsyncMock(return_value=None))

    with pytest.raises(HTTPException) as exc:
        await url_service.resolve_code("nope")
    assert exc.value.status_code == 404


async def test_expired_url_returns_410(monkeypatch):
    monkeypatch.setattr(url_cache, "get_url", AsyncMock(return_value=None))
    monkeypatch.setattr(
        db,
        "get_url_by_code",
        AsyncMock(return_value={
            "original_url": "https://example.com",
            "expires_at": datetime.now() - timedelta(hours=1),
            "is_active": True,
        }),
    )

    with pytest.raises(HTTPException) as exc:
        await url_service.resolve_code("abcd")
    assert exc.value.status_code == 410


async def test_deactivated_url_returns_410(monkeypatch):
    monkeypatch.setattr(url_cache, "get_url", AsyncMock(return_value=None))
    monkeypatch.setattr(
        db,
        "get_url_by_code",
        AsyncMock(return_value={
            "original_url": "https://example.com",
            "expires_at": None,
            "is_active": False,
        }),
    )

    with pytest.raises(HTTPException) as exc:
        await url_service.resolve_code("abcd")
    assert exc.value.status_code == 410
