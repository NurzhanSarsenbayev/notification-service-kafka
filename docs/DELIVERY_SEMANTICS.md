# Delivery Semantics

This document describes the delivery guarantees, retry behavior, and failure handling
of the Notification Service.

The system favors explicit, observable delivery semantics over fragile exactly-once guarantees.

---

## Delivery Guarantees

- **Delivery model:** at-least-once
- **Message duplication:** possible
- **Duplicate side effects:** prevented via idempotent processing

The system is designed so that message re-delivery does not result in duplicated
external side effects (such as sending multiple emails).

---

## Idempotency Model

Idempotency is enforced at the persistence layer.

Before processing a notification job, the worker checks the delivery state
associated with the job identifier.

If a terminal delivery state already exists, the job is skipped.

This ensures that repeated processing of the same job does not result
in duplicated external side effects.

---

## Retry Strategy

Retries are applied for transient failures during delivery.

Key characteristics:

- retries are **bounded** by a maximum number of attempts
- delays between attempts are configurable
- retry logic is implemented inside the worker
- retry state is persisted and observable

Retries are not handled by Kafka-level retry topics.
Instead, retry behavior is controlled explicitly by the application.

After each failed attempt, the delivery state is updated.
Once retry attempts are exhausted, the job is considered failed.

---

## Dead Letter Queue (DLQ)

Jobs that cannot be processed successfully after exhausting all retry attempts
are published to a Dead Letter Queue.

The DLQ serves as:

- a record of non-recoverable failures
- a debugging aid
- a mechanism for manual inspection or reprocessing

Publishing to the DLQ is an explicit and observable outcome of the delivery process.

---

## Crash Safety and Re-delivery

The system tolerates worker crashes and restarts.

Because delivery state is persisted before and after each attempt:

- re-delivered messages do not cause duplicate side effects
- interrupted deliveries can be retried safely
- processing can resume after failures without manual intervention

---

## Failure Classification

Failures are classified implicitly based on their behavior:

- **Transient failures:** retried (e.g. temporary provider outage)
- **Permanent failures:** eventually moved to the DLQ
- **Expired jobs:** skipped and marked as expired

Jobs may include scheduling constraints:

- **expires_at:** if the expiration time is reached, the job is marked as expired
  and is not delivered
- **send_after:** delivery is postponed until the specified time

All failure outcomes are persisted and observable.

---

## Trade-offs and Non-Goals

The system intentionally does not aim to provide:

- exactly-once delivery semantics
- transactional guarantees across Kafka and external providers

These trade-offs simplify the system while preserving reliability,
predictable behavior, and debuggability.
