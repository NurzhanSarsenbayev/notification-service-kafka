import uuid

import pytest
from starlette.testclient import TestClient


@pytest.mark.asyncio
async def test_post_event_accepted(api_client: TestClient):
    event_payload = {
        "event_id": str(uuid.uuid4()),
        "event_type": "user_registered",
        "source": "auth_service",
        "occurred_at": "2025-11-14T12:34:56Z",
        "payload": {
            "user_id": str(uuid.uuid4()),
            "registration_channel": "web",
            "locale": "ru",
            "user_agent": "Mozilla/5.0",
        },
    }

    resp = api_client.post("/api/v1/events", json=event_payload)
    assert resp.status_code == 202, resp.text

    data = resp.json()
    assert data["status"] == "accepted"
    assert data["event_id"] == event_payload["event_id"]
    assert data["jobs_count"] == 1
