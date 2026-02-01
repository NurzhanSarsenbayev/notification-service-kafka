---

# 📘 **Notification API — HTTP Documentation**

Версия: **v1**
Статус: **MVP (Stage 2)**

---

# 1. 🎯 Назначение сервиса

**Notification API** — это HTTP-входная точка сервиса уведомлений.
Он принимает события от других микросервисов онлайн-кинотеатра, валидирует их и публикует во внутреннюю очередь Kafka для дальнейшей обработки воркером.

Notification API **не выполняет отправку сообщений** — это задача **Notification Worker**.

---

# 2. 🏗 Общая архитектура

```text
[Auth / Content / Admin Panel Services]
                |
             HTTP POST /events
                |
        +---------------------+
        |   Notification API  |
        +---------------------+
                |
                | Kafka publish (notifications.outbox)
                v
        +----------------------+
        |  Notification Worker |
        +----------------------+
                |
      [email / push / websocket]
```

API работает независимо от воркера:
даже если Kafka недоступна, API продолжает принимать события (режим деградации).

---

# 3. 📚 Версии API

Базовый URL:

```text
/api/v1
```

---

# 4. ❤️ Health Checks

## `GET /health`

Проверка того, что приложение запущено.

### Response (200)

```json
{"status": "ok"}
```

---

# 5. 📩 События: `POST /api/v1/events`

Notification API принимает внешние события в едином формате.

---

## 5.1. 🔧 Формат Event

```json
{
  "event_id": "uuid",
  "event_type": "string",
  "source": "string",
  "occurred_at": "ISO datetime",
  "payload": {}
}
```

Описание полей:

| Поле          | Тип      | Описание                                   |
| ------------- | -------- | ------------------------------------------ |
| `event_id`    | UUID     | Уникальный ID события                      |
| `event_type`  | string   | Тип события — определяет структуру payload |
| `source`      | string   | Источник события                           |
| `occurred_at` | datetime | Когда событие произошло                    |
| `payload`     | object   | Данные события                             |

---

## 5.2. 📦 Поддерживаемые типы событий (MVP)

В этом MVP **полностью реализован только один сквозной сценарий** — `user_registered`.
Остальные типы событий объявлены в контракте, но пока **не реализованы** и честно возвращают `501 Not Implemented`.

---

### 1) `user_registered` ✅ *Реализовано*

Payload:

```json
{
  "user_id": "uuid",
  "registration_channel": "web",
  "locale": "ru",
  "user_agent": "Mozilla/5.0"
}
```

**Поведение:**

* payload валидируется;
* формируется один `NotificationJob` для указанного `user_id`;
* `channel` = `email`, `template_code` = `"welcome_email"`;
* job публикуется в Kafka-топик `notifications.outbox`;
* воркер отправляет welcome-уведомление (MVP: логирует отправку).

---

### 2) `new_film_released` ⚠️ *Пока не реализовано*

Payload (контракт на будущее):

```json
{
  "film_id": "uuid",
  "title": "string",
  "genres": ["sci-fi"],
  "age_rating": "16+",
  "release_date": "2025-11-15",
  "target_segment": {
    "by_genres": ["sci-fi"],
    "min_age": 16
  }
}
```

**Статус реализации:**

* схема события описана;
* **бизнес-логика (выбор сегмента пользователей и генерация `NotificationJob`) пока не реализована**.

**Текущее поведение API:**

* если прислать событие с `event_type = "new_film_released"`, API вернёт:

```json
{
  "detail": "Event type 'new_film_released' is not implemented in this MVP"
}
```

с кодом **501 Not Implemented**.

---

### 3) `campaign_triggered` ⚠️ *Пока не реализовано*

Payload (контракт на будущее):

```json
{
  "campaign_id": "uuid",
  "template_code": "black_friday_sale",
  "channels": ["email", "push"],
  "segment": {
    "segment_id": "bf_loyal_customers"
  }
}
```

**Статус реализации:**

* схема события описана;
* логика кампаний/сегментов и массовых рассылок **не реализована в этом MVP**.

**Текущее поведение API:**

* при `event_type = "campaign_triggered"` API вернёт:

```json
{
  "detail": "Event type 'campaign_triggered' is not implemented in this MVP"
}
```

с кодом **501 Not Implemented**.

---

## 5.3. 🎛 Обработка события

При получении Event API:

1. Валидирует:

   * общий формат `BaseEvent`,
   * структуру `payload` в зависимости от `event_type`.

2. Дальше возможны варианты:

   * если `event_type = "user_registered"` и payload корректный:

     * событие конвертируется в один или несколько `NotificationJob`;
     * job’ы публикуются в Kafka-топик `notifications.outbox`;
     * API возвращает `202 Accepted`.

   * если `event_type` поддерживается контрактом, но **ещё не реализован** (`new_film_released`, `campaign_triggered`):

     * API возвращает **501 Not Implemented**.

   * если `event_type` неизвестен (нет в `EventType`):

     * API возвращает **400 Bad Request**.

