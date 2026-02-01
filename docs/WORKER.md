
---

# 📘 **Notification Worker — Service Documentation**

Версия: **v1**
Статус: **MVP (Stage 3)**


---

# 1. 🎯 Назначение сервиса

**Notification Worker** — это фоновый компонент Notification Service.
Он отвечает за фактическую доставку уведомлений пользователям.

Worker:

* читает `NotificationJob` из Kafka-топика `notifications.outbox`;
* выбирает нужный канал доставки (email / push / ws);
* загружает шаблон и рендерит сообщение;
* получает контакты пользователя;
* отправляет уведомление;
* пишет историю доставок в Postgres;
* при неустранимой ошибке отправляет сообщение в DLQ-топик `notifications.dlq`.

Worker **не имеет HTTP API** и работает только через Kafka.

---

# 2. 🏗 Архитектура Worker Service

```text
Kafka: notifications.outbox
        |
        v
+-----------------------+
|  Notification Worker  |
+-----------------------+
|  Kafka consumer       |
|  Job processor        |
|  Retry engine         |
|  Status writer        |
|  Senders (email/push) |
+-----------------------+
        |
        v
Postgres: notification_delivery
        |
        v
Kafka DLQ: notifications.dlq
```

---

# 3. ⚙️ Конфигурация

Worker использует общую конфигурацию `Settings`.

### Kafka

```text
kafka_bootstrap_servers   = "kafka:9092"
kafka_outbox_topic        = "notifications.outbox"
kafka_dlq_topic           = "notifications.dlq"
kafka_consumer_group      = "notification-worker"
```

### Postgres (asyncpg)

```text
db_asyncpg_dsn = "postgresql://notifications:notifications@notifications-db:5432/notifications"
```

### Retry / Тайминги

```text
max_attempts              = 3
retry_delays_seconds      = [1.0, 3.0, 10.0]
max_send_delay_seconds    = 300
```

---

# 4. 🧱 Kafka → Worker → DB Пайплайн

Основной сценарий:

```text
1. Worker читает сообщение из Kafka
2. Десериализация и валидация NotificationJob
3. Идемпотентность (проверка job_id в БД)
4. Проверка expires_at
5. Проверка send_after (отложенная отправка)
6. Попытка отправки уведомления
7. Retry-pолиκа
8. Запись статуса в Postgres
9. DLQ при окончательном фейле
```

---

# 5. 🔧 NotificationJob (входной формат)

Worker получает `NotificationJob` в JSON-формате:

```json
{
  "job_id": "uuid",
  "user_id": "uuid",
  "channel": "email",
  "template_code": "welcome_email",
  "locale": "ru",
  "data": {},
  "meta": {
    "event_type": "user_registered",
    "event_id": "uuid",
    "campaign_id": null,
    "priority": "normal"
  },
  "created_at": "2025-11-14T12:00:00Z",
  "send_after": null,
  "expires_at": null
}
```

Каналы:

* `email`
* `push`
* `ws`
* `sms` *(зарезервировано)*

---

# 6. 🔁 Job Processing Pipeline

## 6.1. Идемпотентность

Перед обработкой Worker проверяет, существует ли запись `notification_delivery` с тем же `job_id`.

Job пропускается, если статус:

* `SENT`
* `FAILED` (при `>= max_attempts`)
* `EXPIRED`

## 6.2. Expiration

Если `job.expires_at` уже в прошлом:

* Worker записывает статус `EXPIRED`;
* отправка не выполняется.

## 6.3. Send After (отложенная отправка)

Если `send_after > now()`:

* Worker ждёт до указанного времени,
* но не дольше `max_send_delay_seconds`.

## 6.4. Retry Policy

На каждую job допускается максимум `max_attempts`.

Задержки: `retry_delays_seconds = [1.0, 3.0, 10.0]`.

Алгоритм:

1. Попробовать отправить уведомление.
2. При ошибке → записать `RETRYING` или `FAILED`.
3. Если попытки ещё есть → подождать задержку.
4. Если попытки закончились → job отправляется в DLQ.

---

# 7. ✉️ Доставка уведомлений

Worker поддерживает каналы:

### **email**

Используется `EmailSender`.
В MVP — логирование:

```
[EMAIL] Sending to=user@example.com subject="..." body="..."
```

### **push** *(MVP stub)*

Канал подключён архитектурно, но не реализован фактический провайдер.

### **ws** *(MVP stub)*

Идентично push.

### Выбор канала

Worker маршрутизирует через:

```python
if job.channel == NotificationChannel.EMAIL:
    email_sender.send(...)
```

---

# 8. 📝 История доставок

Все статусы пишутся в таблицу `notification_delivery` через репозиторий.

Поддерживаемые статусы:

```
SENT
RETRYING
FAILED
EXPIRED
```

### Случаи:

* успешная отправка → `SENT`
* retry → `RETRYING`
* окончательная ошибка → `FAILED`
* протухшая задача → `EXPIRED`

---

# 9. 🚨 DLQ (Dead Letter Queue)

Worker публикует неуспешные задачи в `notifications.dlq`.

Два типа сообщений:

### 1. Невалидный JSON

```json
{
  "raw_value": "...",
  "error_message": "Invalid JSON in Kafka message",
  "failed_at": "2025-11-21T12:34:56Z"
}
```

### 2. Job после max_attempts

```json
{
  "job": { ... },
  "error_message": "User has no email",
  "failed_at": "2025-11-21T12:34:56Z"
}
```

---

# 10. 📈 Масштабирование

Worker масштабируется горизонтально:

* все инстансы входят в одну consumer group:

  ```
  kafka_consumer_group = notification-worker
  ```

* Kafka распределяет партиции между воркерами;

* модель доставки — **at-least-once**;

* идемпотентность выполняется за счёт `job_id`.

---

# 11. ▶️ Как запустить Worker локально

При наличии docker-compose:

```bash
docker compose up notifications-worker
```

Логи:

```bash
docker compose logs -f notifications-worker
```

Отправить тестовый job вручную:

```bash
kafka-console-producer \
  --bootstrap-server localhost:9092 \
  --topic notifications.outbox
```

И вставить JSON job одной строкой.

---

# 12. 🧩 Статус документа

✔ Актуально для **MVP Notification Worker (Stage 3)**
🔄 Может быть дополнено реализацией реальных провайдеров (SMTP, push, ws).

---