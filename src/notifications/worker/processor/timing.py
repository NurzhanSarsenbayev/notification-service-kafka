from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from src.notifications.common.schemas import NotificationJob
from ..repositories import NotificationDeliveryRepository
from .status_writer import mark_expired

logger = logging.getLogger(__name__)


async def handle_expiration_if_needed(
    job: NotificationJob,
    existing,
    delivery_repo: NotificationDeliveryRepository,
) -> bool:
    """
    Check expires_at and mark the job as EXPIRED when needed.
    """
    if not job.expires_at:
        return False

    now = datetime.now(timezone.utc)
    expires = job.expires_at.astimezone(timezone.utc)

    if now <= expires:
        return False

    attempts = existing.attempts if existing else 0
    logger.warning("Job %s expired at %s", job.job_id, expires)

    await mark_expired(
        delivery_repo=delivery_repo,
        job=job,
        attempts=attempts,
    )
    return True


async def wait_send_after_if_needed(
    job: NotificationJob,
    max_send_delay_seconds: int,
) -> None:
    """
    Handle send_after: sleep until due time (bounded by max_send_delay).
    """
    if not job.send_after:
        return

    now = datetime.now(timezone.utc)
    target = job.send_after.astimezone(timezone.utc)

    if target <= now:
        return

    delay = (target - now).total_seconds()
    delay = min(delay, float(max_send_delay_seconds))

    if delay <= 0:
        return

    logger.info("Delaying job %s for %.2f sec until %s",
                job.job_id, delay, target)
    await asyncio.sleep(delay)
