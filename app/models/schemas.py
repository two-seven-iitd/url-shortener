from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# --- Request Models ---

class ShortenRequest(BaseModel):
    url: str
    custom_alias: Optional[str] = None
    expires_in_hours: Optional[int] = None


class ShortenResponse(BaseModel):
    short_url: str
    code: str
    original_url: str
    created_at: datetime
    expires_at: Optional[datetime] = None


# --- URL listing ---

class UrlSummary(BaseModel):
    code: str
    original_url: str
    clicks_count: int
    is_custom_alias: bool
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool


class UrlListResponse(BaseModel):
    urls: list[UrlSummary]
    total: int


# --- Analytics Models ---

class ClickRecord(BaseModel):
    id: Optional[int] = None
    url_id: int
    timestamp: datetime
    ip_address: str
    country: Optional[str] = None
    city: Optional[str] = None
    device_type: str = "unknown"
    browser: str = "unknown"
    os: str = "unknown"
    referrer: Optional[str] = None


class UrlAnalytics(BaseModel):
    code: str
    original_url: str
    total_clicks: int
    created_at: datetime
    expires_at: Optional[datetime] = None
    clicks_by_day: list[dict]
    clicks_by_country: list[dict]
    clicks_by_device: dict[str, int]
    clicks_by_browser: dict[str, int]
    clicks_by_os: dict[str, int]
    top_referrers: list[dict]
    clicks_by_hour: list[dict]


class UrlAnalyticsSummary(BaseModel):
    code: str
    total_clicks: int
    created_at: datetime


# --- Misc ---

class HealthResponse(BaseModel):
    status: str
    redis: str
    postgres: str


class SiteStats(BaseModel):
    total_urls: int
    total_redirects: int
