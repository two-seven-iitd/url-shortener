from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.db import repository as db
from app.services import analytics_service


URL_RECORD = {
    "id": 42,
    "original_url": "https://example.com",
    "created_at": datetime(2026, 1, 1),
    "expires_at": None,
}


def _patch_analytics_queries(monkeypatch):
    monkeypatch.setattr(db, "get_url_by_code", AsyncMock(return_value=URL_RECORD))
    monkeypatch.setattr(db, "count_clicks", AsyncMock(return_value=5))
    monkeypatch.setattr(db, "clicks_by_day", AsyncMock(return_value=[{"date": "2026-01-01", "count": 5}]))
    monkeypatch.setattr(db, "clicks_by_country", AsyncMock(return_value=[{"country": "IN", "count": 5}]))
    monkeypatch.setattr(db, "clicks_by_device", AsyncMock(return_value={"desktop": 5}))
    monkeypatch.setattr(db, "clicks_by_browser", AsyncMock(return_value={"Chrome": 5}))
    monkeypatch.setattr(db, "clicks_by_os", AsyncMock(return_value={"Windows": 5}))
    monkeypatch.setattr(db, "top_referrers", AsyncMock(return_value=[{"referrer": "Direct", "count": 5}]))
    monkeypatch.setattr(db, "clicks_by_hour", AsyncMock(return_value=[{"hour": 14, "count": 5}]))


async def test_get_url_analytics_aggregates_all_fields(monkeypatch):
    _patch_analytics_queries(monkeypatch)

    result = await analytics_service.get_url_analytics("abcd", days=30)

    assert result.code == "abcd"
    assert result.total_clicks == 5
    assert result.clicks_by_day == [{"date": "2026-01-01", "count": 5}]
    assert result.clicks_by_country == [{"country": "IN", "count": 5}]
    assert result.clicks_by_device == {"desktop": 5}
    assert result.clicks_by_browser == {"Chrome": 5}
    assert result.clicks_by_os == {"Windows": 5}
    assert result.top_referrers == [{"referrer": "Direct", "count": 5}]
    assert result.clicks_by_hour == [{"hour": 14, "count": 5}]


async def test_get_url_analytics_unknown_code_raises_404(monkeypatch):
    monkeypatch.setattr(db, "get_url_by_code", AsyncMock(return_value=None))

    with pytest.raises(HTTPException) as exc:
        await analytics_service.get_url_analytics("nope")
    assert exc.value.status_code == 404


async def test_log_click_never_raises_on_failure(monkeypatch):
    monkeypatch.setattr(db, "get_url_by_code", AsyncMock(side_effect=RuntimeError("db down")))

    class FakeRequest:
        client = type("C", (), {"host": "1.2.3.4"})()
        headers = {"user-agent": "test-agent"}

    # Should swallow the error rather than propagating it.
    await analytics_service.log_click("abcd", FakeRequest())


async def test_log_click_records_device_and_geo(monkeypatch):
    monkeypatch.setattr(db, "get_url_by_code", AsyncMock(return_value=URL_RECORD))
    insert_mock = AsyncMock()
    monkeypatch.setattr(db, "insert_click", insert_mock)
    monkeypatch.setattr(db, "increment_click_count", AsyncMock())
    monkeypatch.setattr(analytics_service.url_cache, "incr", AsyncMock())
    monkeypatch.setattr(analytics_service, "lookup_geo", lambda ip: ("IN", "Delhi"))
    monkeypatch.setattr(
        analytics_service, "parse_user_agent", lambda ua: ("mobile", "Chrome", "Android")
    )

    class FakeRequest:
        client = type("C", (), {"host": "1.2.3.4"})()
        headers = {"user-agent": "test-agent", "referer": "https://twitter.com"}

    await analytics_service.log_click("abcd", FakeRequest())

    insert_mock.assert_awaited_once_with(
        url_id=42,
        ip_address="1.2.3.4",
        country="IN",
        city="Delhi",
        device_type="mobile",
        browser="Chrome",
        os="Android",
        referrer="https://twitter.com",
    )
