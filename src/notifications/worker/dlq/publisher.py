from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from aiokafka import AIOKafkaProducer

from notifications.common.schemas import NotificationJob
from notifications.common.config import Settings

logger = logging.getLogger(__name__)


class DlqPublisher:
    """Publish messages to the DLQ topic."""

    def __init__(self, settings: Settings, producer: AIOKafkaProducer) -> None:
        self._settings = settings
        self._producer = producer

    async def publish_job(
        self, job: NotificationJob, error_message: str | None
    ) -> None:
        payload: dict[str, Any] = {
            "job": job.model_dump(mode="json"),
            "error_message": error_message,
            "failed_at": datetime.now(timezone.utc).isoformat(),
        }
        await self._send(payload, key=str(job.job_id))

    async def publish_raw(self, raw_value: bytes, error_message: str | None) -> None:
        payload = {
            "raw_value": raw_value.decode("utf-8", errors="replace"),
            "error_message": error_message,
            "failed_at": datetime.now(timezone.utc).isoformat(),
        }
        await self._send(payload, key=None)

    async def _send(self, payload: dict[str, Any], key: str | None) -> None:
        value = json.dumps(payload).encode("utf-8")
        key_bytes = key.encode("utf-8") if key else None

        logger.error(
            "Sending message to DLQ topic=%s key=%r payload=%r",
            self._settings.kafka_dlq_topic,
            key,
            payload,
        )

        await self._producer.send_and_wait(
            topic=self._settings.kafka_dlq_topic,
            key=key_bytes,
            value=value,
        )
