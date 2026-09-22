# Scoped отчёт качества и динамический чёрный список

Candidate, 23.09.2026 (МСК). **Production не менялся.** Новая additive migration
`f46f708192a3`, parent `f35e6f708192`. Старые неатрибутированные Redis-ключи
`placement:*` не копируются, не читаются и не очищаются этим пакетом.

## Реализовано

- `/reports/quality` и `/reports/blacklist` читают только проекты текущего owner.
  В отчёте `days=1…365` реально ограничивает период, `[start, end)` UTC; PENDING
  не входит в знаменатель. Отказы: INVALID/SPAM или is_spam, как в scoped alerts.
- Все секции отчёта читаются в одной короткой read-only REPEATABLE READ транзакции,
  после чего SQL освобождается. До 10 худших источников, группировка **по проекту**
  и UTM, до 10 категорий причин плюс точный `other_rejection_count`.
- Excel создаётся установленным `openpyxl`, без отсутствующего pandas. Пустой
  отчёт содержит лист «Сводка», файл формируется без SQL-соединения. Имена/UTM
  экранируются от formula injection; собственные числовые показатели остаются числами.
- `lead_placement_blocks`: owner + project + SHA-256 нормализованного массива UTM,
  названия, техническая причина и срок. JSON-encoding ключа исключает коллизии
  разделителя `:`. Смена owner/неактивный проект/чужой или остановленный связанный
  Client исключают старые решения из чтения и применения.
- `lead.blacklist` планируется в 09:00 `LEAD_ALERT_TIMEZONE` (UTC по умолчанию),
  независимо от Telegram. Parent идёт страницами по 100 активных PhoneProject,
  UUID cursor/upper bound и атомарные replay-safe children/continuation.
- Child `lead.blacklist.project`, maintenance, resource `lead-blacklist:{project}`:
  authoritative job/tenant/payload/lease + блокировка проекта; повторная проверка
  owner/client/activity/policy, bounded SQL агрегация, пакетный INSERT ON CONFLICT,
  fenced commit. Внешнего HTTP/Redis нет, поэтому повтор безопасен.
- Окно `PLACEMENT_BLACKLIST_LOOKBACK_DAYS=21`, допустимо 1–90 дней. Порог/минимум/
  TTL сохранены: 70%, 10 завершённых лидов, 21 день; TTL 1–90. Решения не продлеваются
  ежедневным повтором. Истёкшие и прежние owner-строки проекта удаляются в транзакции
  очередного пересчёта. Повтор не применяет частичный результат после потери lease.
- Отказы самой блокировки исключены из обучения, чтобы она не поддерживала себя
  исключительно собственными отказами. UTM длиннее 200 символов не создают
  динамические решения; статическая валидация продолжает работать.
- Не более 1000 кандидатов/активных блокировок проекта. Превышение останавливает
  и откатывает весь child. Чтение списка владельца также ограничено 1000; превышение
  — явный HTTP 422, не молчаливая обрезка. Постраничный экспорт сверх этого лимита
  пока не реализован.
- UTM validator использует DB project scope, а не глобальные Redis-ключи. Без
  project binding (общая диагностика/старый unbound endpoint) динамический список
  не применяется; явные статические правила из конфигурации сохранены.
- Убрано накопление accepted/rejected лидов в неограниченной общей `_stats` map.
  Глобальный legacy update-blacklist теперь явно запрещён; новый путь — durable planner.
- PhoneReports показывает категории из API-map, название проекта, отдельные
  ошибки/повтор чтения и прочерки вместо ложных нулей. Late response старого периода
  не заменяет текущий; запросы отменяются при уходе, экспорт защищён от двойного клика.

## Проверки

Синтетический PostgreSQL/Redis в internal Docker network, `WW_TEST=1`.
Расширенный прогон: **98 passed, 17 warnings**, 69,29 с. Проверены scopes, TTL,
повтор, NULL/empty UTM, policy changes, lease loss до запуска и перед commit,
bound/rollback, parent pagination 205 проектов, миграция, workbook/formula handling,
HTTP auth/validation, SQL release, startup/runtime и worker pool lifecycle.
Финальный прогон после перехода на bulk INSERT: **19 passed, 17 warnings**,
24,90 с. Контейнеры завершились с exit code 0; проверка включает rollback после
потери lease непосредственно перед INSERT/commit. Локальная компиляция Python
и `git diff --check` прошли.

Frontend: 4 unit/compile/lifecycle tests passed, Vite build passed. Визуальная
проверка страницы в браузере не выполнялась; это не визуальная приёмка.
Первый прогон (79 passed, 2 failed) выявил отсутствующий pandas и необходимость
обновить synthetic preflight fixture под новую таблицу; исправлены до 98 passed.
Полный manifest и restore конечного образа этого schema head ещё предстоят.

## Rollout / ограничения

Не выкатывать этот пакет отдельно в старый legacy scheduler. Нужны additive
migration, согласованный новый API/worker/scheduler с `DURABLE_TASKS=true`,
отключённые embedded schedulers и `EXPECTED_SCHEMA_REVISION=f46f708192a3`.
Worker preflight проверяет наличие таблицы. До открытия — контролируемый первый
scoped пересчёт на сохранённых данных и проверка пустых/ненулевых списков.
Старые общие решения нельзя приписывать произвольному owner; они намеренно не
продолжают блокировать чужие проекты. Согласовать риск пустого начального списка
в окончательном cutover-плане. Downgrade сохраняет таблицу; старые worker images
не должны получать новые queued kinds, перед откатом требуется drain/сверка.

**Остаётся в пункте 3:** ранние `_reject` ветки без project/db, сохранение всех
решений, безопасные immediate exports и внешние validation calls без долгого SQL;
legacy diagnostics/global credentials, остальные interactive AI/report и billing
offline-conversion пути. Данные в новом отчёте — только сохранённые проектные
лиды; несохранённые исторические отказы автоматически не восстановлены.
Пункты 1–4 целиком не объявляются закрытыми; S3/две ночи по-прежнему отложены.
