# AdMirra DevOps — актуальный остаток до полного переключения

Обновлено 23.09.2026 после scoped quality report/placement blacklist. Это **не** утверждение, что весь DevOps-проект готов: ниже три крупных этапа, внутри которых остаётся существенная работа. Полное ТЗ: [admirra_devops_completion_tz_2026-09-11.md](admirra_devops_completion_tz_2026-09-11.md). [Изменения и проверки 21 сентября](devops-progress-2026-09-21.md), [уведомления о качестве лидов 22 сентября](devops-lead-alerts-2026-09-22.md).

## Новый candidate, не production

**Продолжение пунктов 3/4, 23.09:** quality/blacklist endpoints переведены на
owner/project-scoped DB, добавлен bounded durable пересчёт блокировок с TTL и
проверкой lease. Excel без SQL/отсутствующего pandas; PhoneReports — причины,
project labels, error/retry и защита от поздних ответов. Schema head `f46f708192a3`.
Остаются сохранение ранних отказов, immediate exports/validation, legacy diagnostics,
interactive AI/report и billing analytics SQL-over-IO, операторская/визуальная
приёмка. [Контракт, rollout и проверки](devops-lead-placements-2026-09-23.md).

**Продолжение пункта 3, 22.09:** `/lead/stats` переведён с общего файла на owner-scoped
SQL; `/phone-stats/` — один bounded агрегат вместо четырёх запросов, без PENDING
в отклонениях. Quality/blacklist дополнены пакетом 23.09 выше; сохранение ранних
отказов ещё требует правок. [Точный контракт и границы](devops-lead-stats-2026-09-22.md).

**Объединённая проверка, 22.09:** isolated backend manifest — **1281 passed,
1 skipped, 1 deselected**, 6 subtests passed; финальные report guards отдельно —
95 passed, ещё 4 проверки отделения AI receipt от результата доставки — passed.
Проверка не выполняла реальные платежи, LLM или клиентские отправки и не заменяет
sandbox/нагрузочную/визуальную приёмку. Локальные commits: `f81e774`, `14c6131`.

**Продолжение пункта 3, 22.09:** автоматический AI-комментарий теперь использует
готовый snapshot отчёта, освобождает SQL на время LLM/render, сохраняет one-attempt
receipt и не перетирает правки пользователя поздним ответом. Включается с report
freshness guards; production не менялся.
[Контракт и границы](devops-report-comment-2026-09-22.md).

**Продолжение пунктов 2/4, 22.09:** единая account-scoped очередь CP для API,
webhook и maintenance; порядок, non-replayable receipts, сохранение карты до
подтверждения, операторская CLI-сверка и pending/uncertain UI. Schema head
`f35e6f708192`, opt-in `BILLING_PROVIDER_QUEUE=false`.
[Контракт, rollout, проверки и ограничения](devops-billing-order-2026-09-22.md).
Немедленные lead exports/validation, legacy diagnostics и остаток report
SQL-over-IO ещё не закрыты. Отдельная визуальная/operator и sandbox-приёмка
также остаётся; весь пакет 1–4 готовым не объявляем.

**Candidate bounded consumer refresh / UI, 22.09:** реализована ограниченная
догрузка недостающей истории для AI, Sheets и детектора с durable запросами,
deadline, объединением совпадающих consumer jobs, общим бюджетом с report refresh
и проверкой доступа перед fetch/apply. Добавлены waiting/held/ready и явный повтор
подготовки. Новый schema head `f24d5e6f7081`, флаг по умолчанию false.
Пункт 2 (общий финансовый порядок/reconciliation) и остаток legacy SQL-over-IO
пункта 3 **не закрыты**; исправлены отдельные ошибки CP lookup/cancel и email report.
Пункты 5–7 — предпродовые проверки, непосредственно cutover — пункт 8.
[Точный контракт, текущий остаток 1–8 и проверки](devops-consumer-refresh-2026-09-22.md).
Ниже — история предыдущих пакетов, не повторное открытие уже сделанных guard-правок.

**Candidate Sheets / AI / detector, 22.09:** добавлены opt-in проверки покрытия и версии данных для всех трёх consumers: полный Sheets snapshot, detached AI prompt + защита кэша, приостановка detector mutations при неполноте. Live-инструменты ассистента сообщают о неполных/выборочных ответах. Три флага по умолчанию false; production не менялся. До включения остаются bounded refresh для длинной истории/baseline (nightly 7 дней недостаточно), общая нагрузочная/restore-приёмка и cutover. [Контракт, проверки и ограничения](devops-consumer-freshness-2026-09-22.md). Ниже записи предыдущих candidate сохранены как история, а не текущая незавершённость этих guard-правок.

