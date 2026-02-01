# Notification Delivery Service

Fault-tolerant notification delivery service built around Kafka with idempotent processing,
explicit retry semantics, and dead-letter handling.

This project demonstrates how to reliably deliver notifications in a distributed backend system
without message loss, duplicate deliveries, or hidden failures.

---

## Problem

Notification delivery looks simple until you consider real-world constraints:

- messages can be delivered more than once
- workers can crash mid-processing
- downstream providers can fail temporarily or permanently
- retries can cause duplicates
- failures must be observable and debuggable

A naive "send notification" approach quickly leads to data inconsistencies and lost events.

---

## Solution Overview

This service implements a production-inspired notification pipeline with explicit delivery semantics:

- asynchronous processing via Kafka
- idempotent delivery guarantees
- retry and backoff for transient failures
- dead-letter queue (DLQ) for non-recoverable errors
- separation of API, worker, and scheduler responsibilities

The system favors **at-least-once delivery with idempotent handling** over fragile exactly-once guarantees.

---

## Architecture

High-level components:

- **API**  
  Accepts notification jobs and persists them for asynchronous processing.

- **Kafka**  
  Acts as the transport layer between producers and workers.

- **Worker**  
  Consumes notification jobs, applies retry logic, ensures idempotency, and performs delivery.

- **Delivery State (PostgreSQL)**  
  Stores delivery attempts and ensures duplicate messages are not re-processed.

- **Scheduler**  
  Periodically scans for pending or retryable jobs.

- **Mailpit**  
  Used as a demo delivery sink for local development.

An architectural diagram is available in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Delivery Semantics

- **Delivery guarantee:** at-least-once
- **Idempotency:** enforced at the database level
- **Retries:** enabled for transient failures with bounded attempts
- **Dead Letter Queue (DLQ):** non-retryable failures are captured with context
- **Crash safety:** worker restarts do not cause duplicate deliveries

These trade-offs are intentional and documented.

---

## Demo

A complete end-to-end demo is available here:

👉 [`docs/DEMO.md`](docs/DEMO.md)

The demo walks through:

1. Starting the local infrastructure
2. Creating a notification job
3. Observing delivery via Mailpit
4. Inspecting delivery state in the database
5. Triggering retry and DLQ scenarios

The full demo takes ~5 minutes.

---

## Limitations

This project is an MVP focused on delivery semantics:

- single notification channel (email demo)
- no external provider integrations
- no exactly-once guarantees (by design)
- no Kubernetes deployment

These limitations are explicit and intentional.

---

## Tech Stack

- Python 3.11
- FastAPI
- Kafka
- PostgreSQL
- Docker Compose
- pytest

---

## Why This Project Exists

This repository is part of a personal portfolio focused on backend and platform engineering.
The goal is to demonstrate system design decisions, reliability trade-offs, and production-oriented thinking
rather than feature completeness.
```

---