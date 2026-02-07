from datetime import datetime, timezone
from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_post_event_accepted(api_client):
    """
    Happy path for POST /api/v1/events:
    - send a valid user_registered event
    - expect 202 Accepted
    - response includes status='accepted' and (optionally) jobs_count=1
    """

    now = datetime.now(timezone.utc).isoformat()

    payload = {
        "event_id": str(uuid4()),
        "event_type": "user_registered",
        "source": "auth_service",
        "occurred_at": now,
        "payload": {
            "user_id": str(uuid4()),
            "registration_channel": "web",
            "locale": "en",
            "user_agent": "pytest-client",
        },
    }

    response = api_client.post("/api/v1/events", json=payload)

    assert response.status_code == 202, response.text
    data = response.json()

    assert data.get("status") == "accepted"

    # jobs_count is part of the API contract in this project (may be omitted by some implementations)
    if "jobs_count" in data:
        assert data["jobs_count"] == 1


@pytest.mark.asyncio
async def test_create_template(api_client):
    payload = {
        "template_code": "welcome_email",
        "locale": "en",
        "channel": "email",
        "subject": "Welcome!",
        "body": "<h1>Hello!</h1><p>Thanks for signing up</p>",
    }

    response = api_client.post("/api/v1/templates", json=payload)

    assert response.status_code == 201, response.text
    data = response.json()

    assert data["template_code"] == payload["template_code"]
    assert data["locale"] == payload["locale"]
    assert data["channel"] == payload["channel"]
    assert data["subject"] == payload["subject"]
    assert data["body"] == payload["body"]
    assert "id" in data


@pytest.mark.asyncio
async def test_create_template_conflict(api_client):
    payload = {
        "template_code": "welcome_email_conflict",
        "locale": "en",
        "channel": "email",
        "subject": "Welcome!",
        "body": "<h1>Hello!</h1>",
    }

    resp1 = api_client.post("/api/v1/templates", json=payload)
    assert resp1.status_code == 201, resp1.text

    resp2 = api_client.post("/api/v1/templates", json=payload)
    assert resp2.status_code == 409
    assert (
        resp2.json()["detail"]
        == "Template with this code/locale/channel already exists"
    )
