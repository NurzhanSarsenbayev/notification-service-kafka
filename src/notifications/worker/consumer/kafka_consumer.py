from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError

from ..dlq import DlqPublisher
from src.notifications.common.schemas import NotificationJob
from src.notifications.common.config import Settings
from ..processor import JobProcessor

logger = logging.getLogger(__name__)


class KafkaNotificationConsumer:
    """Consumes NotificationJob messages from Kafka and passes them to JobProcessor."""

    def __init__(
        self,
        settings: Settings,
        processor: JobProcessor,
        dlq_publisher: DlqPublisher,
    ) -> None:
        self._settings = settings
        self._processor = processor
        self._dlq = dlq_publisher
        self._consumer: AIOKafkaConsumer | None = None
        self._stopped = asyncio.Event()

    async def start(self) -> None:
        self._consumer = AIOKafkaConsumer(
            self._settings.kafka_outbox_topic,
            bootstrap_servers=self._settings.kafka_bootstrap_servers,
            group_id=self._settings.kafka_consumer_group,
            enable_auto_commit=True,
            value_deserializer=lambda v: v,
        )

        await self._consumer.start()
        logger.info(
            "Kafka consumer started: topic=%s group=%s bootstrap_servers=%s",
            self._settings.kafka_outbox_topic,
            self._settings.kafka_consumer_group,
            self._settings.kafka_bootstrap_servers,
        )

        try:
            async for msg in self._consumer:
                if self._stopped.is_set():
                    logger.info("Stop flag set, breaking consumer loop")
                    break
                await self._handle_message(msg.value)
        except asyncio.CancelledError:
            logger.info("Kafka consumer cancelled")
            raise
        except KafkaError as err:
            logger.exception("Kafka error in consumer loop: %s", err)
        finally:
            await self._stop_consumer()

    async def stop(self) -> None:
        self._stopped.set()
        await self._stop_consumer()

    async def _stop_consumer(self) -> None:
        if self._consumer is not None:
            logger.info("Stopping Kafka consumer...")
            await self._consumer.stop()
            logger.info("Kafka consumer stopped")
            self._consumer = None

    async def _handle_message(self, raw_value: bytes) -> None:
        # 1. JSON deserialization
        try:
            payload: Any = json.loads(raw_value.decode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to decode message from Kafka: %s", exc)
            await self._dlq.publish_raw(
                raw_value,
                error_message="Invalid JSON in Kafka message")
            return

        # 2. NotificationJob validation
        try:
            job = NotificationJob.model_validate(payload)
        except Exception as exc:
            logger.exception("Failed to validate NotificationJob payload: %s",
                             exc)
            await self._dlq.publish_raw(
                raw_value,
                error_message="Invalid NotificationJob payload")
            return

        logger.info(
            "Received job from Kafka: job_id=%s user_id=%s channel=%s",
            job.job_id,
            job.user_id,
            job.channel,
        )

        # 3. Business processing
        try:
            await self._processor.handle_job(job)
        except Exception as exc:
            logger.exception(
                "Unhandled error while handling job %s, sending to DLQ",
                job.job_id,
            )
            await self._dlq.publish_job(job, error_message=str(exc))
        else:
            logger.info(
                "Job %s processed successfully (user_id=%s, channel=%s)",
                job.job_id,
                job.user_id,
                job.channel,
            )
