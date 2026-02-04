from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel

from notifications.common.schemas.notification_enums import NotificationChannel


class EventType(str, Enum):
    CAMPAIGN_TRIGGERED = "campaign_triggered"
    USER_REGISTERED = "user_registered"
    NEW_FILM_ADDED = "new_film_added"
    # other event types can be added here: USER_REGISTERED, PASSWORD_RESET, etc.


class SegmentRef(BaseModel):
    segment_id: str


class CampaignTriggeredEventPayload(BaseModel):
    campaign_id: UUID
    template_code: str
    segment: SegmentRef
    channels: list[NotificationChannel]


class EventIn(BaseModel):
    event_id: UUID
    event_type: EventType
    source: str
    occurred_at: datetime
    payload: dict
