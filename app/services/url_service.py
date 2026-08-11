import re
from datetime import datetime, timedelta
from urllib.parse import urlparse

import asyncpg
from fastapi import HTTPException

from app.cache.redis_cache import url_cache
from app.config import settings
from app.core.base62 import encode_base62
from app.db import repository as db
from app.models.schemas import ShortenRequest, ShortenResponse, UrlListResponse, UrlSummary

ALIAS_RE = re.compile(r"^[a-zA-Z0-9\-]{3,30}$")
MAX_URL_LENGTH = 10_000


def is_valid_url(url: str) -> bool:
    if len(url) > MAX_URL_LENGTH:
        return False
    try:
        result = urlparse(url)
        return all([result.scheme in ("http", "https"), result.netloc])
    except Exception:
        return False


async def create_short_url(body: ShortenRequest, api_key: dict) -> ShortenResponse:
    if not is_valid_url(body.url):
        raise HTTPException(status_code=400, detail="Invalid URL format")

    if body.custom_alias:
        if not ALIAS_RE.match(body.custom_alias):
            raise HTTPException(
                status_code=400,
                detail="Alias must be 3-30 alphanumeric characters or hyphens",
            )

        existing = await db.get_url_by_code(body.custom_alias)
        if existing:
            raise HTTPException(status_code=409, detail="Alias already taken")

        code = body.custom_alias
        try:
            await db.insert_url(
                code=code,
                original_url=body.url,
                api_key_id=api_key["id"],
                is_custom_alias=True,
                expires_in_hours=body.expires_in_hours,
            )
        except asyncpg.UniqueViolationError:
            raise HTTPException(status_code=409, detail="Alias already taken")
    else:
        url_id = await db.next_url_id()
        code = encode_base62(url_id)
        await db.insert_url_with_id(
            url_id=url_id,
            code=code,
            original_url=body.url,
            api_key_id=api_key["id"],
            expires_in_hours=body.expires_in_hours,
        )

    await url_cache.set_url(code, body.url)

    expires_at = None
    if body.expires_in_hours:
        expires_at = datetime.now() + timedelta(hours=body.expires_in_hours)

    return ShortenResponse(
        short_url=f"{settings.base_url}/{code}",
        code=code,
        original_url=body.url,
        created_at=datetime.now(),
        expires_at=expires_at,
    )


async def resolve_code(code: str) -> str:
    """Resolve a short code to its original URL, checking cache before DB.
    Raises 404 for unknown codes and 410 for expired/deactivated ones."""
    original_url = await url_cache.get_url(code)
    if original_url is not None:
        return original_url

    url_record = await db.get_url_by_code(code)
    if url_record is None:
        raise HTTPException(status_code=404, detail="Short URL not found")

    if url_record["expires_at"] and url_record["expires_at"] < datetime.now():
        raise HTTPException(status_code=410, detail="This link has expired")

    if not url_record["is_active"]:
        raise HTTPException(status_code=410, detail="This link has been deactivated")

    original_url = url_record["original_url"]

    ttl = settings.default_cache_ttl_seconds
    if url_record["expires_at"]:
        remaining = int((url_record["expires_at"] - datetime.now()).total_seconds())
        ttl = max(1, min(ttl, remaining))

    await url_cache.set_url(code, original_url, ttl=ttl)
    return original_url


async def deactivate_url(code: str, api_key_id: int) -> None:
    url_record = await db.get_url_by_code(code)
    if url_record is None or url_record["api_key_id"] != api_key_id:
        raise HTTPException(status_code=404, detail="Short URL not found")

    await db.deactivate_url(code, api_key_id)
    await url_cache.delete_url(code)


async def list_urls(api_key_id: int, limit: int = 20, offset: int = 0) -> UrlListResponse:
    rows = await db.list_urls(api_key_id, limit, offset)
    total = await db.count_urls(api_key_id)
    return UrlListResponse(
        urls=[
            UrlSummary(
                code=r["code"],
                original_url=r["original_url"],
                clicks_count=r["clicks_count"],
                is_custom_alias=r["is_custom_alias"],
                created_at=r["created_at"],
                expires_at=r["expires_at"],
                is_active=r["is_active"],
            )
            for r in rows
        ],
        total=total,
    )
