from __future__ import annotations

import logging

from ..auth import AuthClient
from ..dlq import DlqPublisher
from ..repositories import (
    TemplateRepository,
    NotificationDeliveryRepository,
)
from ..senders import EmailSender, PushSender, WsSender
from .timing import handle_expiration_if_needed, wait_send_after_if_needed
from .retry_engine import attempt_with_retries

from src.notifications.common.config import Settings

from src.notifications.common.schemas import (
    NotificationStatus,
    NotificationChannel,
    NotificationJob,
)

logger = logging.getLogger(__name__)


class JobProcessor:
    """Тонкий оркестратор обработки NotificationJob."""

    def __init__(
        self,
        settings: Settings,
        template_repo: TemplateRepository,
        delivery_repo: NotificationDeliveryRepository,
        auth_client: AuthClient,
        email_sender: EmailSender,
        push_sender: PushSender,
        ws_sender: WsSender,
        dlq_publisher: DlqPublisher,
    ) -> None:
        self.settings = settings
        self.template_repo = template_repo
        self.delivery_repo = delivery_repo
        self.auth_client = auth_client
        self.email_sender = email_sender
        self.push_sender = push_sender
        self.ws_sender = ws_sender
        self.dlq = dlq_publisher

    # -------------------- публичный сценарий --------------------

    async def handle_job(self, job: NotificationJob) -> None:
        """Главная точка входа. Здесь только сценарий, без деталей."""
        existing = await self._get_existing(job)
        if self._should_skip(existing):
            return

        # 1. Expiration
        expired = await handle_expiration_if_needed(
            job=job,
            existing=existing,
            delivery_repo=self.delivery_repo,
        )
        if expired:
            return

        # 2. send_after (отложенная отправка)
        await wait_send_after_if_needed(
            job=job,
            max_send_delay_seconds=self.settings.max_send_delay_seconds,
        )

        # 3. Retry-цикл
        existing_attempts = existing.attempts if existing else 0
        await attempt_with_retries(
            job=job,
            existing_attempts=existing_attempts,
            max_attempts=self.settings.max_attempts,
            retry_delays=self.settings.retry_delays_seconds,
            attempt_send_fn=self._attempt_send,
            delivery_repo=self.delivery_repo,
            dlq_publisher=self.dlq,
        )

    # -------------------- helpers --------------------

    async def _get_existing(self, job: NotificationJob):
        return await self.delivery_repo.get_by_job_id(job.job_id)

    def _should_skip(self, existing) -> bool:
        """Решаем, нужно ли вообще обрабатывать job, если она уже есть в БД."""
        if not existing:
            return False

        # existing.status — строка из БД, Enum — NotificationStatus
        if existing.status == NotificationStatus.SENT.value:
            logger.info("Job %s already SENT — skipping", existing.job_id)
            return True

        if (
            existing.status in (
                NotificationStatus.EXPIRED.value,
                NotificationStatus.FAILED.value,
            )
            and existing.attempts >= self.settings.max_attempts
        ):
            logger.info(
                "Job %s already final (%s, attempts=%s) — skipping",
                existing.job_id,
                existing.status,
                existing.attempts,
            )
            return True

        return False

    @staticmethod
    def _normalize_channel(channel: NotificationChannel | str) -> str:
        """Приводим канал к строке (для БД / логов / шаблонов)."""
        if isinstance(channel, NotificationChannel):
            return channel.value
        return str(channel)

    async def _attempt_send(self, job: NotificationJob) -> None:
        """Одна попытка отправки (без retry-логики)."""

        # Приводим канал к строке, с учётом Enum/str
        channel_str = self._normalize_channel(job.channel)

        # 1. Контакты пользователя
        contacts = await self.auth_client.get_user_contacts(job.user_id)

        # 2. Шаблон
        template = await self.template_repo.get_template(
            template_code=job.template_code,
            locale=job.locale,
            channel=channel_str,
        )
        if not template:
            raise RuntimeError(
                f"Template not found: code={job.template_code} "
                f"locale={job.locale} channel={channel_str}"
            )

        # 3. Рендер (защита от None в subject)
        subject_template = template.subject or ""
        body_template = template.body or ""

        try:
            subject = subject_template.format(**job.data)
            body = body_template.format(**job.data)
        except KeyError as exc:
            raise RuntimeError(f"Missing var in template: {exc}") from exc

        # 4. Маршрутизация по каналам
        if channel_str == NotificationChannel.EMAIL.value:
            if not getattr(contacts, "email", None):
                raise RuntimeError("User has no email")

            await self.email_sender.send(
                to=contacts.email,
                subject=subject,
                body=body,
            )

        elif channel_str == NotificationChannel.PUSH.value:
            if not getattr(contacts, "push_token", None):
                raise RuntimeError("User has no push token")

            await self.push_sender.send(
                to=contacts.push_token,
                subject=subject,
                body=body,
            )

        elif channel_str == NotificationChannel.WS.value:
            if not getattr(contacts, "ws_session_id", None):
                raise RuntimeError("User has no ws session id")

            await self.ws_sender.send(
                to=contacts.ws_session_id,
                subject=subject,
                body=body,
            )

        else:
            # На будущее, если кто-то пихнёт неизвестный канал
            raise RuntimeError(f"Unsupported channel: {channel_str}")
