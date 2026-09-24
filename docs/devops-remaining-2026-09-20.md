# AdMirra DevOps — актуальный остаток до полного переключения

**24.09, production cutover:** новая схема `f68b92a3b4c5`, API1/API2,
frontend, consumers и единственный scheduler уже активны. Legacy automation
остановлен. Manual sync Яндекс/VK, AI cross-replica replay и отчёт тестовому
владельцу прошли. Осталось завершить ступени публичной балансировки 10→25→50%
с выдержкой и финальным контролем. S3 и две ночи остаются отложенными.
[Актуальный протокол и rollback](devops-production-cutover-2026-09-24.md).
Исторические статусы ниже не отменяют эти результаты.

**24.09 утром:** [новый mail candidate и фактические role configs](devops-launch-preparation-2026-09-24.md).
Коды/ссылки доступа переведены на приоритетный Unisender Web API; тестовое письмо
доставлено. Candidate `2ce9513` на обоих хостах, подготовлены root-only configs,
DB/Redis/files probes пройдены. Исправлен локальный путь API1→DB до activation.
Свежий backup/restore и 64/64 read load passed. Полная регрессия нового image:
**1639 passed**, 1 skipped, 1 deselected, 6 subtests passed. Production по-прежнему legacy; подтверждение отдельного
хранения ключа и фактический управляемый cutover остаются.

**24.09, финальная приёмка:** [межсерверные 600 reads + recovery, новый restore и worker AI env](devops-final-load-2026-09-24.md).
Два synthetic прогона и 44 recovery/contract теста прошли. Финальный application
image `24f58b7`: **1623 tests passed**, реальный scoped VK/Direct/Metrica + AI/PDF
probe прошёл. Restore с полным launch profile и API-only degraded rollback
проверены; ключевые ограничения описаны в отчёте. Сам cutover **не выполнен**:
ждём подтверждения отдельного хранения recovery key, затем свежий preflight,
render role configs, admission/drain, migrations и наблюдаемый rollout.

Обновлено 24.09.2026: [окружение воркеров и общие файлы подготовлены и проверены](devops-worker-files-2026-09-24.md).
Ближайшие этапы — общая межсерверная нагрузочная/recovery приёмка, затем управляемое переключение.
Ниже сохранена история этапов; старые утверждения «worker.env/storage отсутствуют» заменены новым отчётом.
Полное ТЗ: [admirra_devops_completion_tz_2026-09-11.md](admirra_devops_completion_tz_2026-09-11.md).

**24.09, точечный production hotfix:** [детектор → AI, OpenRouter-комментарии и документы](ai-detector-legal-fixes-2026-09-24.md)
выложены поверх legacy runtime, без DevOps cutover/миграций. Актуальные rollback
images обновлены в `ops/rollback_images.json`; старый candidate `a5635d5` перед
финальной нагрузкой нужно пересобрать с этими правками. Все утверждения ниже о
неизменённых production image IDs относятся к моменту соответствующей проверки.

## Новый candidate, не production

**Предрелизная инвентаризация 23.09:** [фактический runtime и обязательный остаток](devops-production-preflight-2026-09-23.md).
24.09 worker env/roles/mounts подготовлены, private artifact service и legacy
shared-file bridge установлены. Production workers ещё не запущены, финальная
multi-host/mixed-load приёмка не выполнена. Сохранён актуальный rollback baseline со скидочным релизом,
создан свежий backup `20260923T202713Z-ebc64797`, его restore — 65 s, migration/
API/workers boot и 64/64 HTTP passed; полный immutable-image regression —
**1606 passed**. Admission
open, production schema/API/automation не переключались.

