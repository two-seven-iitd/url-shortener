from fastapi import APIRouter, Depends

from app.middleware.auth import get_api_key
from app.models.schemas import UrlAnalytics, UrlAnalyticsSummary
from app.services import analytics_service

router = APIRouter()


@router.get("/analytics/{code}", response_model=UrlAnalytics)
async def get_analytics(code: str, days: int = 30, api_key: dict = Depends(get_api_key)):
    return await analytics_service.get_url_analytics(code, days)


@router.get("/analytics/{code}/summary", response_model=UrlAnalyticsSummary)
async def get_analytics_summary(code: str, api_key: dict = Depends(get_api_key)):
    return await analytics_service.get_url_analytics_summary(code)
