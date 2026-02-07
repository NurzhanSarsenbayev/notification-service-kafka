from datetime import datetime, timedelta, timezone
from uuid import UUID

from notifications.campaign_scheduler.service.scheduler_service import is_campaign_due
from notifications.campaign_scheduler.repositories.campaigns_repo import Campaign


def _campaign(**kwargs) -> Campaign:
    defaults = dict(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        template_code="test_template",
        segment_id="test_segment",
        schedule_cron="* * * * *",
        status="ACTIVE",
        last_triggered_at=None,
        runs_count=0,
        max_runs=None,
    )
    defaults.update(kwargs)
    return Campaign(**defaults)


def test_first_run_due_immediately():
    now = datetime.now(timezone.utc)
    c = _campaign(last_triggered_at=None)

    assert is_campaign_due(c, now) is True


def test_not_due_when_max_runs_reached():
    now = datetime.now(timezone.utc)
    c = _campaign(runs_count=3, max_runs=3)

    assert is_campaign_due(c, now) is False


def test_due_after_cron_interval():
    now = datetime.now(timezone.utc)
    # last_triggered_at is one minute ago, cron="* * * * *" -> due
    c = _campaign(last_triggered_at=now - timedelta(minutes=1))

    assert is_campaign_due(c, now) is True


def test_not_due_before_next_cron():
    now = datetime(2026, 2, 5, 11, 48, 10, tzinfo=timezone.utc)
    c = _campaign(last_triggered_at=now - timedelta(seconds=10))  # 11:48:00
    assert is_campaign_due(c, now) is False
