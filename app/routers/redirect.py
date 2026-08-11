from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.services import url_service
from app.services.analytics_service import schedule_click_log

router = APIRouter()


@router.get("/{code}")
async def redirect_to_url(code: str, request: Request):
    """
    Resolve short code -> original URL and redirect.

    Performance priority:
    1. Redis cache (sub-1ms)
    2. PostgreSQL fallback (5-10ms)
    3. Log click asynchronously (don't block the response)
    """
    original_url = await url_service.resolve_code(code)

    schedule_click_log(code, request)

    return RedirectResponse(url=original_url, status_code=301)
