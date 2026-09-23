# Профиль переключения 24.09 — подготовлен, не включён

Единый список feature flags: `ops/launch_flags.json`. Применять одинаково к
API1, API2, workers и scheduler; `APP_PROCESS_ROLE` задавать отдельно. Файл не
содержит credentials и сам ничего не запускает. Существующий
`compose.workers.yml` содержит пока только базовые guards, не полный профиль.

## Этапы и зависимости

1. Durable ledger/outbox, delivery/idempotency guards, freshness и consumer
   refresh включены. Billing queue и lead guards тоже включены: после первой
   записи их выключение не является допустимым откатом. Legacy document reads
   сохранены; новые exports/links используют общий artifact transport и DB ledger.
2. Shared read cache на первом этапе **выключен**. Сначала совпадение чисел и
   устойчивый worker/API runtime, затем отдельное включение с общим Redis
   credential/profile namespace. Никакого FLUSHALL. Это кэш транспортных чтений
   Метрики, не обещание кэшировать все SQL/страницы.
3. AI prewarm выключен; очередь `ai.prewarm` без consumer. Предварительный
   платный прогрев не должен неожиданно стартовать при первом календарном tick.
4. `DB_AUTO_BOOTSTRAP`, `RUN_SYNC_WORKER`, `RUN_API_SCHEDULER` выключены везде.
   API role=`api`, consumers=`worker`, единственный calendar/outbox=`scheduler`.
   Тесты профиля запрещают `legacy`/`sync` роли.

## Значения вне общего списка flags

- Image: `admirra-devops:24f58b7`, digest
  `sha256:57ac503afcdf6136a90d4bbb9903975ed98cefd9c1ca927a465f4d085930a8dd`.
  `APP_RELEASE=24f58b7`, expected schema `f68b92a3b4c5`.
  Captured old runtime env не должен затереть APP_RELEASE нового image.
- API DB: `/etc/admirra/db-api.env`, pool=5, overflow=0, timeout=5s;
  Redis `/etc/admirra/redis-api.env`. Не брать superuser URL из старого .env.
- Workers: `/etc/admirra/worker.env`, `/etc/admirra/redis-worker.env`, pool=2,
  overflow=0; шесть prefork children суммарно, scheduler ещё два SQL connections.
  Worker Redis DNS `broker`/`cache` работает в `admirra-workers_work`,
  поэтому host network не эквивалентен подготовленному Compose.
- Scheduler: только `/etc/admirra/scheduler.env` + Redis; без provider credentials
  и файловых mounts. `LEAD_ALERT_TIMEZONE=UTC` сохраняет legacy расписание.
  Первый cursor инициализируется текущей минутой, без массовой отправки
  исторически пропущенных клиентских отчётов.
- API1: прежний uploads + private rejected-leads + artifact API1 mTLS.
  API2: `compose.shared-api-files.yml`, общий RW uploads и отдельный API2 mTLS.
  Workers: RO uploads, RW private rejected-leads, worker mTLS. TLS paths под
  `/run/artifact`, service `https://10.77.0.1:9443`.
- Private DB/Redis/TLS проверять из контейнерной сети каждого нового role profile,
  не подменять это тестом с host network.
- Сохранить host ports, networks, auth/encryption keys и unrelated provider/
  billing/mail настройки. Секреты: root-only config, без compose config на экран.
  Использовать raw env или проверенную literal JSON escaping для `$`.

## Откат — важная граница

До первого durable admission сохранённые API/frontend/automation images —
pre-cutover baseline. Даже здесь нельзя downgrade/delete additive schema или
возвращать snapshot DB поверх новых пользовательских записей.

После первого нового job/payment/lead/artifact admission старый backend
`875ab667…` **не совместимый worker rollback**: в нём нет новых guards.
Запрещено запускать старый automation/embedded worker с новым backlog.

Безопасная остановка распространения ошибки: закрыть admission новых sync/
report/AI, остановить новый scheduler, дать running consumers завершить работу
без hard kill, сохранить ledger/outbox/unknown receipts. Истёкшая lease не
доказывает, что сообщение или платёж не отправлены. API, callbacks и финансовые
guards остаются на совместимом runtime; unknown требует reconciliation, не replay.

Это **containment/degraded mode**, не доказательство полного обратного cutover.
До activation требуется репетиция совместимого rollback либо проверенного bridge
на isolated migrated DB. Crash/recovery Celery и старые image tags этот gate
сами по себе не закрывают.

## Что не выполнено этим файлом

Не выполнены: production env activation, migrations, остановка legacy,
запуск новых consumers/calendar, E2E запись разрешённого job и расширение API2.
Непрошедшие gates не проставлять true в cutover evidence.
Окна 03:00/05:00 МСК исключены. Canary требует наблюдения по §20.5 ТЗ;
отложенные владельцем две ночи не отменяют контроль каждой ступени.
