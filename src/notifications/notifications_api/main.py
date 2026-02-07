from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text

from notifications.common.config import settings
from notifications.common.db import engine
from notifications.common.kafka import kafka_publisher
from notifications.notifications_api.api.v1.events import router as events_router
from notifications.notifications_api.api.v1.templates import router as templates_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    await kafka_publisher.start()
    try:
        yield
    finally:
        # shutdown
        await kafka_publisher.stop()


app = FastAPI(
    title=settings.project_name,
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}


@app.get("/ready", tags=["health"])
async def ready():
    # DB readiness
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "checks": {"db": f"error:{type(exc).__name__}"},
            },
        )

    # Kafka readiness (publisher must be started and not in degraded mode)
    if not kafka_publisher.is_ready():
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "checks": {"db": "ok", "kafka": "not_ready"},
            },
        )

    return {"status": "ok", "checks": {"db": "ok", "kafka": "ok"}}


app.include_router(events_router, prefix=settings.api_v1_prefix)
app.include_router(templates_router, prefix=settings.api_v1_prefix)
