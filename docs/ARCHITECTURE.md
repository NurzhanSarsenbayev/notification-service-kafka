# Architecture

This document describes the high-level architecture of the Notification Service,
including its main components, responsibilities, and data flow.

The focus is on system boundaries and delivery semantics rather than implementation details.

---

## Overview

The Notification Service is built as a set of loosely coupled components connected via Kafka.
It separates request handling, asynchronous processing, and delivery execution
to ensure fault tolerance and observability.

---

## Core Components

### API

The API is responsible for accepting notification requests and persisting them
for asynchronous processing. It does not perform delivery itself.

Responsibilities:
- Validate incoming requests
- Persist notification jobs
- Publish messages to Kafka

---

### Kafka

Kafka acts as the transport and buffering layer between producers and consumers.

Responsibilities:
- Decouple API from workers
- Buffer messages during spikes or failures
- Enable retry and DLQ workflows

---

### Worker

Workers consume notification jobs from Kafka and perform delivery.

Responsibilities:
- Apply retry and backoff logic
- Ensure idempotent processing
- Perform actual delivery (email in demo setup)
- Publish failures to DLQ when needed

---

### Delivery State (PostgreSQL)

PostgreSQL is used to track delivery state and enforce idempotency.

Responsibilities:
- Store delivery attempts
- Prevent duplicate side effects
- Provide visibility into delivery outcomes

---

### Scheduler

The scheduler periodically scans for pending or retryable jobs
and re-enqueues them for processing.

Responsibilities:
- Detect stuck or retryable deliveries
- Trigger re-processing when appropriate

---

## Delivery Semantics

- **Delivery guarantee:** at-least-once
- **Idempotency:** enforced via persisted delivery state
- **Retries:** bounded retries for transient failures
- **Dead Letter Queue (DLQ):** captures non-recoverable errors

These trade-offs are intentional and favor reliability and debuggability
over fragile exactly-once guarantees.

---

## Failure Handling

The system is designed to tolerate:

- worker crashes
- transient delivery provider failures
- message re-delivery
- temporary Kafka unavailability

Failures are explicit and observable via logs, database state, and DLQ.

---

## Non-Goals

This project intentionally does not aim to provide:

- exactly-once delivery semantics
- real-time guarantees
- external provider integrations
- Kubernetes-native deployment

These aspects are considered out of scope for this project.

---
