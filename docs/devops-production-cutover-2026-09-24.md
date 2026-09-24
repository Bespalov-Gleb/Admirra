# Production cutover — 24.09.2026

Статус на 08:32 UTC: **API1/API2, frontend, consumers и scheduler переключены**.
Расширение публичной доли API2 ещё идёт, не объявлено завершённым.
Владелец подтвердил отдельное сохранение AGE recovery key. Сам ключ здесь не хранится.
S3/PITR вне двух runtime-серверов и две ночи наблюдения отложены владельцем.
Операционный срок пересмотра временного backup-исключения: 01.10.2026.

## Артефакты и конфигурации

- API/worker source `2ce9513`, image
  `sha256:ef9e5c40671bf570671ddf7f890d364f4648cf64ed030a91eedd9923b1dd8cb4`.
- Frontend source `aeefa00`, image
  `sha256:1b9fbbf8b894e8de33ac97c497c200307e68f182b8bbc8e5a273cada67a4512e`.
  Публичный `/ai` отдаёт entry `index-q99I1Q7L.js`. Лендинг `/` имеет другой index.
- Production Alembic: `cc3d4e5f6a7b` → `f68b92a3b4c5`, одноразовый migration
  container, timeout/lock bounds, отдельные restricted API/worker credentials.
- Server1: `/etc/admirra/releases/cutover-2ce9513-r2/`.
- Server2: `/etc/admirra/releases/cutover-2ce9513/`.
- `admirra-automation-1` остановлен, restart policy `no`. Embedded schedulers
  API отключены. Новый единственный календарь — `admirra-workers-scheduler-1`.
- Workers: manual 2, nightly/backfill 2, reports 1, maintenance 1.
  Broker/cache не пересоздавались. Registration notifier/admin frontend не затронуты.
- Launch guards включены по `ops/launch_flags.json`; `SHARED_READ_CACHE=false`
  и платный AI prewarm выключен. Не заявлять эффект shared aggregate cache,
  пока его отдельное включение не выполнено и не проверено.

## Фактическая приёмка

- Новый encrypted backup `20260924T080459Z-855d8d68` получен server2, три
  encrypted object hashes совпали с расшифрованным manifest.
- Последний restore/read-load закончился 07:57:50 UTC: 74 s, schema f68,
  API/worker boot passed, 64/64 HTTP200. Относится к backup 07:45 того же утра.
- Полная регрессия immutable image: 1639 passed, 1 skipped, 1 deselected,
  6 subtests passed. Runtime renderer и новые ops guards тестировались отдельно.
- Финальный preflight: 50 checks passed. Admission закрыт на время миграции,
  сейчас открыт. Старый API2 исключался перед заменой, параллельного старого
  и нового scheduler не было. Legacy automation использовал весь graceful
  stop deadline; на входе jobs/sending reports/AI runs = 0.
- API1: batch 64 проекта × 4 канала 801.99 ms; API2 1013.49 ms.
  По 12 individual comparisons и access guards прошли. Не SLO 20 видимых карточек.
- Семь read routes через обе реплики возвращают одинаковые данные.
- Две реальные manual sync (Яндекс и VK, только тестовый владелец, days=1,
  force_full=false): SUCCESS; durable jobs succeeded, attempt=1. Первоначальный
  smoke ошибочно ожидал lowercase статусы; исправлен только probe, существующие
  jobs дочитаны без повторного enqueue. Related backfills succeeded.
- Один короткий AI request: succeeded, provider_calls=1, replay через API2
  вернул сохранённый ответ без нового вызова. На согласованном тестовом аккаунте
  `charged=false`; не выдавать эту проверку за списание платной квоты.
- Report `0bc50a57-0238-4028-b305-52a0e0a25767`: readiness ready, PDF 18400 bytes
  одинаков на обоих API. Одна отправка только владельцу тестового аккаунта,
  state sent / recipient receipt accepted / attempt=1. Повтор approve запрещён.
  Принятие провайдером не является самостоятельным доказательством inbox delivery.
- Alertmanager принял тест firing/resolved; telegram transport errors=0.
  Старый readiness monitor ожидал legacy payload: исправлен в `be5b0f5`,
  8 unit tests passed. Оба host probes теперь healthy, ложные alerts resolved.

## Публичное распределение

08:23:31 UTC: новый API2 включён weight 1:9 на четырёх safe-read routes.
Каждая ступень не короче 30 минут; controlled traffic — 24 reads/min,
concurrency 2, только согласованный test account. Ни provider calls,
ни отправки/платежи этим монитором не создаются.

Следующие ступени: 25% с расширением business API routes, затем 50%.
Для общего API/SSE `proxy_next_upstream off`: никакого автоматического
повтора потенциально уже выполненной операции. Четыре проверенных safe-read
routes сохраняют короткий bounded failover. Фактическую долю считать по access log:
least_conn weights не гарантируют точную долю запросов, особенно при SSE.

## Мониторинг и действия оператора

`admirra-runtime-monitor@ingress` читает только агрегаты БД: schema, календарь,
expired leases, uncertain jobs/report/AI, outbox delay. `@workers` проверяет
running/OOM, role/release/schema пяти новых сервисов. Данные/секреты не печатает.
Metrics в `/var/lib/admirra-api2-monitor/runtime-*.prom`, существующий node-exporter.
Отсутствие свежих метрик и unhealthy runtime дают critical через Alertmanager.

При критичной ошибке остановить расширение API2. Не повторять uncertain
платёж/отправку/AI автоматически; сначала сверить operation/recipient receipt.
Проверить scheduler last_tick, очереди и provider auth отдельно от общей latency.

## Откат после приёма durable jobs

Закрыть admission, исключить API2, остановить новый scheduler, выполнить bounded
drain workers и сохранить receipts. Не запускать старую automation/старый API
с legacy writers. Совместимый API-only degraded rollback config сохранён:
`/etc/admirra/releases/cutover-2ce9513-r2/api1-compatible-rollback.json`, image
`sha256:b959c09111a5278493e072452cec334bce7be4dda6e250a72c29be716eda1482`.
Новые worker handlers из rollback image запускать нельзя. Схему не downgrade,
production DB не перезаписывать restore поверх новых пользовательских записей.

Protected evidence/logs: release-root на server1. Локальные незавершённые правки
владельца mobile/landing не включались в эти образы и остались нетронутыми.