---

## 5.4. 📨 Пример запроса (реализованный сценарий)

```http
POST /api/v1/events
Content-Type: application/json
```

```json
{
  "event_id": "6a9f7f26-4c0c-4a91-9f3d-b159c2dcb001",
  "event_type": "user_registered",
  "source": "auth_service",
  "occurred_at": "2025-11-14T12:34:56Z",
  "payload": {
    "user_id": "f3aa4a0e-97d4-4e21-a2b4-9fb7c8d9f001",
    "registration_channel": "web",
    "locale": "ru",
    "user_agent": "Mozilla/5.0"
  }
}
```

---

## 5.5. 🟢 Успешный ответ (202 Accepted)

```json
{
  "status": "accepted",
  "event_id": "6a9f7f26-4c0c-4a91-9f3d-b159c2dcb001",
  "jobs_count": 1
}
```

`jobs_count` — количество сформированных и опубликованных `NotificationJob`
(для `user_registered` в текущем MVP всегда 1).

---

## 5.6. 🔴 Ошибки

### Неверный payload (400 Bad Request)

```json
{
  "detail": "Invalid payload for user_registered: field 'user_id' is required"
}
```

### Неизвестный `event_type` (400 Bad Request)

```json
{
  "detail": "Unsupported event_type: some_random_event"
}
```

### Тип события известен, но не реализован (501 Not Implemented)

Для `new_film_released`:

```json
{
  "detail": "Event type 'new_film_released' is not implemented in this MVP"
}
```

Для `campaign_triggered`:

```json
{
  "detail": "Event type 'campaign_triggered' is not implemented in this MVP"
}
```

---

# 6. 🧱 NotificationJob (что API публикует в Kafka)

API не отправляет уведомления — он публикует во внутренний Kafka-топик структуры вида `NotificationJob`.

Пример (welcome email при регистрации):

```json
{
  "job_id": "uuid",
  "user_id": "uuid",
  "channel": "email",
  "template_code": "welcome_email",
  "locale": "ru",
  "data": {
    "registration_channel": "web",
    "user_agent": "Mozilla/5.0"
  },
  "meta": {
    "event_type": "user_registered",
    "event_id": "uuid",
    "campaign_id": null,
    "priority": "normal"
  },
  "created_at": "2025-11-14T12:35:10Z",
  "send_after": null,
  "expires_at": null
}
```

Поля соответствуют описанию в `docs/QUEUE_JOBS.md`.

> ℹ️ В текущем MVP реальные `NotificationJob` формируются только для события `user_registered`.

---

## 6.1. Каналы доставки

Поддерживаемые значения поля `channel`:

```text
email
push
ws
sms  (зарезервировано)
```

В текущем MVP фактически используется **только `email`**.
Каналы `push`, `ws`, `sms` зарезервированы для будущих расширений.

---

# 7. 🔌 Kafka (режим деградации)

Если Notification API не может подключиться к Kafka:

* логируется ошибка;
* включается **dummy-режим** публикации;
* job’ы **НЕ отправляются** в Kafka, но логируются в виде:

```text
[KAFKA DUMMY] Would publish to notifications.outbox: {...}
```

При этом API **всё равно возвращает статус `202 Accepted`**,
чтобы не ломать работу внешних сервисов во время проблем с брокером.

> Ответ `202 Accepted` в dummy-режиме означает:
> «Событие принято API, но фактическая публикация в очередь временно отключена».

---

# 8. 📝 Работа с шаблонами уведомлений

Notification API предоставляет CRUD для шаблонов в таблице `templates`.

---

## 8.1. `GET /api/v1/templates`

Получить список всех шаблонов.

### Response (200)

```json
[
  {
    "id": "82e3e29a-804e-4367-b84b-6d71e0a1fed3",
    "template_code": "welcome_email",
    "locale": "ru",
    "channel": "email",
    "subject": "Добро пожаловать!",
    "body": "<h1>Привет!</h1><p>Спасибо за регистрацию</p>"
  }
]
```

---

## 8.2. `POST /api/v1/templates`

Создать новый шаблон.

### Request

```json
{
  "template_code": "welcome_email",
  "locale": "ru",
  "channel": "email",
  "subject": "Добро пожаловать!",
  "body": "<h1>Привет!</h1><p>Спасибо за регистрацию</p>"
}
```

### Response (201)

```json
{
  "id": "232420e6-c069-4974-9313-6c029684eaa5",
  "template_code": "welcome_email",
  "locale": "ru",
  "channel": "email",
  "subject": "Добро пожаловать!",
  "body": "<h1>...</h1>"
}
```

### Ошибка — шаблон уже существует (409 Conflict)

```json
{
  "detail": "Template with this code/locale/channel already exists"
}
```