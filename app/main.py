import logging
import asyncio
from contextlib import suppress
from app.redis_client import redis, available, listen
from app.middleware.redis_rate_limit import RedisRateLimitMiddleware
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.config import settings
from app.database import engine
from app.api import api_router
from app.exceptions import register_exception_handlers
from app.middleware.request_logging import RequestLoggingMiddleware
from app.middleware.production import ErrorMiddleware, RateLimitMiddleware

logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app):
    try:
        Path("var/uploads").mkdir(parents=True, exist_ok=True)
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        listener = asyncio.create_task(listen())
        try:
            yield
        finally:
            listener.cancel()
            with suppress(asyncio.CancelledError):
                await listener
            await redis.aclose()
    finally:
        await engine.dispose()

app = FastAPI(title=settings.app_name, version="2.0.0", lifespan=lifespan)
app.add_middleware(RedisRateLimitMiddleware)
app.add_middleware(ErrorMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"], expose_headers=["X-Request-ID", "X-Process-Time-Ms"])
register_exception_handlers(app)
app.include_router(api_router)

@app.get("/", tags=["health"])
@app.get("/health", tags=["health"])
async def health():
    redis_ok = await available()
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    return {"status": "healthy" if redis_ok else "degraded", "service": settings.app_name, "database": "ok", "redis": "ok" if redis_ok else "unavailable"}
