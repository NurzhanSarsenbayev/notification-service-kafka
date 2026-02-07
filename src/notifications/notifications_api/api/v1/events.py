from fastapi import APIRouter, Depends, status

from notifications.notifications_api.schemas.event import BaseEvent as Event
from notifications.notifications_api.services.notification_service import (
    NotificationService,
)
from notifications.notifications_api.utils.dependencies import get_notification_service

router = APIRouter(prefix="/events", tags=["events"])


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Accept an external event and enqueue notification jobs",
)
async def receive_event(
    event: Event,
    service: NotificationService = Depends(get_notification_service),
):
    jobs_count = await service.handle_event(event)
    return {
        "status": "accepted",
        "event_id": str(event.event_id),
        "jobs_count": jobs_count,
    }
