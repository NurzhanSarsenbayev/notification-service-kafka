# Notification Service

A production-minded notification service built with FastAPI, Kafka, and PostgreSQL.

Fault-tolerant notification delivery service built around Kafka with idempotent processing,
explicit retry semantics, and dead-letter handling.

---

## What this service does

This service implements a production-inspired notification pipeline with:

- asynchronous processing via Kafka
- idempotent delivery handling
- retry and backoff for transient failures
- dead-letter queue (DLQ) for non-recoverable errors
- separation of API, worker, and scheduler responsibilities

---

## Why it exists (problem statement)

This repository is part of a personal portfolio focused on backend and platform engineering.
The goal is to demonstrate system design decisions, reliability trade-offs, and production-oriented thinking
rather than feature completeness.

In real-world systems, notification delivery is complicated by retries, worker crashes,
and unreliable downstream providers. Naive approaches often lead to duplicates,
lost messages, or silent failures.

---

## High-level architecture

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

## Quickstart (local)

The service is designed to be run locally using Docker Compose.

### Prerequisites

- Docker
- Docker Compose

### Run

```bash
git clone https://github.com/NurzhanSarsenbayev/notifications_sprint_1.git --> change to new link
cd notifications_sprint_1

cp .env.sample .env
docker compose infra/docker-compose.yml up --build
```
### After startup:

API is available at: http://localhost:8000/docs

Mailpit UI is available at: http://localhost:8025

To verify the full notification flow, follow the demo guide:

👉 docs/DEMO.md

---

## Demo / How to verify

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

## Guarantees and trade-offs

- Delivery guarantee: at-least-once
- Idempotency: enforced at the database level
- Retries: enabled for transient failures with bounded attempts
- Dead Letter Queue (DLQ): captures non-retryable failures with context
- Crash safety: worker restarts do not cause duplicate side effects

---

## Repository structure

- src/notifications/notifications_api — FastAPI service
- src/notifications/worker — Kafka consumer and delivery logic
- src/notifications/campaign_scheduler — periodic job scheduler
- infra — Docker Compose and infrastructure configuration
- docs — architecture and operational documentation

---

## Limitations & future work

This project is an MVP focused on delivery semantics:

- single notification channel (email demo)
- no external provider integrations
- no exactly-once guarantees (by design)
- no Kubernetes deployment

These limitations are explicit and intentional.

---
