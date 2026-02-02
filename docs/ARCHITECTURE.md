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

OLD


# 🏛 ARCHITECTURE — Notification Service

Сервис нотификаций объединяет несколько микросервисов онлайн-кинотеатра и отвечает за доставку сообщений пользователям по событиям, которые генерируются другими сервисами.

Архитектура построена вокруг связки:

> **HTTP API → Kafka → Worker → Postgres (+ DLQ)**

---

## 1. 🧩 Основные компоненты

### 1.1. Notification API (FastAPI)

Центральная входная точка сервиса нотификаций.

**Задачи:**

* принимает внешние события `Event` от других сервисов (Auth, Content, UGC, Admin);
* валидирует формат события и `payload`;
* маппит события в одно или несколько заданий `NotificationJob`;
* публикует `NotificationJob` в Kafka-топик `notifications.outbox`;
* предоставляет CRUD по шаблонам письма (`templates`).

**Важно:**

* API **не отправляет уведомления** — он только формирует и публикует задания в очередь.
* В случае недоступности Kafka может работать в «деградирующем» режиме (dummy publisher), логируя job вместо реальной публикации.

---

### 1.2. Kafka

Брокер сообщений, через который связываются API и worker.

**Используемые топики:**

| Топик                  | Назначение                                               |
| ---------------------- | -------------------------------------------------------- |
| `notifications.outbox` | Основная очередь задач `NotificationJob`                 |
| `notifications.dlq`    | Dead Letter Queue: задачи, которые не удалось обработать |

**Особенности реализации в этом проекте:**

* Retry-логика реализована **внутри воркера**, а не через отдельный retry-топик.
* Семантика доставки: **at-least-once** (возможны повторы, которые гасим идемпотентностью по `job_id`).

---

### 1.3. Notification Worker

Отдельный сервис (фоновый процесс), который отвечает за фактическую обработку и доставку уведомлений.

**Задачи:**

1. Чтение сообщений из Kafka-топика `notifications.outbox`.
2. Валидация и десериализация `NotificationJob`.
3. Проверка идемпотентности по `job_id` (по таблице `notification_delivery`).
4. Обработка срока годности уведомления (`expires_at`) и отложенной отправки (`send_after`).
5. Получение контактных данных пользователя через `AuthClient` (сейчас stub).
6. Загрузка шаблона из таблицы `templates`.
7. Рендер сообщения (`subject`, `body`) на основе шаблона и `job.data`.
8. Отправка по нужному каналу (`email` / `push` / `ws`) через соответствующий sender.
9. Запись статуса доставки в таблицу `notification_delivery`.
10. Публикация в DLQ (`notifications.dlq`) при неуспешной обработке.

Worker **не имеет HTTP API** и общается только с Kafka и Postgres.

---

### 1.4. Postgres

Хранилище для:

* шаблонов сообщений (`templates`);
* истории доставок (`notification_delivery`).

Используются разные технологии:

* в API — SQLAlchemy (async engine);
* в worker — `asyncpg` (через пул подключений).

---

### 1.5. Общие компоненты (`notifications.common`)

Общий код, который используется и API, и worker:

* `config` — общие настройки (Kafka, Postgres, retry, send_after и т.д.);
* `schemas` — Pydantic-схемы (в т.ч. `NotificationJob`, `NotificationMeta`, `NotificationChannel`, `NotificationStatus`);
* `db` — создание и прокидывание `AsyncSession` (для API);
* `kafka` — обёртка Kafka-публикатора (`KafkaNotificationJobPublisher`) и dummy-режим.

---

### 1.6. Campaign Scheduler (MVP-задел)

Отдельный компонент (в этом проекте — минимальный костяк), который в будущем:

* будет запускать маркетинговые кампании по расписанию;
* ходить в Notification API или писать job’ы напрямую в Kafka;
* работать с таблицей `campaigns`.

В текущем MVP логика кампаний и сегментации **практически не реализована** — есть только архитектурный задел.

---

## 2. 📂 Структура проекта

Упрощённый вид:

```text
src/
  notifications/
    common/                 # общие настройки/схемы/обёртки
      config.py
      db.py
      kafka.py
      schemas/
        notification_job.py
        notification_enums.py
        ...
    notifications_api/      # HTTP API
      main.py
      api/v1/
        events.py           # POST /api/v1/events
        templates.py        # CRUD по шаблонам
      services/
        notification_service.py  # Event → NotificationJob → publish
      repositories/
        templates.py
      schemas/
        event.py
        template.py
      utils/
        dependencies.py
    worker/                 # Notification Worker
      main.py
      startup.py            # создание Kafka producer и PG pool
      consumer/
        kafka_consumer.py   # чтение job из Kafka
      processor/
        job_processor.py    # оркестрация обработки job
        retry_engine.py     # глобальный retry-цикл
        status_writer.py    # запись статусов в БД
        timing.py           # send_after / expires_at
      repositories/
        template_repo.py
        notification_delivery_repo.py
      senders/
        base.py             # интерфейс BaseSender
        email_sender.py
        push_sender.py      # stub
        ws_sender.py        # stub
      auth/
        client.py           # AuthClient (stub)
      dlq/
        publisher.py        # публикация в notifications.dlq
```

---

## 3. 🔄 Поток данных (end-to-end)

Рассмотрим реализованный сценарий `user_registered`.

