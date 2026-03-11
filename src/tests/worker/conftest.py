from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from notifications.common.config import Settings
from notifications.common.schemas import (
    NotificationJob,
    NotificationMeta,
    NotificationChannel,
)
from notifications.worker.auth.client import UserContacts


class FakeTemplate:
    def __init__(self, subject: str, body: str) -> None:
        self.subject = subject
        self.body = body


class FakeTemplateRepo:
    def __init__(self) -> None:
        self.get_template = AsyncMock(
            return_value=FakeTemplate(
                subject="Hello, {name}!",
                body="Welcome, {name}!",
            )
        )


class FakeDeliveryRepo:
    def __init__(self) -> None:
        self.get_by_job_id = AsyncMock(return_value=None)
        self.save_status = AsyncMock()
        self.try_claim_job = AsyncMock(return_value=True)


class FakeAuthClient:
    def __init__(self, *, email: str | None = None) -> None:
        self._email = email
        self.get_user_contacts = AsyncMock(side_effect=self._get_contacts)

    async def _get_contacts(self, user_id):
        return UserContacts(
            user_id=user_id,
            email=self._email,
            push_token=None,
            ws_session_id=None,
        )


class FakeDlqPublisher:
    def __init__(self) -> None:
        self.publish_job = AsyncMock()
        self.publish_raw = AsyncMock()


class FakeEmailSender:
    def __init__(self) -> None:
        self.send = AsyncMock()


class FakePushSender:
    def __init__(self) -> None:
        self.send = AsyncMock()


class FakeWsSender:
    def __init__(self) -> None:
        self.send = AsyncMock()


def make_notification_job(
    *,
    channel: NotificationChannel = NotificationChannel.EMAIL,
) -> NotificationJob:
    now = datetime.now(timezone.utc)

    return NotificationJob(
        job_id=uuid4(),
        user_id=uuid4(),
        channel=channel,
        template_code="welcome_email",
        locale="ru",
        data={"name": "User"},
        meta=NotificationMeta(
            event_type="user_registered",
            event_id=uuid4(),
            campaign_id=None,
            priority="normal",
        ),
        created_at=now,
        send_after=None,
        expires_at=None,
    )


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def template_repo() -> FakeTemplateRepo:
    return FakeTemplateRepo()


@pytest.fixture
def delivery_repo() -> FakeDeliveryRepo:
    return FakeDeliveryRepo()


@pytest.fixture
def dlq_publisher() -> FakeDlqPublisher:
    return FakeDlqPublisher()


@pytest.fixture
def email_sender() -> FakeEmailSender:
    return FakeEmailSender()


@pytest.fixture
def push_sender() -> FakePushSender:
    return FakePushSender()


@pytest.fixture
def ws_sender() -> FakeWsSender:
    return FakeWsSender()


@pytest.fixture
def job_email() -> NotificationJob:
    return make_notification_job(channel=NotificationChannel.EMAIL)
