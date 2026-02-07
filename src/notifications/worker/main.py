from __future__ import annotations

import asyncio
import logging
import signal

from notifications.common.health_files import mark_ready, clear_ready, heartbeat_loop
from notifications.worker.auth import AuthClient
from notifications.worker.consumer import KafkaNotificationConsumer
from notifications.worker.core.config import settings
from notifications.worker.core.logger import configure_logging
from notifications.worker.dlq import DlqPublisher
from notifications.worker.processor import JobProcessor
from notifications.worker.repositories import (
    NotificationDeliveryRepository,
    TemplateRepository,
)
from notifications.worker.senders import EmailSender, PushSender, WsSender
from notifications.worker.startup import (
    create_db_pool,
    create_kafka_producer,
    create_http_client,
)


logger = logging.getLogger(__name__)


async def app() -> None:
    # Fail-fast: validate critical settings at startup (do not DLQ jobs due to bad config)

    try:
        _ = settings.retry_delays_seconds
    except ValueError:
        logger.exception("Invalid RETRY_DELAYS_SECONDS_RAW. Worker cannot start.")
        raise

    logger.info(
        "Notification worker app starting with"
        " kafka_bootstrap_servers=%s, outbox_topic=%s, dlq_topic=%s",
        settings.kafka_bootstrap_servers,
        settings.kafka_outbox_topic,
        settings.kafka_dlq_topic,
    )
    clear_ready()

    db_pool = await create_db_pool()
    dlq_producer = await create_kafka_producer()
    http_client = await create_http_client()

    mark_ready()
    hb_task = asyncio.create_task(heartbeat_loop(5.0), name="worker-heartbeat")

    template_repo = TemplateRepository(db_pool)
    delivery_repo = NotificationDeliveryRepository(db_pool)
    auth_client = AuthClient(settings, http_client)
    email_sender = EmailSender(
        host=settings.smtp_host, port=settings.smtp_port, sender=settings.smtp_from
    )
    push_sender = PushSender()
    ws_sender = WsSender()
    dlq_publisher = DlqPublisher(settings, dlq_producer)

    processor = JobProcessor(
        settings=settings,
        template_repo=template_repo,
        delivery_repo=delivery_repo,
        auth_client=auth_client,
        email_sender=email_sender,
        push_sender=push_sender,
        ws_sender=ws_sender,
        dlq_publisher=dlq_publisher,
    )

    consumer = KafkaNotificationConsumer(
        settings=settings,
        processor=processor,
        dlq_publisher=dlq_publisher,
    )

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _handle_signal(sig: signal.Signals) -> None:
        logger.info("Received signal %s, shutting down...", sig)
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_signal, sig)
        except NotImplementedError:
            logger.warning("Signal handlers not supported in this environment")

    logger.info("Starting Kafka consumer task...")
    consumer_task = asyncio.create_task(consumer.start(), name="kafka-consumer")

    try:
        logger.info("Worker is running, waiting for stop event...")
        await stop_event.wait()
        logger.info("Stop event set, cancelling consumer task...")
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            logger.info("Consumer task cancelled")
    finally:
        hb_task.cancel()
        clear_ready()
        await http_client.aclose()
        logger.info("HTTP client closed")
        await dlq_producer.stop()
        logger.info("Kafka producer stopped")
        await db_pool.close()
        logger.info("Postgres pool closed")


def main() -> None:
    configure_logging()
    logger.info("Notification worker main() starting")
    asyncio.run(app())
    logger.info("Notification worker main() exited")


if __name__ == "__main__":
    main()
