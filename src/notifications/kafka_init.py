from __future__ import annotations

import asyncio
import logging
from typing import List

from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from aiokafka.errors import KafkaError

from notifications.common.config import settings

logger = logging.getLogger(__name__)


async def wait_for_kafka(
    bootstrap_servers: str,
    attempts: int = 20,
    delay: float = 1.0,
) -> None:
    """Wait until Kafka is ready and responds to metadata requests."""
    for attempt in range(1, attempts + 1):
        try:
            logger.info(
                "Checking Kafka availability (attempt %s/%s)... bootstrap_servers=%s",
                attempt,
                attempts,
                bootstrap_servers,
            )
            admin = AIOKafkaAdminClient(bootstrap_servers=bootstrap_servers)
            await admin.start()
            await admin.close()
            logger.info("Kafka is up and responding")
            return
        except KafkaError as exc:
            logger.warning(
                "Kafka not ready yet on attempt %s/%s: %s",
                attempt,
                attempts,
                exc,
            )
        except OSError as exc:
            logger.warning(
                "Network error while connecting to Kafka on attempt %s/%s: %s",
                attempt,
                attempts,
                exc,
            )

        if attempt == attempts:
            logger.error("Kafka is still not available, giving up")
            raise SystemExit(1)

        await asyncio.sleep(delay)


async def create_topics() -> None:
    """Create outbox and DLQ topics if they do not exist."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )

    logger.info(
        "Kafka init started: bootstrap_servers=%s, outbox=%s, dlq=%s",
        settings.kafka_bootstrap_servers,
        settings.kafka_outbox_topic,
        settings.kafka_dlq_topic,
    )

    await wait_for_kafka(settings.kafka_bootstrap_servers)

    admin = AIOKafkaAdminClient(bootstrap_servers=settings.kafka_bootstrap_servers)
    await admin.start()
    try:
        existing: List[str] = list(await admin.list_topics())
        logger.info("Existing topics: %s", existing)

        topics_to_create: list[NewTopic] = []
        if settings.kafka_outbox_topic not in existing:
            topics_to_create.append(
                NewTopic(
                    name=settings.kafka_outbox_topic,
                    num_partitions=1,
                    replication_factor=1,
                )
            )
        if settings.kafka_dlq_topic not in existing:
            topics_to_create.append(
                NewTopic(
                    name=settings.kafka_dlq_topic,
                    num_partitions=1,
                    replication_factor=1,
                )
            )

        if not topics_to_create:
            logger.info(
                "Topics already exist, nothing to create (outbox=%s, dlq=%s)",
                settings.kafka_outbox_topic,
                settings.kafka_dlq_topic,
            )
            return

        await admin.create_topics(new_topics=topics_to_create)
        logger.info(
            "Created topics: %s",
            [t.name for t in topics_to_create],
        )
    finally:
        await admin.close()
        logger.info("Kafka admin client closed")


def main() -> None:
    asyncio.run(create_topics())


if __name__ == "__main__":
    main()
