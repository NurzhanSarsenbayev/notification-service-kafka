from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from notifications.common.db import get_db_session
from notifications.common.kafka import kafka_publisher
from notifications.notifications_api.repositories.templates import TemplateRepository
from notifications.notifications_api.services.notification_service import (
    NotificationService,
)


async def get_db(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncSession:
    return session


def get_template_repository(
    session: AsyncSession = Depends(get_db),
) -> TemplateRepository:
    return TemplateRepository(session=session)


def get_notification_service() -> NotificationService:
    # publisher is global; it is started/stopped in the lifespan hook
    return NotificationService(job_publisher=kafka_publisher)
