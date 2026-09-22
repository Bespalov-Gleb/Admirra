# Проверка актуальности перед подготовкой ReportDelivery

Статус: **candidate, production не менялся**. Продолжение sync coverage `b3b0dfa`, часть REPORT-02. Это не завершение всего REPORT/DevOps.

## Что реализовано

- Nullable `report_deliveries.data_readiness`, миграция `f13c4d5e6f70` после `f02b3c4d5e6f`. Хранятся integrations/client/owner, стадии, настройки, диапазон, фиксированный порог свежести, deadline, revision, причины нехватки.
- `REPORT_FRESHNESS_GUARDS=false` по умолчанию. Включение требует `DURABLE_TASKS=true` и `REPORT_DELIVERY_GUARDS=true`; несовместимая конфигурация отклоняется при старте. Миграция обязательна до выкладки ORM с новым столбцом **даже при выключенном флаге**.
- Проверяются все каналы, поскольку ReportDelivery сохраняет четыре переключаемых шаблона. Обязательные данные: campaigns рекламных каналов и metrika_goals выбранных целей/статистических счётчиков. Login-level OAuth-ссылки Метрики не считаются счётчиками. Optional balance/strategies не получают фиктивного watermark.
- Проверяется текущий и предыдущий равный период: сравнительные KPI не строятся на непроверенной базе. Экспериментальная шестимесячная dynamics-секция по-прежнему выключена в delivery builder.
- Политика candidate: `REPORT_DATA_MAX_AGE_MINUTES=1440`, `REPORT_DATA_WAIT_MINUTES=30`; ограниченные диапазоны настроек 1–1440 и 1–120 минут. Порог и срок фиксируются при первом ожидании, не сдвигаются при повторной проверке/смене целей.
- При отсутствии данных — сохранённый `waiting`, тот же delivery, одна следующая проверка в ближайшую минуту через transactional outbox. Нет sleep, занятого renderer или SQL connection в период ожидания. По deadline — `held`, дальнейшие проверки не создаются.
- `reports.resume` использует существующую очередь `reports`, проверяет execution lease, payload, tenant и resource. Kind **non-replayable**, поскольку при готовности может отправить отчёт. Unknown send/worker loss не вызывает слепой повтор: остаётся действующий route ledger и операторская сверка. Новых очередей/Celery result backend нет.
- Ручное создание/тест расписания не получает разрешения на автоотправку через ожидание. После готовности ручной preview остаётся на согласовании. Автоматическое правило сохраняет approval/anomaly guards, повторно проверяет настройки и активность пользователя после render. Начальная автоотправка и resume используют CAS `pending → sending`, чтобы не повторить ручную отправку, прошедшую во время render.
- Смена целей/кабинета до фиксации снимка пересобирает требования с новой revision, без продления deadline. Изменённое/выключенное правило удерживается для проверки, а не неожиданно отправляет новый набор получателей.
- Data capture фиксирует доступные client IDs, держит client/integration locks только на SQL-фазе и проверяет доступный scope повторно перед фиксацией. PDF/PNG строятся по detached ORM-объекту после commit; даже lazy load при `expire_on_commit` не открывает SQL внутри render. Сбой render сохраняет неизменяемые JSON-данные для повторной генерации.
- Готовый подтверждённый снимок не перечитывает статистику при повторе получателя или переключении шаблона; `coverage_revision` сохраняется во всех вариантах. Старый snapshot без подтверждения при включённом флаге удерживается, а не автоматически считается проверенным.
- API отдаёт безопасное `data_readiness` (`status`, `reason`, `deadline`, `revision`, `checked_at`), без внутренних source/owner/settings. Approve/test при неготовности возвращают 409; preview сохраняется как pending. Неполные данные не заменяются нулями.

## Проверки

Изолированные синтетические PostgreSQL/Redis на server 2, internal Docker network, `WW_TEST=1`. Никаких production credentials, внешних отправок, AI или платежей. Источник — Git `b3b0dfa` + точечный patch; runtime dependencies из `admirra-devops:3d65ef3`. Это не immutable release image и не финальный общий manifest.

Окончательный прогон: **144 passed, 26 warnings, 75,67 s** (`test_report_freshness`, `test_calendar_work`, `test_reports_final`, `test_report_route_guards`, `test_report_artifacts`, `test_sync_coverage`, `test_durable_work`, `test_runtime_roles`). Тесты включают отсутствие comparative window, второй канал без coverage, scope/owner/pause, смену целей, terminal deadline, queue dedupe, manual/approval/auto, повтор handler, подмену payload, immutable retry, render без SQL, переключение шаблона, ручную отправку и включение approval во время render, HTTP 409 и additive migration. В первом прогоне был 1 packaging failure: статический тест требовал не включённый в backend-пакет `Reports.vue`; файл из Git добавлен в QA-пакет, в окончательном прогоне тест не исключался. `git diff --check` и compile проверка прошли.

## Остаток и условия включения

Дополнение следующего candidate: bounded producer и UI waiting/held/deadline retry из пунктов 2–3 реализованы; детали и ограничения в [refresh и UI](devops-report-refresh-2026-09-22.md). Ниже сохранены исходные rollout-требования; общий REPORT/DevOps и включение в production ещё не закрыты.

1. Новый флаг **не включать**, пока legacy writers не выключены и необходимые даты не получили durable coverage. Статус SUCCESS/наличие фактов не заменяют подтверждение.
2. Этот этап ждёт существующую manual/night/history синхронизацию, **не запускает автоматически массовое обновление всех кабинетов**. Нужен bounded producer refresh для отсутствующих диапазонов с tenant/provider budget; особенно для длинных сравнительных периодов, которые не входят в обычный nightly lookback. Без него долгий диапазон безопасно останется held, а не уйдёт с нулями.
3. Добавить в UI явные waiting/held, причины и управляемую повторную подготовку после deadline; сейчас сохранён совместимый business status `pending` и добавлено поле API. Terminal held не сбрасывается обычным approve. До включения нужно также решить fate старых неподтверждённых pending snapshots — без переотправки уже отправленных.
4. Direct exports/Sheets, AI и детектор пока не переведены на этот barrier. Полное разделение render/send, resource/deadline limits и устранение остальных длинных транзакций в старом send/AI пути остаются открыты.
5. Перед rollout: полный regression/restore окончательного артефакта, миграции, drained jobs, согласованный набор consumers с новым kind, mixed-load и разрешённый end-to-end отчёт. При rollback не оставлять `reports.resume` старому worker: drain/hold/reconcile; отключение флага не даёт legacy sender права переотправлять неизвестные исходы.

S3 и две ночи наблюдения остаются отложенными владельцем. Включение production-флагов, restart/migrations и расширение canary этим этапом не выполнялись.
