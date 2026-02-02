from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID
import logging

import httpx

from src.notifications.common.config import Settings  # или откуда у тебя берётся Settings

logger = logging.getLogger(__name__)


@dataclass
class UserContacts:
    user_id: UUID
    email: str | None = None
    push_token: str | None = None
    ws_session_id: str | None = None


class AuthClient:
    """Клиент для Auth-сервиса.

    В бою:
      - ходит в Auth по HTTP и возвращает реальные контакты.
    В тестах:
      - подменяется на FakeAuthClient через фикстуры.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def get_user_contacts(self, user_id: UUID) -> UserContacts:
        # Demo mode: if AUTH_BASE_URL is empty/unset, do not make HTTP calls.
        if not self._settings.auth_base_url:
            return self._fake_contacts(user_id)

        url = f"{self._settings.auth_base_url}/api/v1/users/{user_id}"

        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(url)
                data = resp.json()
        except Exception as exc:
            # Fallback, чтобы не ломать воркер, если Auth недоступен.
            logger.warning(
                "AuthClient: failed to fetch user %s from %s: %s — using fake contacts",
                user_id,
                url,
                exc,
            )
            return self._fake_contacts(user_id)

        return UserContacts(
            user_id=user_id,
            email=data.get("email"),
            push_token=data.get("push_token"),
            ws_session_id=data.get("ws_session_id"),
        )

    @staticmethod
    def _fake_contacts(user_id: UUID) -> UserContacts:
        """MVP-режим: фейковые данные, чтобы не падать."""
        fake_email = f"user-{user_id}@example.com"
        fake_push = f"push-{user_id}"
        fake_ws = f"ws-{user_id}"

        return UserContacts(
            user_id=user_id,
            email=fake_email,
            push_token=fake_push,
            ws_session_id=fake_ws,
        )