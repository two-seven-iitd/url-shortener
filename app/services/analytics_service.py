import asyncio
import logging
from datetime import datetime, timedelta

from fastapi import HTTPException, Request

from app.cache.redis_cache import url_cache
from app.core.geo import lookup_geo
from app.core.user_agent import parse_user_agent
from app.db import repository as db
from app.models.schemas import UrlAnalytics, UrlAnalyticsSummary

logger = logging.getLogger(__name__)


async def log_click(code: str, request: Request) -> None:
    """Log click data asynchronously. Failures here should never affect the redirect."""
    try:
        ip = request.client.host if request.client else None
        user_agent_str = request.headers.get("user-agent", "")
        referrer = request.headers.get("referer")

        device_type, browser, os_name = parse_user_agent(user_agent_str)
        country, city = lookup_geo(ip) if ip else (None, None)

        url_record = await db.get_url_by_code(code)
        if url_record is None:
            return

        await db.insert_click(
            url_id=url_record["id"],
            ip_address=ip,
            country=country,
            city=city,
            device_type=device_type,
            browser=browser,
            os=os_name,
            referrer=referrer,
        )

        await db.increment_click_count(code)
        await url_cache.incr("stats:redirects:total")

    except Exception as e:
        logger.warning("Click logging failed for code=%s: %s", code, e)


def schedule_click_log(code: str, request: Request) -> None:
    """Fire-and-forget click logging so the redirect response is never blocked."""
    asyncio.create_task(log_click(code, request))


async def get_url_analytics(code: str, days: int = 30) -> UrlAnalytics:
    url_record = await db.get_url_by_code(code)
    if not url_record:
        raise HTTPException(status_code=404, detail="URL not found")

    url_id = url_record["id"]
    since = datetime.now() - timedelta(days=days)

    (
        total_clicks,
        clicks_by_day,
        clicks_by_country,
        clicks_by_device,
        clicks_by_browser,
        clicks_by_os,
        top_referrers,
        clicks_by_hour,
    ) = await asyncio.gather(
        db.count_clicks(url_id, since),
        db.clicks_by_day(url_id, since),
        db.clicks_by_country(url_id, since),
        db.clicks_by_device(url_id, since),
        db.clicks_by_browser(url_id, since),
        db.clicks_by_os(url_id, since),
        db.top_referrers(url_id, since, limit=10),
        db.clicks_by_hour(url_id, since),
    )

    return UrlAnalytics(
        code=code,
        original_url=url_record["original_url"],
        total_clicks=total_clicks,
        created_at=url_record["created_at"],
        expires_at=url_record["expires_at"],
        clicks_by_day=clicks_by_day,
        clicks_by_country=clicks_by_country,
        clicks_by_device=clicks_by_device,
        clicks_by_browser=clicks_by_browser,
        clicks_by_os=clicks_by_os,
        top_referrers=top_referrers,
        clicks_by_hour=clicks_by_hour,
    )


async def get_url_analytics_summary(code: str) -> UrlAnalyticsSummary:
    url_record = await db.get_url_by_code(code)
    if not url_record:
        raise HTTPException(status_code=404, detail="URL not found")

    return UrlAnalyticsSummary(
        code=code,
        total_clicks=url_record["clicks_count"],
        created_at=url_record["created_at"],
    )
