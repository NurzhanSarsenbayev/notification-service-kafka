from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, Sequence

from notifications.worker.dlq import DlqPublisher
from notifications.common.schemas import NotificationJob
from notifications.worker.repositories import NotificationDeliveryRepository
from notifications.worker.processor.status_writer import mark_sent, mark_failure

logger = logging.getLogger(__name__)

AttemptSendFn = Callable[[NotificationJob], Awaitable[None]]


async def attempt_with_retries(
    *,
    job: NotificationJob,
    existing_attempts: int,
    max_attempts: int,
    retry_delays: Sequence[float],
    attempt_send_fn: AttemptSendFn,
    delivery_repo: NotificationDeliveryRepository,
    dlq_publisher: DlqPublisher,
) -> None:
    """Retry loop for a single job.

    - calls attempt_send_fn
    - writes statuses via status_writer
    - publishes to DLQ on final failure
    """
    attempts = existing_attempts

    while attempts < max_attempts:
        attempts += 1
        try:
            await attempt_send_fn(job)
            await mark_sent(delivery_repo, job, attempts)
            return

        except Exception as exc:
            error = str(exc)
            is_last = attempts >= max_attempts

            await mark_failure(
                delivery_repo=delivery_repo,
                job=job,
                attempts=attempts,
                error=error,
                final=is_last,
            )

            if is_last:
                await dlq_publisher.publish_job(job, error_message=error)
                return

            delay = _get_retry_delay(attempts, retry_delays)
            logger.info(
                "Retrying job %s after %.2f sec (attempt %s/%s)",
                job.job_id,
                delay,
                attempts,
                max_attempts,
            )
            await asyncio.sleep(delay)


def _get_retry_delay(attempts: int, retry_delays: Sequence[float]) -> float:
    """Select a retry delay for the given attempt number (bounded by the list size)."""
    if not retry_delays:
        return 0.0
    idx = max(0, min(attempts - 1, len(retry_delays) - 1))
    return float(retry_delays[idx])
