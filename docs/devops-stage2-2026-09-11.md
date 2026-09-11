# AdMirra — долговечные задания и приватная сеть, этап 2

Дата: 11 сентября 2026. Продолжение `docs/devops-implementation-2026-09-11.md`.
Пользователь организует независимое backup-хранилище отдельно; реализация остальных частей продолжается.

## Фактический статус

Это **не завершённый переход production на два сервера**. Новые очереди работают и проверяются
на изолированном стенде сервера 2. Бизнес-код production, PostgreSQL-схема, nginx, текущие
контейнеры и расписания не переключены. Единственное изменение на обоих рабочих хостах —
установка `wireguard-tools` и включение выделенного интерфейса `admirra0`.

### Уже включено на хостах

- Сервер 1: `91.221.68.90`, адрес туннеля `10.77.0.1/32`.
- Сервер 2: `91.221.68.94`, адрес туннеля `10.77.0.2/32`.
- UDP 51820, MTU 1420, keepalive 25 секунд, AllowedIPs только адрес второго участника `/32`.
- `wg-quick@admirra0` включён в автозагрузку на обоих хостах.
- Приватные ключи созданы на самих серверах в `/etc/wireguard/admirra0.key`, режим 0600;
  конфигурация `/etc/wireguard/admirra0.conf` также 0600. Ключи не копировались в git/чат.
- Проверены handshake и ping в обе стороны: 0% потерь, средняя задержка примерно 0,7–1,0 мс.
- Default routes остались через прежний `eth0`; SSH доступен. Контейнеры не перезапускались,
  `https://admirra.ru` после включения туннеля вернул 200.
- PostgreSQL и Redis **не опубликованы** через туннель этим этапом. Firewall не изменён.

Повторяемая настройка: `ops/provision_private_link.py` — сначала `--prepare` на каждом хосте,
затем `--configure` с публичным ключом второго. Существующую отличающуюся конфигурацию скрипт
не перезаписывает, пересекающиеся маршруты отклоняет. Нет DNS/NAT/default-route изменений.

Откат только туннеля: `systemctl disable --now wg-quick@admirra0` на обоих серверах.
Делать это через публичный SSH, не через отключаемый туннель. После подключения production
зависимостей такой откат уже потребует отдельного переключения сервисов.

## Реализовано в коде

### PostgreSQL — источник состояния, Redis — транспорт

Миграция `dd4e5f6a7b8c` после `cc3d4e5f6a7b` создаёт:

- `background_jobs`: вид работы, очередь, resource, client scope, payload, состояние,
  попытки, уникальный dedupe key, lease token и срок аренды.
- `background_outbox`: атомарная постановка в той же транзакции, что бизнес-задание.
- `background_schedule_cursor`: подтверждённая позиция календаря.

Существующая `sync_jobs` остаётся контрактом для UI. Новый ручной/ночной sync создаётся вместе
с durable-заданием, под блокировкой интеграции. Несколько API не могут одновременно создать
две активные синхронизации одного кабинета. Повтор публикации в Redis не означает повтор работы.
Queued-задания перепубликуются через 30 секунд: потеря данных Redis не теряет запись PostgreSQL.

Celery получает только UUID, не токены кабинетов и не клиентские данные. Исполняемые обработчики
заданы явным списком. JSON-only, без pickle/result backend; late ACK, prefetch=1, prefork,
мягкий/жёсткий timeout 3000/3060 секунд, обновление child после 50 заданий или порога RSS.
После fork пул PostgreSQL пересоздаётся. Версии Celery 5.6.3 / Kombu 5.6.2 потребовали заменить
Python Redis-клиент 8.1.0 на совместимый 6.4.0. `pip check` проходит; версии закреплены.

### Эксклюзивность и восстановление

- PostgreSQL сериализует получение задач; один активный job на ресурс интеграции.
  Полный sync и goals-only sync одного кабинета не выполняются одновременно.
- Общий предел sync — 4; на проект/client_id — 2. Это **лимит проекта**, не лимит владельца
  аккаунта. Отдельная fairness-политика между платящими организациями ещё не реализована.
- Lease 120 секунд, heartbeat 20 секунд. Потерявший связь child прекращает работу.
- Каждая внешняя SQLAlchemy Session в контексте job проверяет lease перед внешним COMMIT.
  Старый воркер не может зафиксировать данные после передачи задачи новому.