**Продолжение 23.09 — раскрытие групп/объявлений VK:** `a5635d5`, detached collection и
shared guarded apply; ошибка API больше не считается успешной пустой
статистикой, unknown token context отклоняется. Catalog scope/pagination,
смена доступа/настроек, параллельный sync и отмена покрываются isolated тестами.
[Контракт и приёмка](devops-vk-hierarchy-2026-09-23.md). Чистый image:
**272 targeted tests passed**, restore 65 s до `f68b92a3b4c5`, API/workers boot,
**64/64 HTTP 200**; полный manifest не повторялся. Production не изменён. Historical
coverage/watermark и оставшиеся live paths остаются отдельными задачами.

**Продолжение 23.09 — раскрытие кампаний Direct:** `9e54bb8`. Отчёты и каталоги групп/
объявлений собираются без занятой SQL-сессии, затем сохраняются коротко и с
проверкой доступа, настроек и intervening sync. Каталожные нули не стирают
метрики, late/partial results не применяются. [Контракт и приёмка](devops-direct-hierarchy-2026-09-23.md).
Чистый image: **225 targeted tests passed**, restore 66 s до `f68b92a3b4c5`,
API/workers boot и **64/64 HTTP 200** прошли; полный manifest не повторялся.
VK hierarchy/остальные live paths и полнота исторического ad coverage ещё
остаются; этот этап не означает полного закрытия hierarchy или production.

**Продолжение 23.09 — live attribution таблиц/динамики:** `f460f81`, сборка
`e7aaafb` (нормализованы read/traverse права исходников в image). Три общих builder-а
Яндекс/Авито освобождают SQL на время Метрики; проверяют актуальность настроек
и доступа перед возвратом. Регрессия обнаружила и исправила дополнительный
случай 34→65 в фильтрованной таблице и смешение одинаковых goal IDs между
Яндексом/Авито. [Контракт и приёмка](devops-attribution-io-2026-09-23.md).
Чистый image: **211 targeted tests passed**, restore 67 s до `f68b92a3b4c5`,
API/workers boot и **64/64 HTTP read smoke** прошли; полный manifest не повторялся.
Это частичное закрытие live dashboard IO: lazy hierarchy, audience/top ads
и остальные legacy paths требуют отдельной работы. Production не переключён.

**Продолжение 23.09 — интерактивный ассистент без SQL во время IO:** `b8bda45`.
История/вложения и credentials отделены от ORM-сессии, UUID сообщений берётся
до commit, SQL освобождается перед LLM/tools/SSE. Доступ перечитывается между
этапами, поздняя OAuth-запись проверяет актуальность integration. Отмена явно
закрывает agent/LLM/wire. Реальные PostgreSQL-тесты с одним слотом проверяют
освобождение соединения, chat ledger/replay, отмену и смену доступа.
[Контракт, приёмка и ограничения](devops-assistant-io-2026-09-23.md).
Чистый image: **134 целевых tests passed**, restore до `f68b92a3b4c5`,
API/четыре группы workers boot и **64/64 read smoke** прошли. Полный manifest
нового image не повторялся; 1481 ниже относится к предыдущему `5e788f9`.
Это закрывает проверенные interactive assistant paths, **не** весь пункт
SQL-over-IO: live dashboard attribution/dynamics и другие legacy paths ещё
остаются. Полное двухузловое переключение и production этим пакетом не выполнены.

**Продолжение 23.09 — компактные списки и два HTTP API:** `d254266` / `5e788f9`.
Аудит list consumers завершён: frontend запрашивает `include_campaigns=false`,
сохраняя полный старый API по умолчанию. Все project/integration metadata и
числа остаются прежними; кампании получают отдельные picker/table запросы.
Новый двухпроцессный тест с JWT: 120 чтений, 12 sync apply, 12 report receipts
и 4 ожидаемых отказа чужого доступа прошли на чистом image. Это два процесса
в изолированном контейнере, **не** multi-host/cache/SSE/Celery end-to-end.
Frontend: 49 tests и сборка чистых исходников прошли. Подробности и результаты
окончательной приёмки: [компактные списки](devops-compact-project-lists-2026-09-23.md).
Финальный image `5e788f9`: **1481 passed**, отдельно HTTP two-API — passed;
два restore до `f68b92a3b4c5` и оба read smoke **64/64** прошли. JSON списка
1 007 596 → 107 784 bytes (**−89,3%**) при совпадении всех оставшихся полей.
Короткие latency samples не подтверждают общее ускорение всех маршрутов/SLO.
Production не переключён. Пункт ниже о необходимости самого аудита compact
контракта закрыт этим пакетом; более широкие load/cutover gates остаются.

