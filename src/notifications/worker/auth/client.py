from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID
import logging

import httpx

from notifications.common.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class UserContacts:
    user_id: UUID
    email: str | None = None
    push_token: str | None = None
    ws_session_id: str | None = None


class AuthClient:
    """Auth service client.

    Production:
        - fetches real user contacts via HTTP from Auth service.

    Tests:
        - replaced with FakeAuthClient via fixtures.
    """

    def __init__(
        self, settings: Settings, http: httpx.AsyncClient | None = None
    ) -> None:
        self._settings = settings
        self._http = http

    async def get_user_contacts(self, user_id: UUID) -> UserContacts:
        # Demo mode: if AUTH_BASE_URL is empty/unset, do not make HTTP calls.
        if not self._settings.auth_base_url:
            return self._fake_contacts(user_id)

        if self._http is None:
            # Safety net: if not provided, fall back to fake
            return self._fake_contacts(user_id)

        url = f"{self._settings.auth_base_url}/api/v1/users/{user_id}"

        try:
            resp = await self._http.get(url)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning(
                "AuthClient: failed to fetch user %s from %s: %s - using fake contacts",
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
        """Demo mode: fake contacts to keep the worker self-contained."""
        fake_email = f"user-{user_id}@example.com"
        fake_push = f"push-{user_id}"
        fake_ws = f"ws-{user_id}"

        return UserContacts(
            user_id=user_id,
            email=fake_email,
            push_token=fake_push,
            ws_session_id=fake_ws,
        )
