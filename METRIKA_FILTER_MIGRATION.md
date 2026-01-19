# Миграция: Фильтр метрик по профилю (integration_id)

## Цель

Добавить возможность фильтровать метрики Яндекс.Метрики по конкретной интеграции (профилю/аккаунту).

**Проблема:** Если у клиента несколько интеграций Яндекс.Директ (разные профили), все метрики хранятся в одной куче. Невозможно понять, какая метрика к какому профилю относится.

**Решение:** Добавить поле `integration_id` в таблицу `metrika_goals`, чтобы каждая метрика была привязана к конкретной интеграции.

---

## Что изменено

### 1. **База данных**
- Добавлено поле `integration_id` в таблицу `metrika_goals`
- Добавлен foreign key на таблицу `integrations` с `ondelete='CASCADE'`
- Добавлен индекс для ускорения запросов

### 2. **Бэкенд**
- `automation/sync.py`: Теперь сохраняет `integration_id` при синхронизации метрик
- `backend_api/integrations.py`: Фильтрует метрики по `integration_id` вместо `client_id`
- `backend_api/stats.py`: Добавлен опциональный параметр `integration_id` для фильтрации
- `automation/google_sheets.py`: Экспортирует `integration_id` в Google Sheets

### 3. **Миграция**
- Создан файл миграции: `alembic/versions/7a8b9c0d1e2f_add_integration_id_to_metrika_goals.py`

### 4. **Backfill скрипт**
- Создан скрипт: `backfill_metrika_integration_id.py` для заполнения `integration_id` в существующих записях

---

## Инструкция по применению

### Шаг 1: Применить миграцию

Запустите миграцию Alembic внутри Docker контейнера:

```bash
cd trafic_agent
docker compose exec backend alembic upgrade head
```

**Ожидаемый результат:**
```
INFO  [alembic.runtime.migration] Running upgrade 113e8aa25ef0 -> 7a8b9c0d1e2f, add_integration_id_to_metrika_goals
```

### Шаг 2: Заполнить integration_id для существующих записей

Запустите backfill скрипт:

```bash
docker compose exec backend python backfill_metrika_integration_id.py
```

**Ожидаемый результат:**
```
INFO - Found 1234 MetrikaGoals records without integration_id
INFO - Assigned integration abc-123 to MetrikaGoal 1
...
INFO - ✅ Backfill completed successfully!
INFO -    - Updated: 1234 records
INFO -    - Warnings: 5 records (ambiguous or no match)
```

### Шаг 3: Проверить результаты

Проверьте, что все записи имеют `integration_id`:

```bash
docker compose exec db psql -U postgres -d saas_project -c "SELECT COUNT(*) FROM metrika_goals WHERE integration_id IS NULL;"
```

**Ожидаемый результат:**
```
 count 
-------
     0
(1 row)
```

### Шаг 4: Перезапустить приложение

```bash
docker compose restart backend
```

---

## Как использовать новый фильтр

### API

#### 1. Получить метрики для конкретной интеграции в мастере подключения:

```http
GET /api/integrations/{integration_id}/goals?date_from=2026-01-01&date_to=2026-01-31
```

**Теперь возвращает только цели для этой интеграции!**

#### 2. Получить общую статистику по целям с фильтром:

```http
GET /api/stats/goals?client_id={client_id}&integration_id={integration_id}
```

**Параметры:**
- `client_id` (опционально) - фильтр по проекту
- `integration_id` (опционально) - **НОВЫЙ** фильтр по интеграции/профилю

#### 3. Экспорт в Google Sheets:

```python
from automation.google_sheets import GoogleSheetsService

service = GoogleSheetsService()
service.export_metrika_goals(
    spreadsheet_id="...",
    client_id="...",
    integration_id="..."  # НОВЫЙ параметр
)
```

---

## Откат изменений (если нужно)

Если что-то пошло не так, откатите миграцию:

```bash
docker compose exec backend alembic downgrade -1
```

**Внимание:** Это удалит поле `integration_id` и все данные в нем будут потеряны!

---

## Troubleshooting

### Проблема: Миграция не применяется

**Решение:**
```bash
# Проверьте текущую версию
docker compose exec backend alembic current

# Посмотрите историю миграций
docker compose exec backend alembic history

# Примените миграцию явно
docker compose exec backend alembic upgrade 7a8b9c0d1e2f
```

### Проблема: Backfill скрипт показывает много warnings

**Причина:** У клиента несколько интеграций, и скрипт не может однозначно определить, к какой интеграции относится старая метрика.

**Решение:** Это нормально. Скрипт автоматически выбирает наиболее подходящую интеграцию по дате последней синхронизации. Если хотите точность, удалите старые метрики и дождитесь новой синхронизации.

### Проблема: После миграции метрики не отображаются

**Причина:** В мастере интеграции теперь фильтрация идет по `integration_id`, а старые записи могут иметь `NULL`.

**Решение:** Запустите backfill скрипт (Шаг 2).

---

## Что дальше?

После применения миграции:

1. **Новые метрики** будут автоматически сохраняться с `integration_id`
2. **Фильтр в мастере интеграции** (шаг 4) будет показывать только цели текущей интеграции
3. **API `/stats/goals`** теперь можно вызывать с параметром `integration_id` для точной фильтрации
4. **Экспорт в Google Sheets** будет включать колонку "Integration ID"

---

## Контакты

Если возникли вопросы или проблемы, создайте issue в репозитории проекта.