**Candidate direct exports, 22.09:** серверные PDF/PNG/DOCX и создание HTML-ссылки получили opt-in coverage gate и отдельную SQL-фазу до render. Исправлена потеря scope папки при создании ссылки; frontend понимает JSON-ошибки скачивания в Blob. Это не новый async renderer и не перевод Sheets/AI/detектора. [Реализация, проверки и точные границы](devops-direct-export-freshness-2026-09-22.md).

**Candidate report freshness, 22.09:** требования, deadline, revisions и bounded poll `reports.resume` подключены к подготовке ReportDelivery за opt-in флагом. Снимок фиксируется до PDF, renderer не держит SQL; ручная/повторная отправка защищена от гонки с фоновым resume. Candidate schema `f13c4d5e6f70`. Добавлены UI waiting/held/безопасный reset и bounded refresh producer через history queue; 156 backend + 4 frontend tests passed. Другие consumers, общий regression/restore/load и cutover ещё предстоят. [Политика и rollout gates](devops-report-freshness-2026-09-22.md), [refresh и UI, проверки и ограничения](devops-report-refresh-2026-09-22.md).

**Candidate coverage, 22.09:** добавлена сохраняемая подтверждённая полнота date/stage/settings для durable sync и fail-closed reader. Старый SUCCESS/last_sync_at не считается покрытием; missing goals не подтверждают полноту. Это основа, а не включённый freshness barrier: report requirements/wait deadline, per-stage outcomes и consumers отчётов/AI/детектора ещё предстоят. Миграция candidate head `f02b3c4d5e6f`; production этим этапом не меняется. [Контракт и ограничения](devops-sync-coverage-2026-09-22.md).

**Candidate sync, 22.09:** fetch/apply без SQL во время HTTP реализован также для durable manual/night/history Директа, VK и Авито, с атомарной записью, повторной проверкой settings/lease и guarded OAuth renewal. В production не включён. Общий SYNC остаётся открыт: durable per-stage coverage/freshness, UI follow-up, live vendor quota/format acceptance и mixed-load не закрыты. [Реализация и границы](devops-ads-sync-2026-09-22.md). Следующие исторические пункты о непереведённых рекламных каналах относятся к состоянию до этого candidate.

## Уже в production

Примечание 22.09: поверх перечисленных ниже исторических DevOps/performance releases отдельно выложены signup-discount/ecommerce и компактная плашка. Их актуальные образы и additive schema описаны в [журнале релиза](signup-discount-ecommerce-release.md); исторические digests ниже не следует принимать за текущие rollback images. Общая DevOps migration chain и новые consumers этим релизом не включались.

- API-2 / Redis / приватная сеть / exporters / ingress guard; 10% canary только четырёх разрешённых GET/HEAD routes. Dashboard, mutations и SSE на две реплики пока не переключены.
- AI gateway и отдельный AI hotfix `0e5f031`: quota ledger / request idempotency сохранены. Поверх них 21.09.2026 выложен узкий пакет ускорения сводок: backend `4ca866eb…`, automation прежний `33b4ca03…`; затем frontend обновлён до `274aad1d…` (`c39e7e2`): KPI не ждут подробные таблицы, устаревшие read-ответы блокируются. Полные digests в `ops/rollback_images.json`. Runtime не равен git checkout `/root/Admirra`, нельзя деплоить blanket pull/build/up. [Серверные замеры](devops-summary-performance-2026-09-21.md), [frontend: причина задержки, проверки, rollback и ограничения](dashboard-read-lifecycle-2026-09-21.md). Браузерная приёмка владельцем ожидается.
- Central Prometheus: 7 targets / 23 rules. Alertmanager и внешний public heartbeat настроены для группы AdMirra Alerts. Сетевая доставка из API-1 идёт через закрытый WireGuard gateway, внешний heartbeat — напрямую. [Проверки и ограничения](devops-telegram-alerts-2026-09-20.md). Подтверждение фактического получения человеком тестовых пар пока ожидается, gate автоматически не отмечен.
- На API-2 root LVM/ext4 расширен из уже выделенного свободного места: 18,47 → 34,47 GiB, свободно около 19 GiB вместо 3,5 GiB; запас VG 2,47 GiB. Без удаления данных/перезагрузки; services healthy. Metadata backup `/etc/lvm/backup/ubuntu-vg.before-telegram-20260920`.
- Encrypted daily backup на server 2; backup `20260922T044425Z-8fcea122` повторно восстановлен в изоляции до будущего schema head `de0f1a2b3c4d` candidate `3d65ef3` (50 s, workers/application/read smoke passed). [Evidence и границы](devops-ads-sync-2026-09-22.md).
- В production schema остаётся `cc3d4e5f6a7b` плюс additive assistant ledger; новая общая миграционная цепочка/worker consumers **не включены**.
- API-2 получил собственный WireGuard peer `10.78.0.2/32` к AI gateway: private health и каталог OpenRouter проверены из его реального backend-контейнера. API-1 peer, default routes и БД/Redis-сеть сохранены. Это сеть, не полный AI/SSE rollout на API-2.

