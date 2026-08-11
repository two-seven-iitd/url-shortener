import redis.asyncio as redis

from app.config import settings


class UrlCache:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url, decode_responses=True)

    async def get_url(self, code: str) -> str | None:
        """Get original URL from cache. Returns None on miss."""
        url = await self.redis.get(f"url:{code}")
        if url:
            await self.redis.expire(f"url:{code}", settings.default_cache_ttl_seconds)
        return url

    async def set_url(self, code: str, original_url: str, ttl: int | None = None):
        await self.redis.set(f"url:{code}", original_url, ex=ttl or settings.default_cache_ttl_seconds)

    async def delete_url(self, code: str):
        await self.redis.delete(f"url:{code}")

    async def incr(self, key: str):
        await self.redis.incr(key)

    async def get_count(self, key: str) -> int:
        val = await self.redis.get(key)
        return int(val) if val else 0

    async def ping(self) -> bool:
        try:
            return await self.redis.ping()
        except Exception:
            return False

    async def close(self):
        await self.redis.close()


url_cache = UrlCache(settings.redis_url)
