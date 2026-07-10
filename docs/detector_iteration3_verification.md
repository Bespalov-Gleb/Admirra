# Детектор — итерация 3: карта реализации и проверки

| Требование ТЗ | Реализация | Проверка |
|---|---|---|
| Исторический режим не создаёт сигналы | `detector_iteration3.py`; миграция закрывает `baseline`/старые plan-алерты, baseline рассчитывается в фоне | миграция + код-ревью |
| P-1: темп расхода, пауза, прогноз, раннее исчерпание | `_make_plan_spend` | `test_p1_*` |
| P-2: 7-дневный CPL, 1.3×/1.8×, денежный фильтр и лимит бюджета | `_make_plan_cpl` | `test_p2_*` |
| P-3: автоматический/ручной план заявок, только отставание | `_make_plan_leads`, `manual_leads` | `test_p3_*` |
| Один P-алерт на канал, P-2 → P-1 → P-3 | `_collapse_plan_checks`, стабилизированный ключ `plan` | `test_plan_checks_*` |
| C-0/C-1/C-2/C-3 | `_make_balance_alert`, `_make_stopped_alert`, `_make_tracking_alerts`, `sync_issues_for_client` | C-0/C-3 unit-кейс, C-1/C-2 проверяются условиями в коде и на стенде |
| Объём до создания сигнала | конфиг `DETECTOR_*`, проверки в каждом P/C-методе | unit-кейсы P-1/P-2/P-3 |
| Кампании: только дорогая заявка, не alert | `campaign_highlights` API и таблица дашборда | фронтенд-сборка |
| План версионный и пересчёт сразу | append-only endpoints, `_recalculate_detector_now` | настройки + API |
| Онбординг без плана | `PlanOnboardingBanner`, dismiss на 30 дней, CTA в настройки | фронтенд-сборка |
| Детектор скрыт от клиентов | agency-only guard на всех detector API, отчёты не получают данные | API-code review |
| Автоотчёт блокируют только красные P/C | `_rule_blocking_anomaly` | code review |

Выполненные команды перед коммитом:

```bash
DATABASE_URL=... pytest -q tests/test_detector_iteration3.py
npm run build
alembic heads
python -m compileall core backend_api automation tests alembic/versions
git diff --check
```
