import ssl

import asyncpg

from app.config import settings

_pool: asyncpg.Pool | None = None


async def connect() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        kwargs = {}
        if "sslmode=require" in settings.database_url or settings.database_url.startswith("postgresql+"):
            kwargs["ssl"] = ssl.create_default_context()
        _pool = await asyncpg.create_pool(settings.database_url, min_size=2, max_size=10, **kwargs)
    return _pool


async def disconnect() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool is not initialized. Call connect() first.")
    return _pool
