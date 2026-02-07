from __future__ import annotations

import asyncio
import logging
import httpx

import asyncpg
from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaConnectionError

from notifications.worker.core.config import settings

logger = logging.getLogger(__name__)


async def create_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=2.0)


async def create_db_pool() -> asyncpg.Pool:
    """Create a Postgres pool with simple startup retries."""
    max_attempts = 10
    delay_seconds = 1

    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(
                "Creating Postgres pool (attempt %s/%s)... dsn=%s",
                attempt,
                max_attempts,
                settings.db_asyncpg_dsn,
            )
            pool = await asyncpg.create_pool(
                dsn=settings.db_asyncpg_dsn,
                min_size=1,
                max_size=5,
            )
            logger.info("Postgres pool created")
            return pool
        except (OSError, asyncpg.PostgresError) as exc:
            logger.warning(
                "Failed to connect to Postgres on attempt %s/%s: %s",
                attempt,
                max_attempts,
                exc,
            )
            if attempt == max_attempts:
                logger.error("Giving up connecting to Postgres")
                raise
            await asyncio.sleep(delay_seconds)


async def create_kafka_producer() -> AIOKafkaProducer:
    """Create a Kafka producer for DLQ with startup retries."""
    max_attempts = 10
    delay_seconds = 1

    producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_bootstrap_servers)

    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(
                "Starting Kafka producer (attempt %s/%s)... bootstrap_servers=%s",
                attempt,
                max_attempts,
                settings.kafka_bootstrap_servers,
            )
            await producer.start()
            logger.info("Kafka producer started (for DLQ)")
            return producer
        except KafkaConnectionError as exc:
            logger.warning(
                "Failed to connect to Kafka on attempt %s/%s: %s",
                attempt,
                max_attempts,
                exc,
            )
            if attempt == max_attempts:
                logger.error("Giving up starting Kafka producer")
                await producer.stop()
                raise
            await asyncio.sleep(delay_seconds)
