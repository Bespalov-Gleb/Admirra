# AdMirra DevOps — актуальный остаток до полного переключения

Обновлено 21.09.2026 после follow-up sync, scoped export и подключения API-2 к AI gateway. Это **не** утверждение, что весь DevOps-проект готов: ниже три крупных этапа, внутри которых остаётся существенная работа. Полное ТЗ: [admirra_devops_completion_tz_2026-09-11.md](admirra_devops_completion_tz_2026-09-11.md). [Изменения и проверки 21 сентября](devops-progress-2026-09-21.md).

## Уже в production

- API-2 / Redis / приватная сеть / exporters / ingress guard; 10% canary только четырёх разрешённых GET/HEAD routes. Dashboard, mutations и SSE на две реплики пока не переключены.
- AI gateway и отдельный AI hotfix `0e5f031`: quota ledger / request idempotency. Backend `6321c5fb…`, frontend `680b8893…`, automation `33b4ca03…`; полные digests в `ops/rollback_images.json`. Runtime не равен git checkout `/root/Admirra`, нельзя деплоить blanket pull/build/up.
- Central Prometheus: 7 targets / 23 rules. Alertmanager и внешний public heartbeat настроены для группы AdMirra Alerts. Сетевая доставка из API-1 идёт через закрытый WireGuard gateway, внешний heartbeat — напрямую. [Проверки и ограничения](devops-telegram-alerts-2026-09-20.md). Подтверждение фактического получения человеком тестовых пар пока ожидается, gate автоматически не отмечен.
- На API-2 root LVM/ext4 расширен из уже выделенного свободного места: 18,47 → 34,47 GiB, свободно около 19 GiB вместо 3,5 GiB; запас VG 2,47 GiB. Без удаления данных/перезагрузки; services healthy. Metadata backup `/etc/lvm/backup/ubuntu-vg.before-telegram-20260920`.
- Encrypted daily backup на server 2; post-hotfix backup `20260920T190219Z-a6b49102` успешно восстановлен в изоляции до будущего schema head `cd9e0f1a2b3c` (46 s).
- В production schema остаётся `cc3d4e5f6a7b` плюс additive assistant ledger; новая общая миграционная цепочка/worker consumers **не включены**.
- API-2 получил собственный WireGuard peer `10.78.0.2/32` к AI gateway: private health и каталог OpenRouter проверены из его реального backend-контейнера. API-1 peer, default routes и БД/Redis-сеть сохранены. Это сеть, не полный AI/SSE rollout на API-2.

## 1. Завершить безопасную логику фоновых процессов

- Полный sync/history: убрать долгие SQL-транзакции во время внешнего HTTP, завершить settings/coverage guards по каналам. Follow-up и объединение диапазонов реализованы в candidate `7f87205`; видимая UI-связь и полный failure matrix остаются. Ошибка выбранных целей Метрики теперь не даёт ложный SUCCESS в Direct/Avito candidate `e080b13`. Standalone Метрика тоже собирает и проверяет всё окно до замены старых данных (`7e49990`, `dbb3e96`), повреждённый ответ не превращается в нули. Goals-only / detector paths и эти правки не закрывают весь sync.
- `nightly.enqueue` и `reports.rules` разбиты на bounded tenant-scoped children в candidate `3e5ddae`, не production. Parent success означает планирование, не успех всех children.
- `reports.export` теперь scoped per-project в candidate `11f935d`, Sheets IO вынесен из SQL. Остались memory bound истории, freshness barrier и полный snapshot/render/send contract.
- Billing maintenance разбит на warning/recurring children по подпискам (`286b58b`); scoped warning освобождает SQL до SMTP и проверяет период/lease при подтверждении (`6d41b24`, `11d9e40`). Остался финансовый IO/commit контракт recurring reconciliation, в том числе отмена/изменение тарифа в полёте.
- VK maintenance ограничен SQL batches по 100 drafts с безопасным продолжением (`9eb6015`). Lead notifications требуют DB-backed данных вместо process-local analytics, tenant/recipient scopes и side-effect guards; AI prewarm пока выключен.
- Новый календарный occurrence не может обойти `uncertain` на том же resource (`c45b407`). Полная операторская/UI-сверка неизвестных исходов ещё нужна.
- Для расширения API-2 нужны проверки общего файлового состояния, cache revisions/invalidation, upload/SSE и drain; сетевой peer к AI gateway уже подключён.
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
- Две последовательные ночи наблюдения **отложены владельцем 21.09.2026**. Это непроведённая длительная проверка, не выполненный пункт. Короткие functional/load/recovery проверки и мониторинг при выкладке остаются обязательными; полный ночной календарь нельзя считать проверенным по дневному smoke.

## Что сознательно отложено / не является HA

S3/PITR отложены по решению владельца максимум на 30 дней при свежем server-2 backup, проверенном restore и offline recovery key. Риск — RPO около суток и потеря восстановления при утрате обоих узлов. Server 2 не является независимым offsite. PostgreSQL остаётся одним primary, два API не дают HA базы. Telegram и AI gateway также остаются общими точками отказа доставки алертов; независимый второй канал пока не настроен.

Отдельно отложено ожидание двух ночей. Для пользовательского теста скорости готовится узкий, совместимый с текущей схемой пакет summary SQL batches + batch API карточек; он не включает новый worker календарь или расширение canary. Поэтому его выкладка не является подтверждением полного DevOps cutover.
