"""Kafka helpers and abstractions shared across components.

This module provides a publisher used by the API to enqueue NotificationJob messages.
If Kafka is unavailable, the publisher switches to a degraded mode and logs what would
have been published instead of crashing the application.
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional

from aiokafka import AIOKafkaProducer, errors

from notifications.common.config import settings

logger = logging.getLogger(__name__)


class KafkaNotificationJobPublisher:
    """Publishes NotificationJob messages to Kafka.

    If Kafka is unavailable on startup, the publisher switches to a degraded mode
    and logs jobs instead of publishing them.
    """

    def __init__(self, bootstrap_servers: str, topic: str) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._topic = topic
        self._producer: Optional[AIOKafkaProducer] = None
        self._enabled: bool = True

    async def start(self) -> None:
        """Start Kafka producer with a bounded retry loop.

        After exhausting retries, switches to degraded mode.
        """
        if self._producer is not None or not self._enabled:
            return

        max_attempts = 10
        delay_seconds = 1

        for attempt in range(1, max_attempts + 1):
            producer = AIOKafkaProducer(
                bootstrap_servers=self._bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            )
            try:
                logger.info(
                    "Starting Kafka producer (attempt %s/%s) bootstrap_servers=%s",
                    attempt,
                    max_attempts,
                    self._bootstrap_servers,
                )
                await producer.start()
            except Exception:
                logger.exception(
                    "Failed to start Kafka producer (attempt %s/%s) bootstrap_servers=%s",
                    attempt,
                    max_attempts,
                    self._bootstrap_servers,
                )
                try:
                    await producer.stop()
                except Exception:
                    logger.exception("Producer stop failed after unsuccessful start")

                if attempt == max_attempts:
                    logger.error(
                        "Kafka producer is unavailable after %s attempts; switching to degraded mode",
                        max_attempts,
                    )
                    self._enabled = False
                    self._producer = None
                    return

                await asyncio.sleep(delay_seconds)
                continue

            self._producer = producer
            self._enabled = True
            logger.info("Kafka producer started bootstrap_servers=%s", self._bootstrap_servers)
            return

    async def stop(self) -> None:
        if self._producer is None:
            return
        try:
            await self._producer.stop()
        except Exception:
            logger.exception("Failed to stop Kafka producer")
        finally:
            self._producer = None

    async def publish_job(self, payload: Dict[str, Any]) -> None:
        if not self._enabled or self._producer is None:
            logger.info("Kafka degraded mode: would publish topic=%s payload=%s", self._topic, payload)
            return

        try:
            await self._producer.send_and_wait(self._topic, payload)
        except errors.KafkaError:
            logger.exception("Kafka error while publishing topic=%s", self._topic)
        except Exception:
            logger.exception("Unexpected error while publishing topic=%s", self._topic)


kafka_publisher = KafkaNotificationJobPublisher(
    bootstrap_servers=settings.kafka_bootstrap_servers,
    topic=settings.kafka_outbox_topic,
)
