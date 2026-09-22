# Sync coverage — основа freshness barrier

Статус: **локальный candidate, не production**. Это часть SYNC-02, не закрытие всего SYNC/REPORT/DevOps.

## Реализация

- `sync_coverage` хранит подтверждённые диапазоны по integration/client/owner, стадии и семантическим настройкам источника. Новая additive миграция `f02b3c4d5e6f` после `ef1a2b3c4d5e` создаёт пустую таблицу: старый `last_sync_at` не превращается в доказательство покрытия.
- Durable manual/night/history записывают coverage в одной транзакции с фактами и под тем же execution fence. Потеря lease или ошибка записи откатывает обе части. Внешний HTTP остаётся вне SQL-транзакций.
- Директ: campaigns/groups/keywords; VK: campaigns; Авито: campaigns/groups/creatives; Метрика: metrika_goals за фактический lookback, а не только запрошенные даты. Optional balance/strategies не объявляются статистически полными стадиями.
- Подтверждённый пустой ответ является валидным нулевым периодом. Ошибка API не двигает coverage; исчезновение выбранной цели при замене фактов инвалидирует подтверждение этого диапазона.
- Используются эффективные интервалы, не append-only история: перезапись дат убирает старое подтверждение независимо от digest. Поэтому смена целей A → B → A не «оживит» старое подтверждение A поверх фактов B. Незатронутые края диапазона сохраняются.
- Digest содержит привязку кабинета, владельца, платформу, цели/счётчики, фильтры и настройки лидов, но не токены. План исполнения по-прежнему защищён полным credential-sensitive guard; обычная ротация токена не аннулирует историю.
- `observed_at` — время подготовки **до** внешних запросов: долгое выполнение не делает старый снимок более свежим. `recorded_at` — время записи внутри транзакции, не обещание точного времени COMMIT. `execution_id` позволяет связать доказательство с durable job; FK не препятствует будущей retention jobs.
- `core.sync_coverage.assess` требует явный owner/client, список стадий, диапазон и timezone-aware `not_before`. Все даты всех стадий должны быть покрыты. Нет подтверждения, изменились настройки, другой владелец, paused/disconnected источник или устаревшие данные → `ready=False`. Чтение ограничено 4096 интервалами и при превышении тоже закрыто.
- Reader повторно читает и блокирует client → integration, включая обновление ORM identity map. Результат применим к текущей короткой транзакции снимка, не к последующей отправке без проверки. Нельзя держать эти блокировки во время HTTP/PDF/AI.

## Проверки

Изолированные PostgreSQL/Redis на сервере 2, `WW_TEST=1`, отдельная internal Docker network, синтетические данные, без production credentials и внешних API. **242 passed, 175 warnings, 203,86 s** на окончательных исходниках: `test_sync_coverage`, `test_metrika_goal_work`, `test_metrika_sync_work`, `test_metrika_history_work`, `test_ads_sync_work`, `test_ads_sync_contract`, `test_metrika_goal_batch`, `test_sync_followup`, `test_integration_work_scope`.

Использовались runtime dependencies образа `admirra-devops:3d65ef3` (`sha256:f8438bea893dad0083ab2b8d642ff4bb71e27a4143092cdc1a710b51013820f8`) и read-only исходники из Git `ed97823` с точечным coverage patch. Это targeted regression, **не** полный manifest окончательного release image и не live provider test. Проверены upgrade/downgrade таблицы, интервальные пробелы/пересечения/replay, смена настроек A/B/A, credential rotation, scope/identity-map race, expired fence/атомарный rollback фактов и покрытия, missing goals, confirmed empty и три рекламных канала. `git diff --check` и Python compile проверка также прошли.

## Границы и следующий этап

1. Подключить coverage к сохраняемым требованиям report snapshot: integration/stage/date/settings, freshness threshold, deadline ожидания и повторная проверка перед формированием. Не сохранять один `ready=True` вместо требований.
2. Отдельно реализовать per-stage failure/outcome ledger, пользовательские partial/waiting статусы и работу с missing goals. Этот пакет не меняет прежний общий business SUCCESS и не выдаёт его за полноценный per-stage статус.
3. Согласовать freshness policy для отчётов, AI и детектора, включая предыдущий сравнительный период и все источники агрегата; затем добавить consumers и failure tests. Пока они не используют новый reader.
4. **Не включать freshness barriers при legacy writers:** старые обработчики не обновляют ledger. Перед включением — миграции, drain/выключение legacy, exclusive durable writers и новые подтверждённые sync. Нельзя backfill-ить coverage по существованию строк статистики.
5. Перед cutover остаются общий regression/restore на окончательном артефакте, live provider acceptance и mixed-load. Никаких production migrations, смены images, scheduler, workers или ingress в этом этапе нет.

S3 и две ночи наблюдения остаются отложенными по решению владельца, а не выполненными.