## 1. Завершить безопасную логику фоновых процессов

- Полный sync/history: убрать долгие SQL-транзакции во время внешнего HTTP, завершить settings/coverage guards по каналам. Follow-up и объединение диапазонов реализованы в candidate `7f87205`; видимая UI-связь и полный failure matrix остаются. Ошибка выбранных целей Метрики теперь не даёт ложный SUCCESS в Direct/Avito candidate `e080b13`. Standalone Метрика тоже собирает и проверяет всё окно до замены старых данных (`7e49990`, `dbb3e96`), повреждённый ответ не превращается в нули. Goals-only / detector paths и эти правки не закрывают весь sync.
- В candidate `c27876e` + `ac01ed8` queued goals/history привязаны к owner/project и authoritative lease/payload; goals snapshot не принимает нового владельца при гонке подготовки. Worker startup блокируется при старых незавершённых jobs без binding: нужна явная сверка, не автоматическая перепривязка. Это входная защита очереди, **не** закрытие in-flight owner/settings races и долгих транзакций полного legacy history sync. [Изменения и проверки](devops-integration-scope-2026-09-21.md).
- В candidate `cb3be39` **история standalone Метрики** переведена на snapshot → HTTP без SQL → guarded apply, с защитой от смены owner/project/settings и сохранением текущего sync watermark. [Проверки истории](devops-metrika-history-2026-09-21.md). В `a09cf4d` + `3cd3a45` на короткие транзакции переведены также durable manual/night задачи standalone Метрики: атомарные данные/SUCCESS, retry/timeout, follow-up, detector/LLM isolation и полный первый диапазон >90 дней. Legacy consumers и остальные каналы пока не переведены; общий SYNC-пункт остаётся открытым. [Границы и проверки нового обработчика](devops-metrika-sync-2026-09-21.md).
- `nightly.enqueue` и `reports.rules` разбиты на bounded tenant-scoped children в candidate `3e5ddae`, не production. Parent success означает планирование, не успех всех children.
- `reports.export` теперь scoped per-project в candidate `11f935d`, Sheets IO вынесен из SQL. В `b71ec3c` scoped Sheets snapshot читает scalar-строки порциями по 128, имеет общий лимит 50 000 строк / 8 MiB сериализованных данных и отказывает до внешней записи, не обрезая историю. Превышение лимита — failed, не ложный success и не неопределённая доставка. Остались экспорт историй сверх лимита (bounded spool/chunks), freshness barrier, единый snapshot/render/send contract и ограничения legacy interactive export. [Проверки и границы](devops-sheets-bounds-2026-09-21.md).
- Billing maintenance разбит на warning/recurring children по подпискам (`286b58b`); scoped warning освобождает SQL до SMTP и проверяет период/lease при подтверждении (`6d41b24`, `11d9e40`). Scoped recurring теперь тоже освобождает SQL перед CloudPayments, перепроверяет снимок подписки и подтверждает результат отдельной fenced-транзакцией (`5f192f2`, candidate). Изменение тарифа/слотов/отмена в полёте не очищает флаг согласования и даёт `uncertain`, блокирующий повтор. **Осталось:** общий порядок внешних операций interactive API + worker, durable operation intent/provider-state reconciliation. Обнаружение конфликта после HTTP не предотвращает саму внешнюю гонку отмены с update; BILL-01 целиком не закрыт. [Проверки пакета](devops-recurring-2026-09-21.md).
- VK maintenance ограничен SQL batches по 100 drafts с безопасным продолжением (`9eb6015`). В candidate `5a11114` + `f1bfefa` периодические lead quality notifications переведены на DB-backed агрегаты, bounded project/recipient children и fenced dispatch receipts: неизвестный результат Telegram не повторяется автоматически, HTTP не держит SQL. Миграция candidate head теперь `de0f1a2b3c4d`; production не менялся. Полный manifest: **1036 passed**. Остались немедленные lead exports, legacy analytics/placement-blacklist scopes и общая операторская сверка; весь модуль телефонии этим не объявляется готовым. [Контракт и проверки](devops-lead-alerts-2026-09-22.md). AI prewarm пока выключен.
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

Отдельно отложено ожидание двух ночей. Для пользовательского теста скорости **выложен** узкий, совместимый с текущей схемой пакет summary SQL batches + batch API карточек и frontend read lifecycle. Live summary smoke: 64 проекта × 4 канала за 730,96 мс, 12 сравнений совпали, доступ защищён; это не время отображения всей страницы. Он не включает новый worker календарь или расширение canary. Поэтому его выкладка не является подтверждением полного DevOps cutover. Свежий post-frontend backup `20260920T231749Z-450ebc7e`; предрелизный backup summary-релиза восстановлен и проверен на текущей схеме без миграций. Подробные campaign/goal запросы остаются отдельным направлением оптимизации.
