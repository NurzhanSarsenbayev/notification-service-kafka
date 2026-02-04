from uuid import uuid4

from notifications.common.schemas import NotificationChannel
from notifications.worker.processor.status_writer import _ensure_channel


class _DummyJob:
    def __init__(self, channel):
        self.job_id = uuid4()
        self.channel = channel


def test_ensure_channel_enum_email():
    job = _DummyJob(NotificationChannel.EMAIL)
    assert _ensure_channel(job) == "email"


def test_ensure_channel_string_normalized():
    job = _DummyJob("PuSh")
    assert _ensure_channel(job) == "push"


def test_ensure_channel_unknown_string_fallback():
    job = _DummyJob("WTF")
    assert _ensure_channel(job) == "email"


def test_ensure_channel_missing_channel_attr():
    class JobNoChannel:
        def __init__(self):
            self.job_id = uuid4()

    job = JobNoChannel()
    assert _ensure_channel(job) == "email"
