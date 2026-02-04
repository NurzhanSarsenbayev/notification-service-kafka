from __future__ import annotations
import logging

from notifications.worker.senders.base import BaseSender

logger = logging.getLogger(__name__)


class WsSender(BaseSender):
    """Send WebSocket notifications (stub: logs only).

    A real WebSocket gateway can be plugged in later.
    """

    async def send(self, *, to: str, subject: str, body: str) -> None:
        if not to:
            raise ValueError("Recipient ws_session_id is empty")

        logger.info(
            "[WS] Sending to session=%s subject=%r body=%r",
            to,
            subject,
            body,
        )
