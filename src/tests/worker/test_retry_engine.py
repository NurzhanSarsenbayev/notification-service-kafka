import pytest

from notifications.worker.processor.retry_engine import attempt_with_retries
from tests.worker.conftest import (
    FakeDeliveryRepo,
    FakeDlqPublisher,
    make_notification_job,
)


@pytest.mark.asyncio
async def test_retry_engine_retry_then_success():
    job = make_notification_job()
    delivery_repo = FakeDeliveryRepo()
    dlq_publisher = FakeDlqPublisher()

    state = {"attempt": 0}

    async def attempt_send_fn(j):
        state["attempt"] += 1
        if state["attempt"] == 1:
            raise RuntimeError("temporary error")

    retry_delays = [0.0, 0.0, 0.0]

    await attempt_with_retries(
        job=job,
        existing_attempts=0,
        max_attempts=3,
        retry_delays=retry_delays,
        attempt_send_fn=attempt_send_fn,
        delivery_repo=delivery_repo,
        dlq_publisher=dlq_publisher,
    )

    assert delivery_repo.save_status.await_count >= 2
    last_call = delivery_repo.save_status.await_args_list[-1]
    last_kwargs = last_call[1]
    assert last_kwargs["status"] == "SENT"
    dlq_publisher.publish_job.assert_not_awaited()


@pytest.mark.asyncio
async def test_retry_engine_exhausts_attempts_and_goes_to_dlq():
    job = make_notification_job()
    delivery_repo = FakeDeliveryRepo()
    dlq_publisher = FakeDlqPublisher()

    async def attempt_send_fn(j):
        raise RuntimeError("permanent error")

    retry_delays = [0.0, 0.0]

    await attempt_with_retries(
        job=job,
        existing_attempts=0,
        max_attempts=2,
        retry_delays=retry_delays,
        attempt_send_fn=attempt_send_fn,
        delivery_repo=delivery_repo,
        dlq_publisher=dlq_publisher,
    )

    assert delivery_repo.save_status.await_count >= 2
    dlq_publisher.publish_job.assert_awaited_once()
