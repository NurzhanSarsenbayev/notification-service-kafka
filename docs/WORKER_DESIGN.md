# Worker Design

This document describes the internal design of the Notification Worker component,
its responsibilities, and processing flow.

The focus is on architectural decisions and execution model rather than
configuration or operational instructions.

---

## Responsibilities

The Notification Worker is a background component responsible for executing
notification delivery jobs produced by the API.

At a high level, the worker:

- consumes notification jobs from Kafka
- applies delivery rules and scheduling constraints
- performs idempotent delivery
- records delivery outcomes
- routes non-recoverable failures to a Dead Letter Queue (DLQ)

The worker does not expose an HTTP API and operates asynchronously.

---

## High-Level Architecture

The worker is composed of a small set of focused components:

- Kafka consumer
- job processor
- retry and scheduling logic
- delivery channel handlers
- delivery state persistence

Each component has a single responsibility and is designed to be replaceable.

---

## Processing Flow

The worker processes each notification job using a deterministic execution flow.

At a high level, job processing consists of:

- consuming a notification job from Kafka
- validating and deserializing the payload
- enforcing idempotency via persisted delivery state
- evaluating scheduling constraints (`send_after`, `expires_at`)
- routing the job to the appropriate delivery channel
- attempting delivery and persisting the outcome
- retrying or routing failures to the DLQ

The exact delivery guarantees and retry semantics are described in
[`DELIVERY_SEMANTICS.md`](DELIVERY_SEMANTICS.md).

---

## Idempotency and State Management

Idempotency is enforced via persisted delivery state.

Before processing a job, the worker checks whether a terminal delivery state
already exists for the given job identifier.

If so, the job is skipped and no side effects are produced.

This allows safe re-processing and message re-delivery without duplicating
external actions.

---

## Retry and Failure Handling

The worker applies retry logic for transient failures during delivery.

Retry behavior is:

- bounded
- stateful
- explicit and observable

Once retry attempts are exhausted, the job is considered permanently failed
and is routed to the Dead Letter Queue.

Detailed retry behavior is documented in
[`DELIVERY_SEMANTICS.md`](DELIVERY_SEMANTICS.md).

---

## Delivery Channels

Delivery logic is encapsulated behind channel-specific handlers.

The worker routes each job to the appropriate handler based on its channel type.

This design allows new delivery channels to be added without changing
the core processing pipeline.

Channel handlers implement a common interface, allowing new delivery channels
to be introduced without modifying the core worker logic.

---

## Dead Letter Queue (DLQ)

Jobs that cannot be successfully processed are published to a Dead Letter Queue.

The DLQ provides:

- visibility into permanent failures
- a mechanism for inspection and analysis
- a potential reprocessing entry point

Publishing to the DLQ is an explicit terminal outcome.

DLQ messages include enough context to support debugging and post-mortem analysis.

---

## Scalability Model

The worker is designed to scale horizontally.

Multiple worker instances can join the same Kafka consumer group,
allowing Kafka to distribute partitions across instances.

The delivery model remains at-least-once, with idempotency ensuring
safe parallel processing.

---

## Design Trade-offs

The worker design intentionally favors:

- simplicity over complex transactional guarantees
- explicit state over implicit behavior
- observability over hidden retries

Exactly-once delivery semantics are intentionally not implemented,
as they would significantly increase complexity without clear benefit
for this use case.
