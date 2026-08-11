from unittest.mock import AsyncMock, MagicMock

from app.services.rate_limiter import RateLimiter


class FakePipeline:
    def __init__(self, counts):
        self._counts = counts
        self._ops = []

    def incr(self, key):
        self._ops.append(("incr", key))
        return self

    def expire(self, key, ttl):
        self._ops.append(("expire", key, ttl))
        return self

    async def execute(self):
        # First op is always the incr whose result we care about.
        count = next(self._counts)
        return [count, True]


def make_fake_redis(counts):
    redis = MagicMock()
    redis.pipeline = MagicMock(side_effect=lambda: FakePipeline(iter(counts)))
    return redis


async def test_allows_under_limit():
    redis = make_fake_redis([1])
    limiter = RateLimiter(redis)
    assert await limiter.check("key1", limit_per_minute=60) is True


async def test_allows_exactly_at_limit():
    redis = make_fake_redis([60])
    limiter = RateLimiter(redis)
    assert await limiter.check("key1", limit_per_minute=60) is True


async def test_rejects_over_limit():
    redis = make_fake_redis([61])
    limiter = RateLimiter(redis)
    assert await limiter.check("key1", limit_per_minute=60) is False


async def test_uses_per_minute_bucket_key():
    redis = MagicMock()
    pipe = MagicMock()
    pipe.execute = AsyncMock(return_value=[1, True])
    redis.pipeline = MagicMock(return_value=pipe)

    limiter = RateLimiter(redis)
    await limiter.check("abc123", limit_per_minute=60)

    pipe.incr.assert_called_once()
    (key_arg,), _ = pipe.incr.call_args
    assert key_arg.startswith("rate:abc123:")
    pipe.expire.assert_called_once_with(key_arg, 60)
