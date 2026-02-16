# Анализ: конверсии из Яндекс.Метрики

## Цепочка получения данных

### 1. API Метрики (`yandex_metrica.py`)

- **Метод:** `get_goals_stats()`
- **Метрики:** `ym:s:goal{N}visits` (целевые визиты) или `ym:s:sumGoalVisitsAny` (все цели)
- **Фильтр:** `ym:s:lastSignAdvEngine=='Yandex Direct' OR ym:s:lastSignAdvEngine=='Yandex Direct (undefined)'`
- **Размерность:** `ym:s:date` (по дням)

### 2. Синхронизация (`sync.py`)

- **Источник целей:** `integration.selected_goals`, `integration.primary_goal_id`
- **Источник счётчиков:** `integration.selected_counters`
- **Сохранение:** `MetrikaGoals` (goal_id, date, conversion_count, integration_id)

**Исправление:** при `primary_goal_id` используется только эта цель для `goal_id="all"` (без суммирования нескольких целей).

### 3. Агрегация (`stats_service.py`)

- **Метрика «Лиды»:** `MetrikaGoals.conversion_count` WHERE `goal_id='all'`
- **Фильтр:** `integration_id` по активным кампаниям клиента

### 4. Панель «Разбивка по целям» (`stats.py` → `/dashboard/goals`)

- **Исправление:** фильтр по `integration_ids` (интеграции с активными кампаниями)

---

## Разница: visits vs reaches

| Метрика | Описание | Метрика API |
|---------|----------|-------------|
| **Целевые визиты** | Визиты, в которых цель достигнута ≥1 раз | `ym:s:goal{N}visits` |
| **Достижения цели** | Количество срабатываний цели | `ym:s:goal{N}reaches` |

**Пример:** 1 визит, 3 отправки формы → visits=1, reaches=3.

**Сейчас используется:** `visits` (целевые визиты).

**Если нужно совпадение с «Достижения цели» в Метрике:** использовать `ym:s:goal{N}reaches` вместо `visits`.

---

## Возможные причины расхождений

1. **Суммирование нескольких целей** — если одна цель достигнута в нескольких визитах, сумма по целям даёт завышение.
2. **Отсутствие фильтра по `integration_id`** — суммирование целей по всем интеграциям клиента.
3. **visits vs reaches** — сравнение с «Достижения цели» при использовании `visits`.
4. **Фильтр по Директу** — значения `ym:s:lastSignAdvEngine`: `Yandex Direct`, `Yandex Direct (undefined)`.

---

## Проверка по документации Метрики

- [Конверсии](https://yandex.com/dev/metrika/doc/api2/stat/metrics/visits/conversions.html)
- [Параметризация целей](https://yandex.com/dev/metrika/doc/api2/stat/param.html) — `ym:s:goal<goal_id>visits`, `ym:s:goal<goal_id>reaches`