```text
[Auth Service]
    |
    | 1. POST /api/v1/events (event_type = "user_registered")
    v
[Notification API]
    |
    | 2. Валидация BaseEvent + UserRegisteredEventPayload
    | 3. Маппинг в NotificationJob (channel=email, template_code="welcome_email")
    | 4. Публикация job в Kafka (notifications.outbox)
    v
[Kafka: notifications.outbox]
    |
    | 5. KafkaNotificationConsumer читает сообщение
    v
[Notification Worker]
    |
    | 6. Валидация JSON → NotificationJob
    | 7. Проверка по job_id в notification_delivery (идемпотентность)
    | 8. Обработка expires_at / send_after
    | 9. Запрос контактов пользователя в AuthClient (stub)
    |10. Загрузка шаблона (templates)
    |11. Рендер subject/body
    |12. Отправка через EmailSender (MVP: лог)
    |13. Запись статуса SENT в notification_delivery
    v
[Postgres: notification_delivery]
```

При ошибке (например, нет email, не найден шаблон, runtime-exception) включается **Retry Engine**:

* несколько попыток отправки по заданной схеме задержек;
* финальный фейл → запись статуса `FAILED` и отправка события в `notifications.dlq`.

---

## 4. 📦 Контракты данных

Подробно контракты описаны в отдельных документах:

* [EVENTS.md](legacy/EVENTS.md) — формат входящих событий `Event`, которые принимает API;
* [QUEUE_JOBS.md](legacy/QUEUE_JOBS.md) — формат сообщений `NotificationJob` в Kafka.

Здесь важно зафиксировать:

### 4.1. Event → NotificationJob

API оперирует абстракцией `BaseEvent`:

```json
{
  "event_id": "uuid",
  "event_type": "user_registered",
  "source": "auth_service",
  "occurred_at": "ISO datetime",
  "payload": { ... }
}
```

Внутри `NotificationService` событие маппится в список `NotificationJob`.

На данный момент:

* `user_registered` — **реализован**, создаёт один `NotificationJob` на `user_id`;
* `new_film_released` — схема события есть, но маппинг в job **возвращает пустой список** (пока не реализовано);
* `campaign_triggered` — также определён в контракте, но логика формирования job не реализована (возврат пустого списка).

### 4.2. NotificationJob в Kafka

Worker оперирует `NotificationJob`:

```json
{
  "job_id": "uuid",
  "user_id": "uuid",
  "channel": "email",
  "template_code": "welcome_email",
  "locale": "ru",
  "data": { ... },
  "meta": {
    "event_type": "user_registered",
    "event_id": "uuid",
    "campaign_id": null,
    "priority": "normal"
  },
  "created_at": "ISO datetime",
  "send_after": null,
  "expires_at": null
}
```

---

## 5. 🔁 Надёжность и retry

### 5.1. Идемпотентность

Идемпотентность обеспечивается на уровне `notification_delivery`:

* перед обработкой job воркер запрашивает запись по `job_id`;
* если статус уже `SENT` или финальный `FAILED` / `EXPIRED` при `>= max_attempts` — job **пропускается**.

### 5.2. Retry Engine

Retry-контур реализован в `RetryEngine`:

* максимум `max_attempts` (из конфига);
* задержки из `retry_delays_seconds` (например, `[1, 3, 10]`);
* после каждой неудачной попытки:

  * статус `RETRYING` или `FAILED` (если попытки исчерпаны);
  * при финальном фейле — публикация в `notifications.dlq`.

### 5.3. Expiration / send_after

* `expires_at` — если время истекло, job получает статус `EXPIRED` и не отправляется;
* `send_after` — позволяет отложить отправку (воркер ждёт до указанного времени, но не дольше `max_send_delay_seconds`).

---

## 6. 🌐 Интеграция с внешними сервисами

### 6.1. Auth Service

Сейчас реализован через `AuthClient` (stub):

* возвращает фейковые данные контактов по `user_id`;
* архитектурно выделен в отдельный класс → легко заменить на реальный HTTP/gRPC-клиент.

### 6.2. Каналы доставки

Слои отправки уведомлений инкапсулированы в `senders`:

* `EmailSender` — в MVP просто логирует отправку;
* `PushSender` и `WsSender` — архитектурные заглушки (готовы к расширению).

В будущем они могут быть заменены на:

* SMTP / внешние email-провайдеры;
* push-шлюзы (FCM, APNs и т.п.);
* WebSocket-gateway.

JobProcessor не завязан на конкретную реализацию — он использует только интерфейсы.

---

## 7. 📈 Масштабируемость

### 7.1. Горизонтальное масштабирование Worker

* Несколько инстансов Notification Worker входят в одну consumer group (`notification-worker`);
* Kafka распределяет партиции топика `notifications.outbox` между инстансами;
* обеспечивается горизонтальное масштабирование по числу воркеров.

### 7.2. Ограничение нагрузки

* Нагрузка на внешние сервисы (Auth, email-provider и т.д.) контролируется:

  * количеством инстансов worker;
  * настройками Kafka (число партиций, max poll records и т.п.);
  * retry-стратегией.

---

## 8. 📌 Статус архитектуры

На данный момент реализован **MVP Notification Service**:

* есть полноценный API для приёма событий и управления шаблонами;
* есть Kafka-топики `notifications.outbox` и `notifications.dlq`;
* есть асинхронный worker с:

  * идемпотентностью,
  * retry-логикой,
  * поддержкой `send_after` / `expires_at`,
  * записью статусов в Postgres;
* есть базовая архитектура для Auth-интеграции и нескольких каналов доставки.

Следующие элементы считаются **архитектурным заделом** и могут быть доработаны позже:

* реальные интеграции с Auth/email/push/ws;
* логика сегментации пользователей и кампаний;
* отдельный campaign scheduler с cron/periodic задачами;
* отдельный WebSocket-сервис для real-time уведомлений;
* admin-панель для управления рассылками.

---