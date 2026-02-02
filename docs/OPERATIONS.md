# Operations

This document describes how to observe, debug, and operate the Notification Service
in a local or development environment.

It focuses on practical workflows for identifying delivery issues,
inspecting system state, and understanding failure scenarios.

---

## Service Health

This section describes how to verify that core components are running.

### API

- The API exposes a health endpoint for basic liveness checks.
- API availability can be verified via the OpenAPI UI.

### Worker

- The worker runs as a background process without an HTTP interface.
- Worker health is inferred from logs and Kafka consumption activity.

### Kafka

- Kafka availability is required for asynchronous processing.
- If Kafka is unavailable, message processing is paused until it recovers.

---

## Logging

Logs are the primary source of operational visibility.

### Where to Look

- API logs: request validation, job creation, publishing failures
- Worker logs: job processing, retries, delivery attempts, failures

### Correlation Identifiers

The following identifiers are useful for tracing a notification through the system:

- `job_id`
- `event_id`
- delivery status

Searching logs by these identifiers allows correlating API requests,
worker execution, and delivery outcomes.

---

## Delivery State Inspection

Delivery state is persisted in the database and represents the source of truth
for notification outcomes.

### Delivery State Table

The delivery state table records:

- the current delivery status
- the number of attempts
- timestamps of delivery attempts

Inspecting delivery state allows determining whether a notification:

- was delivered successfully
- is currently retrying
- failed permanently
- expired before delivery

---

## Dead Letter Queue (DLQ)

The Dead Letter Queue contains jobs that could not be processed successfully.

### When Messages End Up in the DLQ

Jobs are routed to the DLQ when:

- retry attempts are exhausted
- payloads are invalid or cannot be processed
- delivery fails permanently

### Inspecting DLQ Messages

DLQ messages provide context about the failure and can be used to:

- debug delivery issues
- identify systemic problems
- manually reprocess jobs if needed

---

## Mailpit (Local Delivery)

Mailpit is used as a local email delivery sink.

### Accessing Mailpit

- The Mailpit UI exposes received emails in the local environment.
- It can be used to verify that email notifications are delivered correctly.

### Common Issues

- missing emails due to delivery failures
- incorrect templates or rendered content
- misconfigured local environment

---

## Common Failure Scenarios

This section describes typical failure modes encountered during development.

### Kafka Unavailable

- Jobs cannot be consumed or published.
- Processing resumes automatically once Kafka is available again.

### Invalid Job Payload

- Jobs with invalid structure or data may be skipped or routed to the DLQ.

### Missing User Contact Data

- Delivery may fail if required contact information is unavailable.
- Such failures are visible in logs and delivery state.

### Template Resolution Failures

- Missing or invalid templates result in delivery failures.
- These failures may trigger retries or DLQ routing.

---

## Debugging Checklist

When a notification is not delivered:

1. Verify that all services are running.
2. Check API logs for job creation errors.
3. Check worker logs for processing attempts.
4. Inspect delivery state in the database.
5. Inspect DLQ messages, if present.
6. Verify delivery via Mailpit.

This checklist provides a systematic approach to diagnosing delivery issues.

---

## Scope and Limitations

This document focuses on local and development environments.

Production-grade observability, alerting, and monitoring integrations
are considered out of scope for this project.
