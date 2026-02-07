from __future__ import annotations

import asyncpg
import httpx
import logging

from notifications.common.config import settings

logger = logging.getLogger(__name__)


async def create_db_pool() -> asyncpg.Pool:
    logger.info("Creating Postgres pool for scheduler: dsn=%s", settings.db_asyncpg_dsn)
    pool = await asyncpg.create_pool(
        dsn=settings.db_asyncpg_dsn,
        min_size=1,
        max_size=5,
    )
    logger.info("Postgres pool for scheduler created")
    return pool


def create_http_client() -> httpx.AsyncClient:
    """Create an AsyncClient using a timeout from settings (if configured)."""
    timeout_seconds = getattr(settings, "scheduler_http_timeout_seconds", 5.0)
    logger.info("Creating HTTP client for scheduler, timeout=%s", timeout_seconds)
    return httpx.AsyncClient(timeout=timeout_seconds)
