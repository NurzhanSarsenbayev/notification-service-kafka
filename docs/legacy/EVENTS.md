
---

# 📘 **docs/EVENTS.md — Контракты внешних событий (Event)**

Notification API принимает внешние события от других микросервисов онлайн-кинотеатра.
Каждое событие приводит к созданию **одного или нескольких NotificationJob**, которые отправляются в Kafka.

Документ описывает формат этих событий и поддерживаемые типы.

---

# 1. 📦 Формат Event

```json
{
  "event_id": "uuid",
  "event_type": "string",
  "source": "string",
  "occurred_at": "ISO datetime",
  "payload": {}
}
```

---

## 1.1. 🧱 Обязательные поля

| Поле          | Тип      | Описание                                   |
| ------------- | -------- | ------------------------------------------ |
| `event_id`    | UUID     | Уникальный идентификатор события           |
| `event_type`  | string   | Тип события (определяет структуру payload) |
| `source`      | string   | Источник — сервис-отправитель              |
| `occurred_at` | datetime | Когда событие произошло                    |
| `payload`     | object   | Содержимое события                         |

---

# 2. 📚 Поддерживаемые события (MVP)

На текущем этапе реализована поддержка трёх типов событий.

---

# 2.1. `user_registered`

Отправляется сервисом авторизации после успешной регистрации пользователя.

### Payload

```json
{
  "user_id": "uuid",
  "registration_channel": "web",
  "locale": "ru",
  "user_agent": "Mozilla/5.0"
}
```

### Пример полного события

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

# 2.2. `new_film_released`

Отправляется сервисом контента при появлении нового фильма.

### Payload

```json
{
  "film_id": "uuid",
  "title": "string",
  "genres": ["sci-fi", "action"],
  "age_rating": "16+",
  "release_date": "2025-11-15",
  "target_segment": {
    "by_genres": ["sci-fi"],
    "min_age": 16
  }
}
```

### Пример полного события

```json
{
  "event_id": "a1b2c3d4-0000-0000-0000-000000000001",
  "event_type": "new_film_released",
  "source": "content_service",
  "occurred_at": "2025-11-14T13:00:00Z",
  "payload": {
    "film_id": "5fcc8705-30be-467d-b5e0-e17ab03ff59b",
    "title": "The Matrix",
    "genres": ["sci-fi", "action"],
    "age_rating": "16+",
    "release_date": "2025-11-15",
    "target_segment": {
      "by_genres": ["sci-fi", "action"],
      "min_age": 16
    }
  }
}
```

---

# 2.3. `campaign_triggered`

Отправляется административной панелью для массовых рассылок.

### Payload

```json
{
  "campaign_id": "uuid",
  "template_code": "black_friday_sale",
  "channels": ["email", "push"],
  "segment": {
    "segment_id": "bf_2025_loyal_customers"
  }
}
```

### Пример полного события

```json
{
  "event_id": "c1d2e3f4-0000-0000-0000-000000000001",
  "event_type": "campaign_triggered",
  "source": "admin_panel",
  "occurred_at": "2025-11-14T14:00:00Z",
  "payload": {
    "campaign_id": "9f3d5a5e-0000-0000-0000-000000000001",
    "template_code": "black_friday_sale",
    "channels": ["email", "push"],
    "segment": {
      "segment_id": "bf_2025_loyal_customers"
    }
  }
}
```

---

# 📌 Примечания

* `payload` валидируется строго по типу `event_type`.
* API возвращает **400 Bad Request**, если структура payload нарушена.
* Для каждого `event_type` Notification API формирует один или несколько `NotificationJob`.
* Новые события можно добавлять без изменений в worker — только расширением этого документа и пайплайна в API.

---

