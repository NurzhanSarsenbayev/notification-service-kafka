from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import asyncpg


@dataclass
class NotificationDelivery:
    job_id: UUID
    user_id: UUID
    status: str
    attempts: int
    error_message: Optional[str]
    sent_at: Optional[datetime]
    processing_started_at: Optional[datetime]


class NotificationDeliveryRepository:
    """Access to the notification_delivery table."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_by_job_id(self, job_id: UUID) -> Optional[NotificationDelivery]:
        query = """
            SELECT job_id, user_id, status, attempts, error_message, sent_at, processing_started_at
            FROM notification_delivery
            WHERE job_id = $1;
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, job_id)

        if row is None:
            return None

        return NotificationDelivery(
            job_id=row["job_id"],
            user_id=row["user_id"],
            status=row["status"],
            attempts=row["attempts"],
            error_message=row["error_message"],
            sent_at=row["sent_at"],
            processing_started_at=row["processing_started_at"],
        )

    async def try_claim_job(
            self,
            *,
            job_id: UUID,
            user_id: UUID,
            channel: str,
            stale_after_seconds: int = 300,
    ) -> bool:
        now = datetime.now(timezone.utc)
        stale_before = now - timedelta(seconds=stale_after_seconds)

        async with self._pool.acquire() as conn:
            insert_query = """
                           INSERT INTO notification_delivery (job_id, \
                                                              user_id, \
                                                              channel, \
                                                              status, \
                                                              attempts, \
                                                              processing_started_at)
                           VALUES ($1, $2, $3, $4, 0, $5) ON CONFLICT (job_id) DO NOTHING \
                           """
            result = await conn.execute(
                insert_query,
                job_id,
                user_id,
                channel,
                "PROCESSING",
                now,
            )
            if result == "INSERT 0 1":
                return True

            update_query = """
                           UPDATE notification_delivery
                           SET status                = $2,
                               processing_started_at = $3,
                               updated_at            = now()
                           WHERE job_id = $1
                             AND status NOT IN ('SENT', 'FAILED', 'EXPIRED')
                             AND (
                               status <> 'PROCESSING'
                                   OR processing_started_at IS NULL
                                   OR processing_started_at < $4
                               ) \
                           """
            result = await conn.execute(
                update_query,
                job_id,
                "PROCESSING",
                now,
                stale_before,
            )
            return result == "UPDATE 1"

    async def save_status(
        self,
        *,
        job_id: UUID,
        user_id: UUID,
        channel: str,
        status: str,
        attempts: int,
        error_code: Optional[str],
        error_message: Optional[str],
        sent_at: Optional[datetime],
    ) -> None:
        """Upsert by job_id: create a record or update status/attempt counters.

        Important: channel is always required and must not be NULL.
        """
        query = """
            INSERT INTO notification_delivery (
                job_id,
                user_id,
                channel,
                status,
                attempts,
                error_code,
                error_message,
                sent_at,
                processing_started_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NULL)
            ON CONFLICT (job_id) DO UPDATE
            SET
                status = EXCLUDED.status,
                attempts = EXCLUDED.attempts,
                error_code = EXCLUDED.error_code,
                error_message = EXCLUDED.error_message,
                sent_at = EXCLUDED.sent_at,
                updated_at = now(),
                processing_started_at = NULL;
        """
        async with self._pool.acquire() as conn:
            await conn.execute(
                query,
                job_id,
                user_id,
                channel,
                status,
                attempts,
                error_code,
                error_message,
                sent_at,
            )
