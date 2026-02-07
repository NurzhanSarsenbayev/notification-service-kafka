from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from notifications.common.schemas.notification_enums import (
    NotificationPriority,
    NotificationChannel,
)


class NotificationMeta(BaseModel):
    event_type: str
    event_id: Optional[UUID] = None
    campaign_id: Optional[UUID] = None
    priority: NotificationPriority = NotificationPriority.NORMAL


class NotificationJob(BaseModel):
    job_id: UUID
    user_id: UUID
    channel: NotificationChannel
    template_code: str
    locale: str = "ru"

    data: Dict[str, Any] = Field(default_factory=dict)
    meta: NotificationMeta

    created_at: datetime
    send_after: Optional[datetime] = None
    expires_at: Optional[datetime] = None
