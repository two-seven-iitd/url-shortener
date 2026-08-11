from fastapi import APIRouter, Depends, HTTPException

from app.cache.redis_cache import url_cache
from app.middleware.auth import get_api_key
from app.models.schemas import ShortenRequest, ShortenResponse
from app.services import url_service
from app.services.rate_limiter import RateLimiter

router = APIRouter()
rate_limiter = RateLimiter(url_cache.redis)


@router.post("/shorten", response_model=ShortenResponse, status_code=201)
async def shorten_url(body: ShortenRequest, api_key: dict = Depends(get_api_key)):
    allowed = await rate_limiter.check(api_key["key"], api_key["rate_limit_per_minute"])
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    return await url_service.create_short_url(body, api_key)
