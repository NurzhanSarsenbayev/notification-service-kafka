from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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


class NotificationDeliveryRepository:
    """Access to the notification_delivery table."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_by_job_id(self, job_id: UUID) -> Optional[NotificationDelivery]:
        query = """
            SELECT job_id, user_id, status, attempts, error_message, sent_at
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
        )

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
                sent_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (job_id) DO UPDATE
            SET
                status = EXCLUDED.status,
                attempts = EXCLUDED.attempts,
                error_code = EXCLUDED.error_code,
                error_message = EXCLUDED.error_message,
                sent_at = EXCLUDED.sent_at,
                updated_at = now()
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
