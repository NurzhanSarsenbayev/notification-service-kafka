from datetime import datetime, date
from enum import Enum
from typing import List

from pydantic import BaseModel, Field
from uuid import UUID


class EventType(str, Enum):
    USER_REGISTERED = "user_registered"
    NEW_FILM_RELEASED = "new_film_released"
    CAMPAIGN_TRIGGERED = "campaign_triggered"


# --- payload models ---

class UserRegisteredEventPayload(BaseModel):
    user_id: UUID
    registration_channel: str
    locale: str
    user_agent: str


class NewFilmReleasedTargetSegment(BaseModel):
    by_genres: List[str]
    min_age: int


class NewFilmReleasedEventPayload(BaseModel):
    film_id: UUID
    title: str
    genres: List[str]
    age_rating: str
    release_date: date
    target_segment: NewFilmReleasedTargetSegment


class CampaignTriggeredSegment(BaseModel):
    segment_id: str


class CampaignTriggeredEventPayload(BaseModel):
    campaign_id: UUID
    template_code: str
    channels: List[str]
    segment: CampaignTriggeredSegment


class BaseEvent(BaseModel):
    """Base event envelope (payload-agnostic)."""

    event_id: UUID = Field(..., description="Unique id of the event")
    event_type: EventType = Field(..., description="Type of the event")
    source: str = Field(..., description="Event source (service name)")
    occurred_at: datetime = Field(..., description="When the event happened")
    payload: dict = Field(
        ...,
        description="Event-specific payload (see EVENTS.md)",
    )
