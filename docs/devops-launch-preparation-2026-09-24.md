# Подготовка фактического переключения — 24.09 утром

Владелец подтвердил намерение переключить production. S3 и наблюдение двух
ночей отложены ранее. Подтверждение отдельной копии recovery key вне серверов
и переписки пока не получено: задан отдельный вопрос. Совпадение присланного
ключа с server2 проверено без вывода значения; это не доказательство escrow.

## Новый application image

- Source `2ce9513`, `admirra-devops:2ce9513`.
- Digest `sha256:ef9e5c40671bf570671ddf7f890d364f4648cf64ed030a91eedd9923b1dd8cb4`.
- Доставлен на оба сервера. Build из git archive allowlist, без локальных
  пользовательских frontend/landing изменений и без секретов.
- Включена [приоритетная отправка писем доступа](auth-mail-priority-2026-09-24.md).
  16 targeted unit tests passed. Полная immutable-image regression:
  **1639 passed, 1 skipped, 1 deselected, 6 subtests passed**, 983.39 s.
  Isolated PostgreSQL/Redis, synthetic data, production credentials отсутствуют.
- Одно техническое письмо на согласованный тестовый адрес владельца:
  accepted → sent → **delivered**, 24.09 07:50:26 UTC. job_id
  `1x9eDn-000bi3-Hyw2`. Это проверка нового образа, не включённая production
  логика и не реальный код доступа. Другим пользователям письма не отправлялись.

## Recovery

- Свежий encrypted backup: `20260924T074511Z-e0b5f1f5`, legacy schema
  `cc3d4e5f6a7b`. Sender success 07:45:21 UTC.
- Restore + migrations до `f68b92a3b4c5`, launch flags, API/worker boot:
  passed, 247 s при параллельной регрессии. Read load не был включён в этот
  первый прогон.
- Следующая попытка read load остановилась до нагрузки: не передан обязательный
  test account. Не является успешной приёмкой нагрузки; isolated resources
  удалены штатным cleanup.
- Повтор с явным разрешённым test account: **passed, 74 s**, network=none,
  **64/64 HTTP 200**, 4 concurrent reads, p95 2068.29 ms. Список 72 проектов;
  compact/full metadata совпали. Summary batch 64 проекта × 4 канала:
  959.18 ms, 12 сравнений совпали, access guards passed. Это изолированная копия
  при параллельных тестах, не замер скорости публичного сайта.

## Frontend artifact

Clean frontend source `aeefa00` не менялся в последующих application commits;
518 tracked files сверены с git blob побайтно. Ранее выполненные **53 node
tests** и production build — passed. Dist собран в отдельном каталоге, текущие
неоконченные mobile/landing изменения владельца не затронуты.

На server1 подготовлен `admirra-frontend:cutover-aeefa00`, digest
`sha256:1b9fbbf8b894e8de33ac97c497c200307e68f182b8bbc8e5a273cada67a4512e`.
Overlay на сохранённый production frontend c66a577…, старые hashed chunks не
удалены. Image-level nginx -t passed, index SHA-256 совпадает с проверенным dist:
`631349582dcc18f90759409378269f5d36ce3b203f01a6fef5753deab36d9371`.
Ключевые новые chunks присутствуют. Публичный frontend не переключался,
действующий versioned Nginx bind следует сохранить при activation.

## Подготовленные role configurations

Renderer `ops/render_launch_runtime.py`, операционные commits `97312de`,
`4eadce7`; **13 unit tests passed**. Renderer не запускает сервисы и не
мигрирует БД. Сохраняет previous configs и literal `$` в root-only JSON,
проверяет Compose roundtrip; бизнес-настройки берёт из running API1, не из
более нового checkout .env. Между хостами env передан закрытым SSH pipe,
без печати или локальных credential files.

- Server1: `/etc/admirra/releases/cutover-2ce9513-r2/api1-prepared.json`.
  Прежний файл переименован в `cutover-2ce9513/api1-rejected-hairpin.json`: там обнаружен
  неработающий hairpin путь `10.77.0.1:5432` для контейнера этого же хоста.
- Server2: `/etc/admirra/releases/cutover-2ce9513/api2-prepared.json` и
  `workers-prepared.json`.
- API1 с ограниченной `admirra_api` подключается через `db:5432`; API2 —
  к private gateway; workers — `admirra_worker` через gateway.
- Все три role probes прошли DB read, authenticated Redis PING по трём
  credentials, artifact mTLS health, доступ к uploads/rejected-leads.
  Worker uid=10001, uploads read-only, rejected-leads writable. API1 DDL denied.
- Новые NFS Docker volumes API2 подготовлены. Рабочие consumers/scheduler/API
  из этих конфигураций **не запускались**; one-off diagnostics не исполняли
  background jobs, ticks или business DB writes.

## Production на момент проверки

Backend по-прежнему `875ab667…`, automation `e6f8ebec…`, оба running/restarts=0.
Schema `cc3d4e5f6a7b`, active legacy sync=0, sending reports=0, recent AI=0.
Public `/` и private API2 readiness — 200, active Prometheus alerts=[]
(это точечный снимок, перед переключением проверяется заново).

**Не выполнено:** остановка legacy, production migrations, candidate API/
workers/scheduler activation, frontend activation, E2E новой очереди и
расширение доли API2. Admission не закрывался. Prepared configs не являются
deployment evidence. Полная регрессия получена. До mutation нужны подтверждение
escrow, свежие preflight/drain/backup и существующий rollout plan с наблюдением.

Raw evidence: server2 `/opt/admirra-staging/2ce9513/`
`final-full-tests.log`, `final-launch-restore.log`,
`final-launch-read-load-approved.log`. Секретов/адресов пользователей в отчёте нет.
