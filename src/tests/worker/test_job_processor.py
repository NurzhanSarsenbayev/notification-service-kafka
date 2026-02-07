import pytest

from notifications.worker.processor.job_processor import JobProcessor
from tests.worker.conftest import FakeAuthClient


@pytest.mark.asyncio
async def test_job_processor_happy_email(
    settings,
    template_repo,
    delivery_repo,
    dlq_publisher,
    email_sender,
    push_sender,
    ws_sender,
    job_email,
):
    """
    Happy path:
    - no existing record in delivery_repo;
    - template is found;
    - AuthClient returns an email;
    - EmailSender is called;
    - delivery status SENT is persisted;
    - DLQ is not used.
    """

    auth_client = FakeAuthClient(email="user@example.com")

    processor = JobProcessor(
        settings=settings,
        template_repo=template_repo,
        delivery_repo=delivery_repo,
        auth_client=auth_client,
        email_sender=email_sender,
        push_sender=push_sender,
        ws_sender=ws_sender,
        dlq_publisher=dlq_publisher,
    )

    await processor.handle_job(job_email)

    email_sender.send.assert_awaited_once()
    call = email_sender.send.await_args
    assert call.kwargs["to"] == "user@example.com"
    assert "User" in call.kwargs["subject"]
    assert "User" in call.kwargs["body"]

    statuses = [
        kwargs["status"] for _, kwargs in delivery_repo.save_status.await_args_list
    ]
    assert "SENT" in statuses

    dlq_publisher.publish_job.assert_not_awaited()
    dlq_publisher.publish_raw.assert_not_awaited()