- Освобождение SAVEPOINT не держит блокировку lease до последующих HTTP/LLM вызовов.
  Внешний COMMIT всё равно проверяется — отдельный регрессионный тест.
- Истёкшие replay-safe задачи восстанавливаются с ограничением попыток. Отчёты/платёжные
  операции с неизвестным результатом получают `uncertain`, автоматически не повторяются.
- Обычная ошибка sync использует существующую классификацию/retry-логику; новая очередь
  не умножает её на автоматический Celery autoretry. Уже успешный SyncJob повторно не запускается.
- Завершённые succeeded/failed записи удаляются пакетами после 30 дней; queued/running/uncertain
  не удаляются. Последний случай требует сверки результата человеком/специальным reconciler.

Это не обещание exactly-once внешних HTTP-эффектов. Внутри старых обработчиков ещё есть
best-effort/catch-and-log участки. Получение ответов от рекламных API/LLM при аварийном повторе
может повториться; новая запись статистики защищена, экономическая идемпотентность LLM не заявлена.

### Очереди и календарь

| Очередь | Работа |
|---|---|
| sync.manual | Ручной sync, goals-only обновления |
| sync.nightly | Ночная синхронизация |
| reports | Проектные отчёты, экспорты, уведомления lead-validator |
| maintenance | Постановка ночных sync, VK maintenance, billing maintenance |
| ai.prewarm | Прогрев AI-комментариев |

Календарь перенесён в отдельный процесс; повторные ticks дедуплицируются PostgreSQL.
03:00 МСК — ночные sync; 05:00 МСК — экспорты, AI-прогрев и billing; проектные отчёты — каждую
минуту; VK maintenance — раз в час. Lead-validator сохранён в **UTC**, как в проверенном
production-контейнере: 09:00 daily, понедельник 09:30 weekly, без скрытой смены часового пояса.

Catch-up ограничен сутками. Проектный отчёт старше 15 минут не отправляется задним числом:
проверка есть и при планировании, и при исполнении после ожидания в очереди. Пропущенные
старые отправки не объявляются доставленными. Первая установка календаря начинает с текущей
минуты и не запускает неожиданную историческую рассылку.

### Ограничения API и соединений

HTTP-клиенты Direct, Metrica, VK и Avito получают общий Redis limiter при
`DISTRIBUTED_RATE_LIMITS=true`. Атомарный Lua использует время Redis, ограничивает общий поток
и конкретный credential; ключ credential — SHA-256, исходные токены/логины в Redis-ключах отсутствуют.
HTTP 429 сохраняет общий для этого credential cooldown. При недоступности limiter запрос
не отправляется. Локальные ограничители сохранены как дополнительный консервативный предел.

Стартовые общие RPS: Direct 10, Metrica 2, VK 10, Avito 5; это эксплуатационные настройки,
не утверждение о максимальных договорных квотах API. Увеличивать после измерений/проверки квот.

Для новых ролей SQL statement timeout по умолчанию 60 секунд, lock timeout 10 секунд;
размеры пула задаются на **каждый процесс**, worker-compose использует 2+0 на child.
Legacy defaults сохранены до переключения. `DATABASE_URL` options не теряются при добавлении timeout.

### Запуск и диагностика

`DURABLE_TASKS` выключен по умолчанию. Включение несовместимо с legacy/sync ролями.
Worker CLI: `python -m automation.work_worker`; scheduler: `python -m automation.work_control`.
Проверка запуска требует версию релиза, совпадение Alembic revision и отсутствие старых активных
SyncJob без durable-записи. API в durable-режиме проходит ту же проверку.

`python -m ops.work_status` выполняет read-only запросы и выдаёт JSON: состояния по очередям,
возраст старейшей задачи, истёкшие leases, uncertain и outbox. Exit 2 сигнализирует проблему.
Автоматическая отправка этих сигналов дежурному пока не подключена.

## Конфигурация второго узла — подготовлена, не включена

