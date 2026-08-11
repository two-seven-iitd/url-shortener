import mimetypes
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

mimetypes.init()
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/javascript", ".js")

from app.cache.redis_cache import url_cache
from app.db import database
from app.db.migrations import run_migrations
from app.db import repository as db
from app.models.schemas import HealthResponse, SiteStats
from app.routers import analytics, frontend, redirect, shorten, urls


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = await database.connect()
    await run_migrations(pool)
    yield
    await database.disconnect()
    await url_cache.close()


app = FastAPI(title="URL Shortener", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Order matters: named routes and frontend pages must be registered before
# the catch-all GET /{code} redirect router.
app.include_router(frontend.router)
app.include_router(shorten.router)
app.include_router(analytics.router)
app.include_router(urls.router)


@app.get("/stats", response_model=SiteStats)
async def site_stats():
    total = await db.total_urls()
    redirects = await url_cache.get_count("stats:redirects:total")
    return SiteStats(total_urls=total, total_redirects=redirects)


@app.get("/health", response_model=HealthResponse)
async def health():
    redis_ok = await url_cache.ping()
    try:
        pool = database.get_pool()
        await pool.fetchval("SELECT 1")
        postgres_ok = True
    except Exception:
        postgres_ok = False

    return HealthResponse(
        status="ok" if redis_ok and postgres_ok else "degraded",
        redis="ok" if redis_ok else "down",
        postgres="ok" if postgres_ok else "down",
    )


app.include_router(redirect.router)
