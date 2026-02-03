from __future__ import annotations
import logging

from .base import BaseSender

logger = logging.getLogger(__name__)


class PushSender(BaseSender):
    """Send push notifications (stub: logs only)."""

    async def send(self, *, to: str, subject: str, body: str) -> None:
        if not to:
            raise ValueError("Recipient push_token is empty")

        logger.info(
            "[PUSH] Sending to=%s subject=%r body=%r",
            to,
            subject,
            body,
        )
