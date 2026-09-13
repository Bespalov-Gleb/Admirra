# DB-03 — безопасный инвентаризационный аудит PostgreSQL

Часть T03, не завершение SQL/load acceptance. Runtime-приложение на production не обновлялось.

## Инструмент

```sh
python -m ops.db_read_audit
```

Подключение только через уже заданный `DATABASE_URL`, не аргумент CLI. Отдельный `NullPool`, connect timeout 5 s, SQL-транзакция принудительно `READ ONLY`, каждый statement не более 3 s, lock wait не более 1 s. Четыре запроса к системным каталогам, фиксированный allowlist таблиц, не более 32 table rows / 256 index rows. При достижении границы выставляется `truncation_possible`. Ошибки драйвера не печатаются, чтобы не раскрывать DSN/пароли.

Выход: размер БД, версия, время старта/замера/reset, cumulative counters, доступность `pg_stat_statements`, агрегированные состояния соединений и возраст транзакций; размеры/estimated tuples/churn/vacuum/analyze выбранных таблиц; размеры, valid/ready/scan counters индексов. Есть флаг полноты прав просмотра activity. Имена/email/платежи/токены пользователей, текст выполняемых SQL и содержимое бизнес-таблиц не читаются/не выводятся.

`load_accepted=false` всегда. `n_live_tup`/`n_dead_tup` — оценки, накопленные scans/counters — не текущий RPS. Статистика обновляется с задержкой, область видимости зависит от роли; [PostgreSQL 15: cumulative statistics](https://www.postgresql.org/docs/15/monitoring-stats.html). Не трактовать высокий cache-hit или отсутствие блокировок в одном снимке как доказательство достаточной производительности.

## Production snapshot 13.09.2026, 09:29 UTC

Инструмент передан в stdin отдельного Python-процесса в существующем backend-контейнере. Файлы/env на сервере не менялись; никаких миграций, ANALYZE, VACUUM, CREATE INDEX или restart. Сырой JSON без бизнес-строк сохранён локально в `/private/tmp/admirra-db-audit-2026-09-13.json` (временный диагностический файл, не deploy artifact).

- PostgreSQL 15.18, старт 13.08.2026 00:23 UTC. БД **816 758 119 bytes (~779 MiB)**.
- `pg_stat_statements` установлен. Отдельный запрос `COUNT(*)` в read-only транзакции с timeout 3 s к `public.pg_stat_statements` успешно вернул 3214 записей для текущей БД. Тексты/параметры запросов не извлекались. Для следующего bounded sampling не нужно устанавливать расширение/перезапускать БД; сбор свежих дельт и привязка к коду остаются следующим шагом.
- 11 соединений, все idle; blocked=0, idle-in-transaction=0, активных кроме диагностического=0. Права просмотра activity полные. Это мгновенный снимок.
- На выбранных таблицах не найдено invalid/not-ready индексов, ответ не усечён.
- `stats_reset=NULL`: не вычислять скорость за месяц из этих totals; нужны парные замеры с проверкой reset/restart.

| Таблица | Total bytes | Estimated live/dead | Наблюдение |
| --- | ---: | ---: | --- |
| yandex_keywords | 399 187 968 | 710 541 / 100 290 | Крупнейшая; около 219 MB индексов, предыдущий autovacuum 27.08 |
| vk_stats | 126 648 320 | 29 162 / 2 945 | 10 892 cumulative seq scans / 1 522 470 874 seq tuples read; повод проверить реальные запросы и estimate freshness |
| yandex_groups | 114 450 432 | 275 006 / 34 646 | Около 48 MB индексов; предыдущий autovacuum 27.08 |
| metrika_goals | 94 945 280 | 204 896 / 0 | Большой churn delete/insert, autovacuum/analyze прошли 13.09 |
| report_deliveries | 19 464 192 | 9 / 26 | Основной объём не в heap/index: snapshot TOAST; подтверждает ценность этапа shared artifacts |

Per-table `storage_options=NULL` у выбранных таблиц: индивидуальный `autovacuum_enabled=false` не обнаружен. Это **не** проверка всех глобальных настроек и не доказательство свежести оценок. Нулевые vacuum/analyze counters VK пока не объяснены; не выдавать это за причину задержек без следующего измерения.

Никакие индексы не добавлены/удалены по одному счётчику. Следующий шаг: парные снимки `pg_stat_statements`, сопоставление формы запросов с кодом, representative before/after plans и отдельное решение по autovacuum thresholds/индексам. `VACUUM FULL` не использовать.

## Проверки и границы

Targeted PostgreSQL: **4 passed**, 0,61 s; повтор после добавления детализации heap/index/storage_options — **4 passed**, 0,65 s. Проверены read-only/локальные timeouts, закрытие pool, отсутствие synthetic PII в отчёте, SQL-инъекция через schema (bound parameter), принудительный запрет случайного DDL и отсутствие credentials в CLI-ошибке.

Source-bind полный regression: **445 passed, 1 skipped, 1 deselected**, 47 warnings, 98,82 s. После него добавлена детализация heap/index/storage_options (отдельный targeted повтор); окончательная проверка committed image фиксируется отдельно. Это диагностическая реализация, не ускорение production и не разрешение cutover. Настройки PostgreSQL и права runtime не повышались.

Окончательный committed image `admirra-devops:3429be3`, без source-bind: **445 passed, 1 skipped, 1 deselected**, 47 warnings, 95,35 s. Image ID `sha256:d004c2ba41a7450e045d028f12b100123a0e3373f03790ae9161593a59a7dd89`, release label `3429be3`. `pip check` прошёл; в образе отсутствуют `.env`, `.git`, uploads, landing и frontend. На production 13.09 повторно подтверждены `cdf0a4d` и HTTPS 200.
