# Ручная и ночная standalone Метрика: короткие SQL-транзакции

Candidate `a09cf4d` + `3cd3a45`, 21.09.2026. Не production rollout. Ранее history path был вынесен отдельно в `cb3be39`; теперь durable `sync` для `YANDEX_METRIKA` тоже не использует монолитный legacy handler.

## Реализация

- `durable_sync.execute` направляет standalone Метрику в `metrika_sync_work`. Диспетчер закрывает SQL-сессию до входа в обработчик. Другие платформы и legacy consumer остаются без переключения.
- Prepare сверяет реальный running lease/token, payload/kind/resource/tenant, owner/project, frozen даты и settings digest принятой задачи. Короткие locks: client → integration → business job. Изменившиеся до запуска настройки требуют новой задачи, а не молчаливого принятия текущих параметров.
- Внешний сбор метаданных/статистики выполняется без занятого SQL-соединения. Используется общий проверенный коллектор goals/history; malformed responses не преобразуются в нули.
- Apply под короткими locks повторно проверяет scope/settings/параметры запроса и сохраняет строки, `last_sync_at`, источник manual/auto и SUCCESS business job одной fenced-транзакцией. Истёкший lease перед commit откатывает одновременно данные и статус. Принятый follow-up сохраняет PENDING интеграции после завершения старого окна.
- Сохранены максимум три попытки на retryable ошибки и ожидания 2/4 с без SQL-соединений. Жёсткий timeout использует существующий `SYNC_JOB_TIMEOUT_SEC`. Очередь запросов закрывается перед завершением event loop.
- Detector работает в SAVEPOINT, его ошибка не отменяет успешные данные. Необязательное LLM-пояснение запускается после commit; ошибка не повторяет завершённый сбор статистики. `expected_owner_id` не даёт LLM принять контекст нового владельца при переносе проекта.
- Отказ задачи фиксируется отдельно, без технического provider body в пользовательском тексте. Запись уведомления изолирована SAVEPOINT: её ошибка не возвращает задачу в RUNNING. Ошибка старой задачи не меняет перемещённую/перенастроенную integration. После такой смены нужна новая задача; окончательная UI-сверка статусов остаётся частью общей приёмки.
- Исправлено сужение периода первой загрузки: общий `goal_window` теперь берёт минимум запрошенной даты и 90-дневной bootstrap-даты. Явный период длиннее 90 дней сохраняется целиком. Это касается пользователей общего helper, но не переписывает оставшуюся inline-логику legacy standalone sync.

## Проверки

Первый targeted run: **151 passed**, 169,47 с. PostgreSQL/Redis изолированы, внешние API и LLM подменены; реальные рассылки/платежи не выполнялись. Финальная версия дополнена SAVEPOINT-проверкой уведомлений, потерей lease после flush и длинным первым периодом.

В manifest включены manual/auto, реальный durable dispatcher, provider retry, таймаут, отказ после смены owner/token/counter/pause/request, потеря lease, отсутствие fence, подмена payload, queued settings drift, detector failure, optional LLM failure, follow-up, replay после SUCCESS. HTTP/retry/cache/LLM mocks проверяют отсутствие занятого SQL-соединения; cache и LLM видят committed SUCCESS и строки через новую сессию.

Полный manifest чистого Git-артефакта `3cd3a45`: **1001 passed, 1 skipped, 1 deselected, 96 warnings, 6 subtests passed**, 393,22 с. Добавлены 22 случая к предыдущим 979. Image `admirra-devops:3cd3a45`, digest `sha256:4e4f9909e8ac904fe235796a90e5caad2df60246168f0ee5387a7059f47c3cd1`. Network internal=true, synthetic PostgreSQL/Redis, без production credentials. Optional previous-release comparison пропущен, frontend-source assertion исключён штатно: frontend в backend artifact не входит. Промежуточный полный прогон `a09cf4d` остановлен намеренно при исправлении длинного bootstrap-периода и не считается приёмкой.

Свежий backup `20260921T203526Z-f0033cd1` восстановлен тем же финальным образом: **50 с**, network=none, миграции до `cd9e0f1a2b3c`, worker preflight/boot четырёх групп, application readiness/auth guard и read smoke passed. 40/40 HTTP 200, concurrency 4, p50 135,33 мс / p95 998,40 мс / max 1008,62 мс. Это проверка восстановленной копии с idle workers, не browser timing и не mixed-provider peak.

Test/restore containers, network и volume удалены. Production сохранён на backend `4ca866eb…`, frontend `274aad1d…`, automation `33b4ca03…`; API-2 healthy, `/projects` HTTP 200, мониторинг 7/7 targets up и 0 active alerts. Production-БД и ingress не переключались; реальные рекламные API, клиентские отправки и банковские операции не вызывались.

## Границы

Полные sync/history Direct/VK/Avito всё ещё требуют выделения fetch/apply и покрытия settings/coverage/refresh/failure paths. Legacy standalone Метрика также не переводится этим пакетом; новая ветка работает только в durable dispatch. Общий SYNC-раздел, mixed-provider peak и production cutover не объявляются закрытыми.

Memory/spool budget для больших provider responses, отчётная freshness/revision barrier и единый pipeline, billing operation reconciliation, scoped lead notifications, shared files/cache/SSE/drain остаются в общем остатке. S3 и две ночи наблюдения отложены владельцем; подтверждение Telegram-алертов человеком и независимой копии recovery key не подменено техническими тестами.
