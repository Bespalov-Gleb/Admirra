# AdMirra DevOps — актуальный остаток до полного переключения

Обновлено после подключения Telegram 20.09.2026. Это **не** утверждение, что весь DevOps-проект готов: ниже три крупных этапа, внутри которых остаётся существенная работа. Полное ТЗ: [admirra_devops_completion_tz_2026-09-11.md](admirra_devops_completion_tz_2026-09-11.md).

## Уже в production

- API-2 / Redis / приватная сеть / exporters / ingress guard; 10% canary только четырёх разрешённых GET/HEAD routes. Dashboard, mutations и SSE на две реплики пока не переключены.
- AI gateway и отдельный AI hotfix `0e5f031`: quota ledger / request idempotency. Backend `6321c5fb…`, frontend `680b8893…`, automation `33b4ca03…`; полные digests в `ops/rollback_images.json`. Runtime не равен git checkout `/root/Admirra`, нельзя деплоить blanket pull/build/up.
- Central Prometheus: 7 targets / 23 rules. Alertmanager и внешний public heartbeat настроены для группы AdMirra Alerts. Сетевая доставка из API-1 идёт через закрытый WireGuard gateway, внешний heartbeat — напрямую. [Проверки и ограничения](devops-telegram-alerts-2026-09-20.md). Подтверждение фактического получения человеком тестовых пар пока ожидается, gate автоматически не отмечен.
- На API-2 root LVM/ext4 расширен из уже выделенного свободного места: 18,47 → 34,47 GiB, свободно около 19 GiB вместо 3,5 GiB; запас VG 2,47 GiB. Без удаления данных/перезагрузки; services healthy. Metadata backup `/etc/lvm/backup/ubuntu-vg.before-telegram-20260920`.
- Encrypted daily backup на server 2; post-hotfix backup `20260920T190219Z-a6b49102` успешно восстановлен в изоляции до будущего schema head `cd9e0f1a2b3c` (46 s).
- В production schema остаётся `cc3d4e5f6a7b` плюс additive assistant ledger; новая общая миграционная цепочка/worker consumers **не включены**.

## 1. Завершить безопасную логику фоновых процессов

- Полный sync/history: убрать долгие SQL-транзакции во время внешнего HTTP, завершить settings/coverage guards и follow-up диапазонов по каналам. Goals-only / detector paths не закрывают полный sync.
- `nightly.enqueue` и `reports.rules` разбиты на bounded tenant-scoped children в candidate `3e5ddae`, не production. Parent success означает планирование, не успех всех children.
- `reports.export`, billing maintenance, lead notifications сохраняют общие handlers: ограничить scope и внешние действия. Завершить report freshness barrier и разделение подготовки/отправки. AI prewarm пока выключен.
- Для расширения API-2 нужны проверки общего файлового состояния, cache revisions/invalidation, upload/SSE и drain; второй сервер ещё не имеет собственного peer к AI gateway.
- Evidence: [calendar candidate — 748 passed](devops-calendar-candidate-2026-09-20.md), [ревью и найденные gaps](devops-review-2026-09-20.md).

## 2. Финальная нагрузочная и recovery-приёмка

- Реализовать scoped provider peak launcher, а не только validator/observer: разрешённый test owner/project/integration, жёсткие лимиты внешних запросов/стоимости, без реальных клиентских отправок и банковских списаний. Тестовый аккаунт уже предоставлен, повторно спрашивать его не нужно.
- Прогнать одновременно чтение дашборда, manual/night sync, подготовку отчёта, AI и billing sandbox. Замерить память, DB pools/locks, latency, очереди, cache и поведение отказов. 40/40 HTTP 200 с idle workers — не real-provider peak acceptance.
- Проверить rollback с новыми child kinds, неопределёнными side effects и свежей БД. Не возвращать legacy consumer к незнакомым durable jobs.
- Получить подтверждение владельца, что тестовые уведомления «проблема → восстановлено» обоих путей видны в Telegram, и определить ответственного за реакцию. Одного HTTP/API success недостаточно для human acceptance.
- Подтвердить offline-копию recovery key. Новые notifications/SQL success не заменяют эту проверку.

## 3. Контролируемое переключение и наблюдение

- Окно с ответственным, вне 03:00/05:00 МСК. Перед ним новый backup, актуальные schema/artifact/restore и cutover preflight; старые evidence не подставлять как свежие.
- Admission gate → drain legacy jobs/scheduler → migrations → candidate API-1 и минимальные workers с единственным scheduler → разрешённая end-to-end задача → открыть admission. Billing/lead webhooks не глушить общим запретом.
- Только после корректного single-API режима обновить API-2 на тот же digest/schema, расширять canary ступенями. Не запускать старый и новый глобальные scheduler одновременно.
- Две последовательные ночи наблюдения, controlled report / AI usage / dashboard latency и финальный DoD. Этот этап происходит после включения, а не подменяется коротким smoke.

## Что сознательно отложено / не является HA

S3/PITR отложены по решению владельца максимум на 30 дней при свежем server-2 backup, проверенном restore и offline recovery key. Риск — RPO около суток и потеря восстановления при утрате обоих узлов. Server 2 не является независимым offsite. PostgreSQL остаётся одним primary, два API не дают HA базы. Telegram и AI gateway также остаются общими точками отказа доставки алертов; независимый второй канал пока не настроен.
