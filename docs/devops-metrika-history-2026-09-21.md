# История standalone Метрики без SQL-соединений во время HTTP

Candidate `cb3be39`, 21.09.2026. Не production rollout; новая схема/worker consumers всё ещё не включены.

## Изменение

`history.backfill` для `YANDEX_METRIKA` больше не вызывает монолитный `sync_integration` с открытой SQL-сессией. Диспетчер закрывает свою сессию, затем переиспользует `metrika_goal_work`:

1. Короткая fenced-транзакция: authoritative owner/project/lease guard, чтение настроек, дат, известных названий целей; snapshot без ORM-ссылок. Дополнительно проверяется, что snapshot не сменил owner/project/platform между guard и подготовкой.
2. Метаданные и статистика всех целей/дат собираются без занятого SQL-соединения. Нет fallback «ошибка API = нули».
3. Короткая apply-транзакция: client → integration locks, повторная сверка settings/owner/status, атомарная замена окна и проверка lease перед commit. Cache invalidation только после commit.

Сохранены: выбор основного goal, все цели при отсутствии явного выбора у standalone counter, 90 дней первой загрузки и attribution lookback, объединённая строка `all`, namespace integration/project и уведомления о реально исчезнувших целях. Для standalone используется counter из `account_id`, не `selected_counters` связанного рекламного кабинета. Login-значение вместо числового counter — авторизационная связь: пропускается без provider calls и без изменения текущего sync watermark.

Историческая загрузка не меняет `last_sync_at`, `sync_status` и `last_sync_trigger` текущей синхронизации; не запускает detector/LLM. Actual start date обновляется SQL-частью, как раньше. Потеря lease, смена владельца/проекта/целей/счётчика/токена/платформы во время HTTP не публикует собранные строки; прежние значения сохраняются.

## Проверки

Первый targeted run: **94 passed**, 91,46 с, реальный изолированный PostgreSQL, внешние API подменены. Финальный manifest дополнен отдельной гонкой смены платформы между guard и prepare. HTTP mocks проверяют `pool.checkedout() == 0`; cache callback проверяет отсутствие занятого соединения и видимость уже committed данных через новую сессию.

Полный manifest чистого Git-артефакта `cb3be39`: **979 passed, 1 skipped, 1 deselected, 54 warnings, 6 subtests passed**, 365,68 с. Все 16 новых случаев вошли в общий прогон. Image `admirra-devops:cb3be39`, digest `sha256:fa5bffcb8e9fef118ed5ecc57418264356b555eee85fb1dbabc0a22ce84f8fcc`. Test network internal=true, production credentials не используются; frontend-source assertion исключён штатно, optional previous-release comparison пропущен.

На этом же артефакте повторно восстановлен backup `20260921T200100Z-b4397303`: 51 с, network=none, миграции до `cd9e0f1a2b3c`, preflight/boot четырёх групп workers, readiness/auth guard и чтение тестового аккаунта — passed. 40/40 HTTP 200, concurrency 4, p50 150,94 мс / p95 944,54 мс / max 1044,04 мс. Это idle-worker/read smoke, не смешанная нагрузка с реальными провайдерами и не browser timing.

Test/restore containers, network и volume удалены. Production digests неизменны: backend `4ca866eb…`, frontend `274aad1d…`, automation `33b4ca03…`; API-2 healthy, `/projects` HTTP 200, 7/7 monitoring targets up и 0 active alerts. Клиентские рассылки, банковские операции и provider calls не выполнялись.

## Остаток и ограничения

Это только durable **история standalone Метрики** и расширение общего коллектора. Полная manual/night синхронизация standalone Метрики пока использует прежний путь. Direct/VK/Avito history и sync тоже остаются legacy: их HTTP/SQL границы, token refresh и coverage/settings guards нужно завершить отдельно. Общий SYNC-пункт не закрыт.

Сбор окна пока хранит rows в памяти; этот пакет не добавляет универсальный memory/spool budget для больших provider responses. Сохраняется существующая ограниченная очередь backfill. Mixed-provider peak, единый report pipeline, billing reconciliation, lead notifications и расширение API-2 canary остаются отдельными gates. S3/PITR и две ночи наблюдения отложены владельцем, не выполнены.
