from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

import httpx
from croniter import croniter

from notifications.common.config import settings
from notifications.campaign_scheduler.repositories.campaigns_repo import (
    Campaign,
    CampaignRepository)
from notifications.campaign_scheduler.startup import (
    create_db_pool,
    create_http_client)
from notifications.notifications_api.schemas.event import (
    BaseEvent,
    CampaignTriggeredEventPayload,
    CampaignTriggeredSegment,
    EventType,
)

logger = logging.getLogger(__name__)


def is_campaign_due(campaign: Campaign, now: datetime) -> bool:
    """Determine whether a campaign should run at `now` based on its cron schedule.

    Rules:
    - if max_runs is set and runs_count >= max_runs -> do not run anymore
    - if last_triggered_at is NULL -> first run happens immediately
    - otherwise -> compute the next run time from last_triggered_at using cron
    """
    if (campaign.max_runs is not None
            and campaign.runs_count >= campaign.max_runs):
        return False

    if campaign.last_triggered_at is None:
        # first run: trigger immediately
        return True

    base = campaign.last_triggered_at

    try:
        it = croniter(campaign.schedule_cron, base)
        next_run = it.get_next(datetime)
    except Exception:
        logger.error(
            "Invalid cron expression for campaign %s: %s",
            campaign.id,
            campaign.schedule_cron,
        )
        return False

    return next_run <= now


def _build_event(
    campaign_id: UUID,
    template_code: str,
    segment_id: str,
) -> BaseEvent:
    """Build a BaseEvent for the campaign_triggered event."""
    payload = CampaignTriggeredEventPayload(
        campaign_id=campaign_id,
        template_code=template_code,
        channels=["email"],  # MVP: email only
        segment=CampaignTriggeredSegment(segment_id=segment_id),
    )

    return BaseEvent(
        event_id=uuid4(),
        event_type=EventType.CAMPAIGN_TRIGGERED,
        source="campaign_scheduler",
        occurred_at=datetime.now(timezone.utc),
        payload=payload.model_dump(),
    )


async def _process_campaign(
    campaign: Campaign,
    client: httpx.AsyncClient,
    repo: CampaignRepository,
    now: datetime,
) -> None:
    """Process a single campaign within one scheduler tick."""
    if not is_campaign_due(campaign, now):
        logger.debug(
            "Campaign %s is not due yet (cron=%s, last_triggered_at=%s, "
            "runs_count=%s, max_runs=%s)",
            campaign.id,
            campaign.schedule_cron,
            campaign.last_triggered_at,
            campaign.runs_count,
            campaign.max_runs,
        )
        return

    event = _build_event(
        campaign_id=campaign.id,
        template_code=campaign.template_code,
        segment_id=campaign.segment_id,
    )
    url = f"{settings.api_base_url}{settings.api_v1_prefix}/events"

    try:
        logger.info("Triggering campaign %s via %s", campaign.id, url)
        resp = await client.post(url, json=event.model_dump(mode="json"))
        resp.raise_for_status()
        logger.info(
            "Campaign %s triggered successfully, API responded %s",
            campaign.id,
            resp.status_code,
        )
    except httpx.HTTPError as exc:
        logger.error(
            "HTTP error while triggering campaign %s: %s",
            campaign.id,
            exc,
            exc_info=True,
        )
        return
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Unexpected error while triggering campaign %s: %s",
            campaign.id,
            exc,
        )
        return

    try:
        await repo.mark_campaign_triggered(campaign.id)
        logger.info("Campaign %s marked as triggered at %s", campaign.id, now)
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Failed to update campaign %s after trigger: %s",
            campaign.id,
            exc,
        )


async def _process_tick(
    repo: CampaignRepository,
    client: httpx.AsyncClient,
    poll_interval: int,
) -> None:
    """Run one full scheduler tick: load campaigns and process them."""
    now = datetime.now(timezone.utc)

    try:
        campaigns = await repo.get_active_campaigns()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to fetch active campaigns: %s", exc)
        await asyncio.sleep(poll_interval)
        return

    if not campaigns:
        logger.debug("No active campaigns found on this tick")
        await asyncio.sleep(poll_interval)
        return

    logger.info("Found %s active campaigns", len(campaigns))

    for campaign in campaigns:
        await _process_campaign(campaign, client, repo, now)

    await asyncio.sleep(poll_interval)


async def run_scheduler() -> None:
    """Main scheduler loop.

    - initializes resources (DB pool + HTTP client)
    - runs an infinite loop calling _process_tick()
    """
    poll_interval = settings.scheduler_poll_interval_seconds

    logger.info(
        "Campaign scheduler starting: api_base_url=%s, poll_interval=%s",
        settings.api_base_url,
        poll_interval,
    )

    pool = await create_db_pool()
    client = create_http_client()
    repo = CampaignRepository(pool)

    try:
        while True:
            await _process_tick(repo, client, poll_interval)
    finally:
        logger.info("Closing scheduler resources...")
        await client.aclose()
        await pool.close()
        logger.info("Scheduler resources closed")
