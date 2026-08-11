from fastapi import APIRouter, Depends

from app.middleware.auth import get_api_key
from app.models.schemas import UrlListResponse
from app.services import url_service

router = APIRouter()


@router.get("/urls", response_model=UrlListResponse)
async def list_urls(limit: int = 20, offset: int = 0, api_key: dict = Depends(get_api_key)):
    return await url_service.list_urls(api_key["id"], limit, offset)


@router.delete("/urls/{code}", status_code=204)
async def delete_url(code: str, api_key: dict = Depends(get_api_key)):
    await url_service.deactivate_url(code, api_key["id"])
