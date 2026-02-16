# Анализ цепочки Metrika Goals → Dashboard

## Поток данных

```
Яндекс.Метрика API (bytime)
    → yandex_metrica.get_goals_stats()
    → request_queue.enqueue('metrica', ...)
    → sync._sync_metrika_goals_for_direct()
    → MetrikaGoals (БД)
    → stats.get_goals()
    → PromotionEfficiency.vue
```

## Выявленные конфликты и блокеры

### 1. **Множественный запуск sync (ensure_data_synced)**
- `ensure_data_synced_async` вызывается из: `get_summary`, `get_dynamics`, `get_campaign_stats`
- При загрузке дашборда все 3 эндпоинта могут вызваться параллельно
- **Результат**: 3 потока sync для одной интеграции → конкуренция за очередь Metrika, дублирование записи в БД

### 2. **Request Queue — один worker на тип API**
- 3 workers: metrica, direct, vk (по одному на тип)
- Metrika limiter: 2 req/sec
- При 3 параллельных sync: 3×12 = 36 запросов к Metrika, идут последовательно через 1 worker
- **Результат**: sync может занимать 20+ секунд

### 3. **sync_metrika_goals_background + sync_integration_background**
- Оба могут запускаться одновременно (get_goals пустой → goals sync; data gap → full sync)
- Оба пишут в MetrikaGoals
- **Результат**: гонка, последний commit выигрывает (обычно ок)

### 4. **Кеш пустого ответа**
- `get_goals` с `@cache_response(ttl=900)` кеширует `[]`
- `CacheService.clear()` вызывается после sync — кеш сбрасывается
- **Результат**: после sync следующий запрос — cache miss, данные должны подтянуться

### 5. **Event loop и потоки**
- `sync_metrika_goals_background` создаёт новый event loop в потоке
- Очередь инициализирована в main loop при startup
- Workers очереди работают в main loop
- Sync thread ставит task в очередь и ждёт future — worker в main loop выполняет
- **Результат**: должно работать, main loop обрабатывает запросы и workers

### 6. **Docker: путь к debug.log**
- `os.path.join(..., "..", "..", ".cursor", "debug.log")` от `backend_api/stats.py` → `trafic_agent/.cursor/debug.log`
- В Docker рабочая директория может быть `/app` или `trafic_agent` — путь может не совпадать
- **Результат**: debug.log может не создаваться в контейнере

## Рекомендуемые исправления

1. **Дедупликация sync** — не запускать sync для интеграции, если уже идёт
2. **Дедупликация ensure_data_synced** — один вызов на "сессию" загрузки
3. **Проверка записи в БД** — после sync убедиться, что MetrikaGoals не пуста