`ops/compose.workers.yml`: два manual + два nightly child, отдельные reports/maintenance/prewarm,
один scheduler; ограничения CPU/RAM/PID, non-root workers, read-only root filesystem,
ротация логов, grace period для завершения работы. Redis broker: AOF/everysec + snapshot,
noeviction, maxmemory 256 МБ; отдельный disposable cache: LFU, maxmemory 128 МБ.
Образы Redis закреплены digest. Порты привязаны только к `10.77.0.2`, не к публичному IP.

Compose проверен через `config --no-env-resolution --quiet`. Это синтаксическая проверка,
**не проверка готовности production-конфигов**. Требуются `/etc/admirra/worker.env`, ACL Redis
с отключённым default user, отдельными пользователями broker/cache/health и паролями,
`redis-health.env` с `REDISCLI_AUTH` для health user (только PING), каталог `/srv/admirra/worker-data`
с правами UID 10001. Конфиги с секретами не создавались/не переносились этим этапом.
Нужны reviewed DB-доступ по туннелю и host/Docker firewall до включения этих служб.

## Проверки

На отдельной internal Docker-сети без опубликованных портов и исходящих обращений:
PostgreSQL 15.18, Redis 7.4, Python 3.13, non-root/read-only test container.

Контрольный набор: **225 passed, 1 deselected**, 46 предупреждений на момент проверки исходников.
Единственный deselected — проверка Vue-файла, не включаемого в backend artifact. Это не утверждение,
что весь репозиторный test suite проверен. Устаревшие тесты `tests/test_sync.py` исправлены:
актуальные async API, profile selection, refresh token, пустой отчёт, раздельные sessions,
rollback и продолжение соседней интеграции. Старые 7 baseline failures больше не исключаются.

Проверены конкурентная постановка/claim, caps, outbox rollback, crash после publish,
потеря транспортных сообщений, истечение lease, fencing/savepoint, unsafe→uncertain, retention,
calendar catch-up, schema mismatch и orphaned legacy jobs, HTTP hooks, fail-closed limiter,
shared 429 cooldown и миграция/downgrade. Реальный prefork child принудительно завершался
SIGKILL во время незакоммиченного INSERT; запись откатилась, новая попытка выполнилась,
тройная повторная доставка оставила ровно один итоговый INSERT.

Повторение проверки готового образа без исходников с хоста:

```sh
TEST_IMAGE=<проверяемый-образ> docker compose -f ops/compose.isolated.yml -f ops/compose.artifact-tests.yml run --rm tests
docker compose -f ops/compose.isolated.yml down
```

## Что ещё необходимо до полного production cutover

1. Независимый backup/restore и WAL-стратегия; доступ к хранилищу пользователь организует отдельно.
2. Приватная публикация PostgreSQL, отдельные DB/Redis credentials, firewall, deploy-user,
   безопасная доставка секретов и общий immutable release на узлах.
3. Partial-статусы sync вместо ложного SUCCESS при сбое части источников; короткие DB-транзакции.
4. Идемпотентность/uncertain на уровне **каждого получателя отчёта**, UI повторов и reconciliation.
   Текущий generic ledger сам по себе не закрывает окно «провайдер принял, локальный commit не прошёл».
   Экспорты и отправки стоит разнести дальше при росте времени выполнения.
5. Tenant-safe кэш и инвалидация после commit; убрать N+1/fan-out карточек. Кэш целого мутирующего
   `/dashboard/summary` не включать; выделить чистые вычислительные функции.
6. Вынести in-memory backfill/report tokens/local artifacts/uploads; проверить AI SSE/drain;
   лишь затем подключать API-2 к nginx upstream. Сейчас балансировщик не переключён.
7. Алерты/метрики, нагрузочная приёмка, ночной прогон и проверенный rollback.

Не запускать старый embedded worker и новый Celery одновременно. Перед переходом остановить
постановку работ на время drain, проверить активные SyncJob, применить миграцию и только затем
включать новые роли. Откат миграции запрещён при queued/running/uncertain работах.

## Источники технических решений

[Celery Redis transport](https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/redis.html),
[Celery worker lifecycle](https://docs.celeryq.dev/en/stable/userguide/workers.html),
[SQLAlchemy Session events](https://docs.sqlalchemy.org/en/20/orm/session_events.html),
[HTTPX event hooks](https://www.python-httpx.org/advanced/event-hooks/),
[Redis persistence](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/),
[WireGuard quick start](https://www.wireguard.com/quickstart/).
