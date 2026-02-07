from __future__ import annotations

import logging
from datetime import datetime, timezone

from notifications.common.schemas import (
    NotificationStatus,
    NotificationJob,
    NotificationChannel,
)
from notifications.worker.repositories import NotificationDeliveryRepository

logger = logging.getLogger(__name__)


def _ensure_channel(job: NotificationJob) -> str:
    """Normalize a job channel for DB persistence.

    Rules:
    1) If channel is missing -> fallback to "email" (MVP compatibility).
    2) If Enum -> use .value.
    3) If string -> normalize to lower-case and try to parse NotificationChannel.
    4) If parsing fails -> fallback to "email" and log a warning.
    """
    ch = getattr(job, "channel", None)

    # 1) MVP fallback
    if ch is None:
        logger.warning("Job %s has no channel -> fallback to 'email'", job.job_id)
        return NotificationChannel.EMAIL.value

    # 2) Enum -> .value
    if isinstance(ch, NotificationChannel):
        return ch.value

    # 3) String -> normalize and try to parse enum
    if isinstance(ch, str):
        normalized = ch.strip().lower()
        try:
            return NotificationChannel(normalized).value
        except ValueError:
            logger.warning(
                "Job %s has unknown channel '%s' -> fallback to 'email'",
                job.job_id,
                ch,
            )
            return NotificationChannel.EMAIL.value

    # 4) Unexpected type -> fallback
    logger.error(
        "Job %s has invalid channel type '%s' -> fallback to 'email'",
        job.job_id,
        type(ch),
    )
    return NotificationChannel.EMAIL.value


async def mark_sent(
    delivery_repo: NotificationDeliveryRepository,
    job: NotificationJob,
    attempts: int,
) -> None:
    await delivery_repo.save_status(
        job_id=job.job_id,
        user_id=job.user_id,
        channel=_ensure_channel(job),
        status=NotificationStatus.SENT.value,
        attempts=attempts,
        error_code=None,
        error_message=None,
        sent_at=datetime.now(timezone.utc),
    )
    logger.info("Job %s SENT (attempt %s)", job.job_id, attempts)


async def mark_failure(
    delivery_repo: NotificationDeliveryRepository,
    job: NotificationJob,
    attempts: int,
    error: str,
    final: bool,
) -> None:
    status = NotificationStatus.FAILED if final else NotificationStatus.RETRYING

    await delivery_repo.save_status(
        job_id=job.job_id,
        user_id=job.user_id,
        channel=_ensure_channel(job),
        status=status.value,
        attempts=attempts,
        error_code=None,
        error_message=error,
        sent_at=None,
    )
    logger.warning(
        "Job %s %s on attempt %s: %s",
        job.job_id,
        status.value,
        attempts,
        error,
    )


async def mark_expired(
    delivery_repo: NotificationDeliveryRepository,
    job: NotificationJob,
    attempts: int,
    message: str = "Notification expired",
) -> None:
    await delivery_repo.save_status(
        job_id=job.job_id,
        user_id=job.user_id,
        channel=_ensure_channel(job),
        status=NotificationStatus.EXPIRED.value,
        attempts=attempts,
        error_code=None,
        error_message=message,
        sent_at=None,
    )
    logger.warning("Job %s EXPIRED (attempts=%s)", job.job_id, attempts)