**Нагрузочная проверка 23.09 — согласованность чтения:** смешанный тест обнаружил
разрыв между отдельными SELECT расхода и лидов при параллельном sync. В `ed31916`
SQL-only сводки/карточки/списки переведены на единый read-only snapshot; N+1 при
сериализации проектов заменён пакетной загрузкой. Добавлены deterministic race
и mixed regression. [Сценарий, границы и evidence](devops-mixed-read-2026-09-23.md).
Production не переключён; это не полная двухрепличная/real-provider приёмка.
Чистые образы: исходный `2db26eb` — 1458 passed; исправленный `ed31916` —
96 целевых passed (не полный повтор manifest). Оба восстановлены до `f68b92a3b4c5`,
API/worker boot и 64/64 read requests прошли. Mixed synthetic: 120 чтений,
12 sync и 12 report receipts без разрыва cost/leads. В list payload обнаружены
2250 вложенных кампаний (~900 KB), общий response ~1 MB: нужен аудит компактного
контракта и повторная нагрузка. Лёгкие маршруты не показали общего ускорения;
SLO/capacity пока не приняты. Новые результаты не отменяют оставшиеся этапы ниже.

**Продолжение 23.09 — legacy intake и операторская сверка:** старые URL теперь
поддерживают явный signed project scope в guarded режиме; добавлены auditable
close/confirm без resend, terminal closed и честные pending/held/closed подписи.
Новый schema head `f68b92a3b4c5`. Read-only production inventory: **0 phone projects,
0 leads**, при этом **94 рекламных проекта** — другой модуль. Предварительный
синтетический load 2/8 threads прошёл без потерь/дублей; это **не** общий
dashboard/mixed-load. [Контракт, операторская процедура и замеры](devops-lead-reconciliation-2026-09-23.md).
Старые пункты про отсутствие project adapters/CLI ниже заменены этим пакетом.
Регрессия: 260 passed; после последней защиты отката — 70 passed в целевом
перекрывающемся наборе. Frontend: 2 unit tests и production build прошли.
Это локальный candidate, не deployment; общая нагрузка/restore/cutover остаются.

**Продолжение 23.09 — проектный lead intake/exports:** добавлен opt-in
`LEAD_DELIVERY_GUARDS` с предварительным сохранением заявки, project-scoped
idempotency/dedup, detached validation/enrichment и атомарной очередью отправок.
Для каждой отправки — fenced receipt, без blind retry после неизвестного
результата. Schema head `f57a8192a3b4`. Production не менялся. **Остаются**
legacy unbound endpoints, operator reconciliation/UI,
sandbox/mixed-load и общий cutover. [Контракт и точные границы](devops-lead-intake-2026-09-23.md).
**Уточнение владельца 23.09:** Bitrix в продукте не используется. Разработка
проектной интеграции Bitrix исключена из release scope; наличие legacy-кода
не является требованием реализовать эту интеграцию. Остаточные настройки
проверить при инвентаризации, без подключения CRM и удаления данных.
Изолированная regression этого пакета: **228 passed, 29 warnings, 132.41s**;
реальных provider sends/платежей не выполнялось.

**Продолжение 23.09 — диагностика Lead Validator:** общие probes закрыты internal
superadmin access, token preview/raw errors убраны, test-validate стал dry-run
без глобальной CRM/Telegram/dedup. Auth/scope SQL освобождается до HTTP; общий
Redis limiter защищает обе реплики, при недоступности — fail-closed 503.
[Контракт и проверки](devops-lead-diagnostics-2026-09-23.md). Реальный приём/
early rejects/exports и остальные пункты ниже ещё не завершены.

