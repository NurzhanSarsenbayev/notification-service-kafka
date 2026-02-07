from datetime import datetime, timezone
from typing import List, Type, TypeVar
from uuid import uuid4

from fastapi import HTTPException, status
from pydantic import BaseModel

from notifications.common.kafka import KafkaNotificationJobPublisher
from notifications.common.schemas import (
    NotificationChannel,
    NotificationJob,
    NotificationMeta,
)
from notifications.notifications_api.schemas.event import (
    BaseEvent,
    EventType,
    UserRegisteredEventPayload,
    NewFilmReleasedEventPayload,
    CampaignTriggeredEventPayload,
)

TPayload = TypeVar("TPayload", bound=BaseModel)


class NotificationService:
    """Maps Event -> NotificationJob and publishes jobs to Kafka."""

    def __init__(self, job_publisher: KafkaNotificationJobPublisher) -> None:
        self._job_publisher = job_publisher

    async def handle_event(self, event: BaseEvent) -> int:
        """API entry point.

        - validates payload via _map_* helpers
        - builds a list of NotificationJob objects
        - publishes each job to Kafka
        - returns the number of enqueued jobs
        """
        jobs = self._map_event_to_jobs(event)

        for job in jobs:
            # Pydantic v2: model_dump(mode="json") produces JSON-serializable values.
            await self._job_publisher.publish_job(job.model_dump(mode="json"))

        return len(jobs)

    def _map_event_to_jobs(self, event: BaseEvent) -> List[NotificationJob]:
        now = datetime.now(timezone.utc)

        if event.event_type == EventType.USER_REGISTERED:
            return self._map_user_registered(event, now)

        if event.event_type == EventType.NEW_FILM_RELEASED:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Event type 'new_film_released' is not implemented in this MVP",
            )

        if event.event_type == EventType.CAMPAIGN_TRIGGERED:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Event type 'campaign_triggered' is not implemented in this MVP",
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported event_type: {event.event_type}",
        )

    def _parse_payload(
        self,
        event: BaseEvent,
        payload_cls: Type[TPayload],
        context: str,
    ) -> TPayload:
        """Validate and parse an event payload.

        If the payload does not match the expected schema, returns HTTP 400.
        """
        try:
            return payload_cls(**event.payload)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid payload for {context}: {exc}",
            ) from exc

    def _map_user_registered(
        self, event: BaseEvent, now: datetime
    ) -> List[NotificationJob]:
        payload = self._parse_payload(
            event=event,
            payload_cls=UserRegisteredEventPayload,
            context="user_registered",
        )

        job = NotificationJob(
            job_id=uuid4(),
            user_id=payload.user_id,
            channel=NotificationChannel.EMAIL,
            template_code="welcome_email",
            locale=payload.locale,
            data={
                "registration_channel": payload.registration_channel,
                "user_agent": payload.user_agent,
            },
            meta=NotificationMeta(
                event_type=event.event_type.value,
                event_id=event.event_id,
                campaign_id=None,
            ),
            created_at=now,
        )
        return [job]

    def _map_new_film_released(
        self, event: BaseEvent, now: datetime
    ) -> List[NotificationJob]:
        """Template for a future implementation of the 'new_film_released' event."""
        _ = self._parse_payload(
            event=event,
            payload_cls=NewFilmReleasedEventPayload,
            context="new_film_released",
        )
        # TODO: select users by segment and generate jobs.
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="new_film_released notifications are not implemented in this MVP",
        )

    def _map_campaign_triggered(
        self, event: BaseEvent, now: datetime
    ) -> List[NotificationJob]:
        """Template for a future implementation of the 'campaign_triggered' event."""
        _ = self._parse_payload(
            event=event,
            payload_cls=CampaignTriggeredEventPayload,
            context="campaign_triggered",
        )
        # TODO: select users by campaign/segment and generate jobs.
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="campaign_triggered notifications are not implemented in this MVP",
        )
