# DB-03 — интервальная статистика запросов

Подготовлен `ops/db_statement_sample.py`. Запуск: `python -m ops.db_statement_sample --seconds 30`; DATABASE_URL берётся из защищённого окружения. Ожидание 1–30 секунд, две короткие read-only транзакции, connect 5 s / statement 3 s / lock 1 s. Между снимками SQL connection освобождается. Никаких CREATE EXTENSION/reset/ANALYZE/изменений server settings в инструменте.

Вызывается `pg_stat_statements(false)`: текст запросов вообще не возвращается. До 10 000 записей, top-20 по **дельте** execution time, общие totals по всем top-level entries (nested не суммируются повторно). Ключ включает DB role OID/queryid/toplevel. Новая запись получает нулевую начальную базу только при полном снимке без вытеснений. [PostgreSQL 15: pg_stat_statements](https://www.postgresql.org/docs/15/pgstatstatements.html).

Сравнение отказывается от результата при изменении fingerprint кластера/БД, старта/версии сервера/расширения, global reset/dealloc; при пропавших/скрытых/дублирующихся entries, уменьшении/невалидности counters, превышении row cap. Metadata reset/dealloc сверяется и до/после каждого чтения. Нужны полные права диагностического чтения и доступ к `pg_control_system`, runtime-роли ради этого не расширяются.

Ограничения: SQL calls/s не HTTP RPS и не CPU utilization; включены диагностические SQL. Учитываются завершённые вызовы, которые могли начаться до окна; ошибки/текущие операции представлены не полностью. PG15 не позволяет гарантированно обнаружить targeted reset, если к следующему снимку новый счётчик уже превысил старый. Не совмещать sampling со сбросами статистики/maintenance. Короткий спокойный интервал не заменяет нагрузочную приёмку. `load_accepted=false` сохраняется.

## Проверки

- 31 targeted test, 0,65 s: правильные дельты/новые entries/разные роли/nested, границы/reset/restart/eviction/аномальные counters, отсутствие секретов в CLI-ошибках.
- Настоящий PostgreSQL + pg_stat_statements: connection released при ожидании, бизнес-строки/SQL-текст не возвращаются, реальный reset обнаруживается. Расширение загружается только в изолированном test Compose; production не перезапускался.
- Source-bind полный regression: **476 passed, 1 skipped, 1 deselected**, 47 warnings, 94,64 s. Image-only acceptance фиксируется после сборки коммита.

## Read-only production sample

13.09.2026, **16:09:36–16:10:06 UTC**, 30,042 s. Передан standalone script в stdin существующего backend-контейнера, без записи файлов/env на сервере. Не запускались принудительные sync, отчёты, AI или нагрузочные запросы. JSON без текстов/параметров SQL: `/private/tmp/admirra-statements-2026-09-13.json` (временный локальный diagnostic file, не release artifact).

- 330 завершённых top-level SQL calls, **10,985 SQL calls/s**.
- Суммарная дельта execution time **26,945 ms**, включая собственную диагностику (~9,159 ms у чтения первого snapshot).
- 33 изменившихся statement entries; два регулярных запроса по 78 calls / ~0,081 ms mean за интервал.
- В таком спокойном окне нет доказательства перегруженной БД. Нельзя из этого обещать p95/RPS ёмкость сайта или выбирать индексы.

Для сопоставления двух частых queries отдельно извлечены только relation/predicate identifiers из нормализованного текста на стороне PostgreSQL; полные SQL/константы/данные пользователей в вывод не отправлялись. Это дополнительная диагностика, не часть text-free sampler.

Следующий этап DB-03: связать частые формы с кодом, подготовить репрезентативные профили/планы, измерить before/after для конкретной оптимизации. Общие full-sync/report/AI транзакции и прочие пункты основного ТЗ остаются открытыми.