### Уточнённое решение владельца 23.09: модуль проверки заявок остаётся

Отмена предыдущего решения об отсрочке: Lead Validator (формы сайтов, антиспам,
quality/blacklist, CRM/email/TG экспорты) остаётся в релизе. Модуль не выключать.
Закрыть ранние `_reject`, обогащение, exports и diagnostics, затем общую регрессию,
mixed-load/recovery, проверку миграций/отката и только после приёмки — cutover.

Это **не** бот новых регистраций AdMirra, не телефоны OAuth-профилей и не
лиды/конверсии рекламной аналитики. Эти действующие функции остаются в релизе.

В коде старый модуль существует: `backend_api/main.py` подключает phone routers,
lead/webhook routers и legacy lead jobs; durable calendar также планирует `lead.*`.
Поэтому отсутствие пункта в интерфейсе не означает отключения. Перед релизом
проверить queued/running/uncertain `lead.*` и безопасный drain без удаления evidence
и слепых повторов. Существующие проекты/данные не удалять.
Общий объект `lead_scheduler` содержит также отчёты и VK maintenance — его нельзя
целиком отключать по имени. Регистрационные уведомления не затрагивать.

Production/env этим уточнением **не изменены**. Оставшиеся lead exports/validation
снова входят в обязательный объём. В активном плане также AI/report/billing
внешние вызовы, операторская приёмка,
проверки двух серверов, финального артефакта/миграций/restore/load и cutover.

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
- Получение всех четырёх Telegram уведомлений обоих путей **подтверждено владельцем**. Ответственный за реакцию остаётся организационным пунктом; повторять тест ради HTTP success не нужно.
- Подтвердить offline-копию recovery key. Новые notifications/SQL success не заменяют эту проверку.

## 3. Контролируемое переключение и наблюдение

- Окно с ответственным, вне 03:00/05:00 МСК. Перед ним новый backup, актуальные schema/artifact/restore и cutover preflight; старые evidence не подставлять как свежие.
- Admission gate → drain legacy jobs/scheduler → migrations → candidate API-1 и минимальные workers с единственным scheduler → разрешённая end-to-end задача → открыть admission. Billing/lead webhooks не глушить общим запретом.
- Только после корректного single-API режима обновить API-2 на тот же digest/schema, расширять canary ступенями. Не запускать старый и новый глобальные scheduler одновременно.
- Две последовательные ночи наблюдения **отложены владельцем 21.09.2026**. Это непроведённая длительная проверка, не выполненный пункт. Короткие functional/load/recovery проверки и мониторинг при выкладке остаются обязательными; полный ночной календарь нельзя считать проверенным по дневному smoke.

## Что сознательно отложено / не является HA

S3/PITR отложены по решению владельца максимум на 30 дней при свежем server-2 backup, проверенном restore и offline recovery key. Риск — RPO около суток и потеря восстановления при утрате обоих узлов. Server 2 не является независимым offsite. PostgreSQL остаётся одним primary, два API не дают HA базы. Telegram и AI gateway также остаются общими точками отказа доставки алертов; независимый второй канал пока не настроен.

Отдельно отложено ожидание двух ночей. Для пользовательского теста скорости **выложен** узкий, совместимый с текущей схемой пакет summary SQL batches + batch API карточек и frontend read lifecycle. Live summary smoke: 64 проекта × 4 канала за 730,96 мс, 12 сравнений совпали, доступ защищён; это не время отображения всей страницы. Он не включает новый worker календарь или расширение canary. Поэтому его выкладка не является подтверждением полного DevOps cutover. Свежий post-frontend backup `20260920T231749Z-450ebc7e`; предрелизный backup summary-релиза восстановлен и проверен на текущей схеме без миграций. Подробные campaign/goal запросы остаются отдельным направлением оптимизации.
