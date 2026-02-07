# Tests

This project tests operationally critical behavior of a notification system:
API → Kafka → background processing (Worker / Campaign Scheduler) → delivery.

The goal is confidence in delivery semantics and deterministic behavior,
not 100% line coverage.

## What tests guarantee (behavioral invariants)

### API
- Accepts valid events and templates and returns stable HTTP contracts
- Rejects invalid payloads with predictable validation errors
- Keeps API handlers stable as integration points for Scheduler and external services

### Worker
- Retry loop is deterministic:
  - attempts are counted
  - statuses are written on each failure
  - DLQ publish happens on final failure
- Retry budget is bounded and configured via settings:
  - `max_attempts = 3`
  - `retry_delays = 1, 3, 10 seconds` (default)
- Status writing is consistent (SENT / FAILED with attempt count and error message)

### Campaign Scheduler
- Campaign triggering logic is deterministic:
  - `is_campaign_due(...)` behaves correctly across edge cases (time windows / last_triggered_at)

## What tests do NOT guarantee (explicit trade-offs)

- Performance under load (throughput/latency)
- Kafka/PostgreSQL correctness (we rely on upstream systems)
- Full end-to-end exactly-once delivery guarantees (distributed systems limitation)

## Test layout (high level)

- API tests: events/templates endpoints
- Worker tests: retry engine, status writer, job processing
- Scheduler tests: campaign due logic

(We intentionally document behavior, not file-by-file lists.)

## How to run (real project commands)

### Local unit tests (no docker required):

```bash
make test-local
```
### Local lint + formatting checks:

```bash
make lint
make fmt-check
```

### Docker-based tests
(recommended, closest to real environment):

```bash
make test
```
(Alternative name kept for compatibility: make test-e2e)

### End-to-end verification (demo)
This is the fastest way to validate the full pipeline manually:

```bash
cp .env.sample .env
make up
make ready
make demo
```
Expected outcome:

- Worker consumes jobs from Kafka and processes them

- Mailpit shows delivered email messages

### Mailpit UI:

http://localhost:18025 (default; configurable via .env.sample)

### Debugging failures
Service logs:

```bash
make logs-api
make logs-worker
make logs-scheduler
```
If the worker looks stuck:

- check Kafka container health and worker logs

- confirm readiness: make ready

- inspect DLQ publishing logs for final failures

### Database inspection:

```bash
make psql
```

---