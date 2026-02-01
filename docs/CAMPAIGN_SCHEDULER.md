
---

# 📘 **CAMPAIGN_SCHEDULER.md**

**Механизм маркетинговых кампаний в Notification Service**

Документ объясняет:

* что такое маркетинговая кампания;
* как работает планировщик кампаний (campaign scheduler);
* как он генерирует события `campaign_triggered`;
* как эти события проходят через Notification API и далее в Worker.

---

# 1. Что такое кампания

Маркетинговая кампания — это запись в таблице `campaigns`, которая описывает:

| Поле                | Описание                                            |
| ------------------- | --------------------------------------------------- |
| `template_code`     | какой шаблон использовать                           |
| `segment_id`        | сегмент пользователей, которым отправлять сообщения |
| `schedule_cron`     | расписание в формате cron                           |
| `status`            | `ACTIVE`, `INACTIVE`, `PAUSED`                      |
| `last_triggered_at` | время последнего запуска (может быть `NULL`)        |
| `runs_count`        | сколько запусков было                               |
| `max_runs`          | максимальное количество запусков (∞ если `NULL`)    |

### Пример записи

```sql
INSERT INTO campaigns (
    id,
    name,
    template_code,
    segment_id,
    schedule_cron,
    status,
    max_runs
) VALUES (
    gen_random_uuid(),
    'Promo to premium users',
    'new_features',
    'segment_premium_users',
    '* * * * *',   -- каждую минуту
    'ACTIVE',
    3
);
```

---

# 2. Как работает Campaign Scheduler

Scheduler — это отдельный сервис, который каждые **N секунд**:

1. Загружает все кампании со статусом `ACTIVE`.
2. Для каждой кампании определяет, пора ли её запускать:

   * проверяет лимит `max_runs`;
   * сравнивает `last_triggered_at` с cron-расписанием.
3. Если кампания должна выполниться — формирует событие `campaign_triggered` и отправляет в Notification API.
4. После успешного ответа API — обновляет состояние кампании в Postgres:

   * `last_triggered_at = NOW()`;
   * `runs_count = runs_count + 1`;
   * если достигнут лимит `max_runs` — выставляет `status = INACTIVE`.

Если API недоступно — scheduler логирует ошибку и продолжает работать.

---

# 3. Cron-логика

Функция `is_campaign_due(campaign, now)` определяет готовность кампании к запуску:

1. Если `max_runs` задан и `runs_count >= max_runs` → кампания больше не запускается.
2. Если `last_triggered_at IS NULL` → это первый запуск, camпания запускается сразу.
3. Иначе:

   * `base = last_triggered_at`;
   * `next_run = croniter(schedule_cron, base).get_next()`;
   * если `next_run <= now` → пора запускать.

Некорректные cron-выражения игнорируются, ошибка пишется в лог.

---

# 4. Формат события, отправляемого в API

Scheduler отправляет строго совместимое событие:

`POST /api/v1/events`

```json
{
  "event_id": "uuid",
  "event_type": "campaign_triggered",
  "source": "campaign_scheduler",
  "occurred_at": "2025-11-21T12:00:00Z",
  "payload": {
    "campaign_id": "uuid",
    "template_code": "new_features",
    "channels": ["email"],
    "segment": {
      "segment_id": "segment_premium_users"
    }
  }
}
```

---

# 5. Payload `campaign_triggered` в Notification API

Модель в API:

```python
class CampaignTriggeredSegment(BaseModel):
    segment_id: str


class CampaignTriggeredEventPayload(BaseModel):
    campaign_id: UUID
    template_code: str
    channels: List[str]
    segment: CampaignTriggeredSegment
```

Notification API валидирует payload именно по этим полям.

---

# 6. Что делает Notification API

После получения события:

1. Валидирует формат `BaseEvent`.
2. Проверяет `event_type == "campaign_triggered"`.
3. Валидирует payload как `CampaignTriggeredEventPayload`.
4. Передаёт управление в `NotificationService`.
5. `NotificationService`:

   * определяет сегмент пользователей по `segment_id`;
   * формирует для каждого пользователя `NotificationJob`;
   * публикует задания в Kafka — `notifications.outbox`.

API возвращает:

```json
{
  "status": "accepted",
  "event_id": "...",
  "jobs_count": N
}
```

---

# 7. Что делает worker

Worker:

1. Читает job из Kafka.
2. Проверяет идемпотентность (`job_id`).
3. Загружает данные пользователя из Auth.
4. Рендерит шаблон.
5. Отправляет уведомление.
6. Записывает статус (`SENT`, `FAILED`, `RETRYING`, `EXPIRED`).
7. В случае ошибок:

   * делает retry;
   * или отправляет job в `notifications.dlq`.

---

# 8. Жизненный цикл кампании

1. Маркетолог создаёт кампанию в БД (`status = ACTIVE`, `runs_count = 0`).
2. Scheduler решает, что кампания должна быть запущена.
3. Выполняет HTTP POST → `/events` в Notification API.
4. Notification API генерирует пачку job в Kafka.
5. Worker отправляет уведомления.
6. Scheduler обновляет состояние кампании.
7. Кампания продолжает работать, пока не достигнет лимита.
8. Когда лимит достигнут — `status = INACTIVE`.

---

# 9. Ограничения MVP

* Поддерживается только email-канал.
* `segment_id` — абстрактный идентификатор (реальный сегментатор не реализован).
* Cron-логика не восстанавливает пропущенные слоты.
* Нет API для CRUD кампаний — управление только через БД.

---

# 10. Что можно улучшить

* API для создания/удаления/паузы кампаний.
* Поддержка нескольких каналов (`email`, `push`, `sms`).
* Реальный сегментатор (по жанрам, возрасту, странам).
* Сквозная аналитика кампаний.
* Более точный cron-планировщик (учитывающий пропуски и зависимости).

---
