import time


class RateLimiter:
    def __init__(self, redis_client):
        self.redis = redis_client

    async def check(self, api_key: str, limit_per_minute: int) -> bool:
        """
        Token bucket rate limiting using Redis.

        Key: rate:{api_key}:{current_minute_timestamp}
        Value: number of requests made in this minute
        TTL: 60 seconds (auto-cleanup)

        Returns True if request is allowed, False if rate limited.
        """
        minute_bucket = int(time.time()) // 60
        key = f"rate:{api_key}:{minute_bucket}"

        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, 60)
        results = await pipe.execute()

        current_count = results[0]
        return current_count <= limit_per_minute
