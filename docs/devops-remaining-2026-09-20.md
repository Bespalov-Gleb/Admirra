# AdMirra DevOps — актуальный остаток до production cutover

Состояние на 20.09.2026 после commit `649bc79`. Этот файл — короткая оперативная карта; полные требования и история evidence находятся в `admirra_devops_completion_tz_2026-09-11.md`.

## Уже подтверждено

- Server 2 доступен только через нужные public/private границы; WireGuard, Docker, API-2, Redis, exporters и timers автоматически восстановились после полной OS reboot.
- Ограниченный read-canary на четырёх GET/HEAD routes получает 10%. Reboot и отдельный WireGuard fault прошли с реальным fallback; после исправления stale keepalive — 120/120 ответов без итоговых `5xx/000`, max 2,106 s.
- Центральный Prometheus видит шесть targets. PostgreSQL/Redis exporters используют отдельные read-only identities; ожидаемые fault alerts после теста автоматически погасли, текущий alert set пуст.
- Ежедневный encrypted PostgreSQL + runtime backup уходит на restricted repository server 2. Retention и stale alert включены.
- Полный backup восстановлен; migrations `cc3d4e5f6a7b → bc8d9e0f1a2b`, release-manifest checksum, worker preflight, четыре launch workers и API smoke прошли в `network=none`. Временные ресурсы полностью удалены.
- Immutable candidate `acf6ed8`, image `sha256:ad9559725e724789281765526f85839b8b9adf604c114ad25850812b0c544d0a`: 603 passed, 1 skipped, 1 deselected; artifact hygiene и `pip check` успешны.
- Launch capacity profile вместе с API-2: 6144 MiB caps, 1796 MiB OS headroom, worker DB 14 + reserve 4 из 20, API-2 pool 5. `ai.prewarm` явно выключен до отдельного решения. Arithmetic/boot приняты; одновременный worker-set + real-snapshot API read-load дал 40/40 HTTP 200, p95 692 ms. Worker/provider peak ещё не принят.
- Production application остаётся на `cdf0a4d` / schema `cc3d4e5f6a7b`; candidate migrations/workers не включались.

## P0 — блокирует миграцию production

1. **Внешняя recovery point.** Нужен storage вне обоих runtime-серверов с versioning/immutability и раздельными writer/restore/delete credentials. После доступа: continuous WAL/PITR, escrow age/recovery keys, повторный restore именно из внешнего repository. Текущий межсерверный daily backup даёт RPO около суток и не переживает потерю обоих узлов.
2. **Alert → человек.** Alertmanager с секретом через file, pinned image, deploy/rollback, Prometheus routing/rules и synthetic firing/resolved smoke [подготовлен и проверен](devops-alertmanager-prepared-2026-09-20.md). Владелец выбирает отдельный технический webhook и ответственного; после защищённой установки URL остаются production deploy, подтверждение человеком firing/resolved и внешний heartbeat вне обоих app servers.
3. **Worker/provider peak acceptance.** Read API + idle worker mixed-smoke уже пройден. На восстановленной копии либо утверждённом test tenant остаётся выполнить bounded manual/night/report/AI/billing load; измерить RSS/PSS, CPU, Redis/AOF, DB pool/locks, provider quotas и latency.
4. **Окно cutover.** Нужны дата/оператор и запрет окна 03:00/05:00 МСК. Fail-closed [cutover preflight](devops-cutover-preflight-2026-09-20.md) уже проверяет окно, точные artifacts/schema, recovery/alert evidence, отсутствие активных side effects и approvals; незаполненный шаблон блокируется. Перед окном evidence собирается заново.

## Порядок после P0

1. Перевести подготовленный [ingress admission gate](devops-cutover-admission-2026-09-20.md) в `closed`, остановить legacy scheduler/consumer и повторно подтвердить отсутствие legacy `QUEUED/RUNNING` jobs. Gate точечно оставляет billing/lead webhooks и обычные reads доступными.
2. Применить пять additive migrations отдельным job; проверить schema head и девять новых таблиц.
3. Поднять candidate API-1 без embedded scheduler/sync, затем минимальный launch worker set и единственный scheduler. Выполнить approved test job end-to-end.
4. Открыть admission, наблюдать single-API worker rollout. При correctness/side-effect uncertainty остановить claims, не повторять действие автоматически.
5. Только после стабильного single-API режима переводить API-2 на тот же digest/schema и расширять canary ступенями 10% → 25% → целевое распределение. Dashboard/mutations/SSE не добавлять до проверки shared state/files и drain.
6. Проверить две последовательные ночи, controlled report и AI usage, сравнить dashboard latency/SQL до и после; затем оформить финальный DoD.

## Не считать готовым заранее

- Наличие Redis само по себе не ускоряет дашборд: shared read-cache включается только после revision/invalidation и outage/race tests.
- Два API не означают HA базы: PostgreSQL пока остаётся single primary на server 1.
- `capacity_pass=true`, зелёный unit suite и успешный boot не доказывают provider/peak capacity.
- Server-2 repository не является независимым offsite, а nightly dump не является PITR.
