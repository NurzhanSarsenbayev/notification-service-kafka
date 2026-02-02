# Demo: Notification Delivery Flow

This document demonstrates a minimal end-to-end flow of the notification delivery system.

The goal is to show how a notification job is accepted, processed asynchronously,
delivered idempotently, and tracked in persistent storage.

---

## Prerequisites

- Docker and Docker Compose
- Ports configured via `.env` (see `.env.sample`)

---

## 1. Start infrastructure

```bash
docker compose up -d
````

Wait until all services become healthy.

---

## 2. Submit a notification job

Send a notification request to the API (example payload):

```bash
curl -X POST http://localhost:${API_PORT:-8000}/api/v1/notifications \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-1",
    "email": "user@example.com",
    "subject": "Test notification",
    "body": "Hello from the notification service"
  }'
```

The API responds immediately after persisting the job.

---

## 3. Observe asynchronous processing

* The API produces a Kafka message
* The worker consumes the message
* Delivery is attempted exactly once per logical notification
* Retry logic is applied if needed

Worker logs will show processing progress.

---

## 4. Verify delivery

### Mailpit (demo sink)

Open Mailpit UI:

```
http://localhost:${MAILPIT_UI_PORT:-8025}
```

The notification email should appear there.

---

### Delivery state (PostgreSQL)

Inspect delivery records:

```sql
SELECT * FROM notification_delivery;
```

This table ensures idempotent delivery and prevents duplicates.

---

## 5. Retry and DLQ scenarios

Delivery failures are handled as follows:

* transient errors trigger retries
* non-retryable errors are sent to the dead-letter queue (DLQ)

See retry and failure scenarios in:

* [`docs/TESTS.md`](legacy/TESTS.md)
* [`docs/ARCHITECTURE.md`](ARCHITECTURE.md)

---

## Summary

This demo illustrates:

* asynchronous notification delivery
* at-least-once semantics with idempotent processing
* retry and DLQ handling
* observable and debuggable failure modes
