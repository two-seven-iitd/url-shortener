from datetime import datetime, timedelta
from typing import Optional

from app.db.database import get_pool


# --- API keys ---

async def get_api_key(key: str) -> Optional[dict]:
    pool = get_pool()
    row = await pool.fetchrow("SELECT * FROM api_keys WHERE key = $1", key)
    return dict(row) if row else None


# --- URLs ---

async def get_url_by_code(code: str) -> Optional[dict]:
    pool = get_pool()
    row = await pool.fetchrow("SELECT * FROM urls WHERE code = $1", code)
    return dict(row) if row else None


async def insert_url(
    code: str,
    original_url: str,
    api_key_id: int,
    is_custom_alias: bool = False,
    expires_in_hours: Optional[int] = None,
) -> int:
    pool = get_pool()
    expires_at = datetime.now() + timedelta(hours=expires_in_hours) if expires_in_hours else None
    row = await pool.fetchrow(
        """INSERT INTO urls (code, original_url, api_key_id, is_custom_alias, expires_at)
           VALUES ($1, $2, $3, $4, $5) RETURNING id""",
        code, original_url, api_key_id, is_custom_alias, expires_at,
    )
    return row["id"]


async def next_url_id() -> int:
    """Reserve the next id from the urls sequence so its base62 code can be computed
    before the row is inserted (code is UNIQUE NOT NULL, so we can't insert a placeholder)."""
    pool = get_pool()
    return await pool.fetchval("SELECT nextval('urls_id_seq')")


async def insert_url_with_id(
    url_id: int,
    code: str,
    original_url: str,
    api_key_id: int,
    expires_in_hours: Optional[int] = None,
) -> None:
    pool = get_pool()
    expires_at = datetime.now() + timedelta(hours=expires_in_hours) if expires_in_hours else None
    await pool.execute(
        """INSERT INTO urls (id, code, original_url, api_key_id, expires_at)
           VALUES ($1, $2, $3, $4, $5)""",
        url_id, code, original_url, api_key_id, expires_at,
    )


async def increment_click_count(code: str) -> None:
    pool = get_pool()
    await pool.execute("UPDATE urls SET clicks_count = clicks_count + 1 WHERE code = $1", code)


async def deactivate_url(code: str, api_key_id: int) -> bool:
    pool = get_pool()
    result = await pool.execute(
        "UPDATE urls SET is_active = FALSE WHERE code = $1 AND api_key_id = $2",
        code, api_key_id,
    )
    return result.endswith("1")


async def list_urls(api_key_id: int, limit: int = 20, offset: int = 0) -> list[dict]:
    pool = get_pool()
    rows = await pool.fetch(
        """SELECT * FROM urls WHERE api_key_id = $1
           ORDER BY created_at DESC LIMIT $2 OFFSET $3""",
        api_key_id, limit, offset,
    )
    return [dict(r) for r in rows]


async def count_urls(api_key_id: int) -> int:
    pool = get_pool()
    return await pool.fetchval("SELECT COUNT(*) FROM urls WHERE api_key_id = $1", api_key_id)


async def total_urls() -> int:
    pool = get_pool()
    return await pool.fetchval("SELECT COUNT(*) FROM urls")


# --- Clicks ---

async def insert_click(
    url_id: int,
    ip_address: Optional[str],
    country: Optional[str],
    city: Optional[str],
    device_type: str,
    browser: str,
    os: str,
    referrer: Optional[str],
) -> None:
    pool = get_pool()
    await pool.execute(
        """INSERT INTO clicks (url_id, ip_address, country, city, device_type, browser, os, referrer)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
        url_id, ip_address, country, city, device_type, browser, os, referrer,
    )


# --- Analytics ---

async def count_clicks(url_id: int, since: datetime) -> int:
    pool = get_pool()
    return await pool.fetchval(
        "SELECT COUNT(*) FROM clicks WHERE url_id = $1 AND clicked_at >= $2",
        url_id, since,
    )


async def clicks_by_day(url_id: int, since: datetime) -> list[dict]:
    pool = get_pool()
    rows = await pool.fetch(
        """SELECT DATE(clicked_at) AS date, COUNT(*) AS count
           FROM clicks WHERE url_id = $1 AND clicked_at >= $2
           GROUP BY DATE(clicked_at) ORDER BY date""",
        url_id, since,
    )
    return [{"date": str(r["date"]), "count": r["count"]} for r in rows]


async def clicks_by_country(url_id: int, since: datetime) -> list[dict]:
    pool = get_pool()
    rows = await pool.fetch(
        """SELECT COALESCE(country, 'Unknown') AS country, COUNT(*) AS count
           FROM clicks WHERE url_id = $1 AND clicked_at >= $2
           GROUP BY country ORDER BY count DESC LIMIT 20""",
        url_id, since,
    )
    return [{"country": r["country"], "count": r["count"]} for r in rows]


async def clicks_by_device(url_id: int, since: datetime) -> dict[str, int]:
    pool = get_pool()
    rows = await pool.fetch(
        """SELECT device_type, COUNT(*) AS count
           FROM clicks WHERE url_id = $1 AND clicked_at >= $2
           GROUP BY device_type""",
        url_id, since,
    )
    return {r["device_type"]: r["count"] for r in rows}


async def clicks_by_browser(url_id: int, since: datetime) -> dict[str, int]:
    pool = get_pool()
    rows = await pool.fetch(
        """SELECT browser, COUNT(*) AS count
           FROM clicks WHERE url_id = $1 AND clicked_at >= $2
           GROUP BY browser ORDER BY count DESC LIMIT 10""",
        url_id, since,
    )
    return {r["browser"]: r["count"] for r in rows}


async def clicks_by_os(url_id: int, since: datetime) -> dict[str, int]:
    pool = get_pool()
    rows = await pool.fetch(
        """SELECT os, COUNT(*) AS count
           FROM clicks WHERE url_id = $1 AND clicked_at >= $2
           GROUP BY os ORDER BY count DESC LIMIT 10""",
        url_id, since,
    )
    return {r["os"]: r["count"] for r in rows}


async def top_referrers(url_id: int, since: datetime, limit: int = 10) -> list[dict]:
    pool = get_pool()
    rows = await pool.fetch(
        """SELECT COALESCE(referrer, 'Direct') AS referrer, COUNT(*) AS count
           FROM clicks WHERE url_id = $1 AND clicked_at >= $2
           GROUP BY referrer ORDER BY count DESC LIMIT $3""",
        url_id, since, limit,
    )
    return [{"referrer": r["referrer"], "count": r["count"]} for r in rows]


async def clicks_by_hour(url_id: int, since: datetime) -> list[dict]:
    pool = get_pool()
    rows = await pool.fetch(
        """SELECT EXTRACT(HOUR FROM clicked_at)::int AS hour, COUNT(*) AS count
           FROM clicks WHERE url_id = $1 AND clicked_at >= $2
           GROUP BY hour ORDER BY hour""",
        url_id, since,
    )
    return [{"hour": r["hour"], "count": r["count"]} for r in rows]
