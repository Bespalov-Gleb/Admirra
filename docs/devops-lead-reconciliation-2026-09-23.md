# Legacy endpoints, operator resolution и предварительная нагрузка

Candidate 23.09.2026. Production code/env/схема не менялись. Реальные письма,
CRM, Telegram и Метрика при тестировании не вызывались.

## Read-only инвентаризация production

Через SQL connection работающего `admirra-backend-1` подтверждено:

- phone_projects: **0**;
- leads: **0**;
- рекламных clients: **94** — это другой, действующий модуль.

Дополнительный read-only запрос к production Postgres: активных/подписанных
phone projects и проектов с enable_bitrix_check — также 0. В последних 20 000
строках логов backend не найдено POST к lead/tilda/marquiz/phone endpoints.
Это ограниченная выборка, **не** доказательство отсутствия запросов за всю
историю (контейнеры/логи могли ротироваться). Переносить существующие записи
проектных подключений в этой БД не требуется. Модуль не выключен.

## Старые URL сохранены

При `LEAD_DELIVERY_GUARDS=true` `/api/lead/`, `/api/webhook/tilda/`,
`/api/webhook/marquiz/` используют project intake, а не глобальные credentials.
Нужно указать `?project_id=<UUID>` и `X-Webhook-Secret` проекта. Для провайдеров,
умеющих передать только URL, поддержан существующий параметр `secret`; URL с
секретом нельзя публиковать, при его использовании нужно исключить query из
access logs. Предпочтителен заголовок. `Idempotency-Key` передаётся в ledger.

Нет project_id — 422; неверный секрет — 401; нет настроенного секрета — 503.
CAPTCHA/SQL scope/dedup/очередь те же, что у `/api/webhook/phone/{UUID}`.
Авторизация отпускает SQL до provider IO. Смена настроек после авторизации
проверяется повторно. Server-to-server формы сохраняют пропуск browser-антибот
полей; `/lead/` сохраняет проверки формы. При выключенном guard старое поведение
совместимо; rollout должен обновлять все API/workers согласованно.

## Операторская сверка без повторных отправок

Новый additive schema head: **f68b92a3b4c5**, parent f57a8192a3b4. Добавлен
`lead_operation_resolutions` и terminal `closed` в intake/receipt. Down migration
не удаляет audit/evidence. Preflight требует новую таблицу при включённом guard.
После первого сохранённого intake нельзя выключать guard даже после завершения
всех задач: legacy path обошёл бы idempotency при повторе старого запроса.
Откат — только на совместимый release с сохранением guarded admission/ledger,
не через выключение флага или удаление истории.

CLI запускается оператором с DB-доступом, не публичным HTTP endpoint. По умолчанию
только читает; owner UUID обязателен, вывод не содержит контактов/токенов/тела.

```sh
python -m ops.lead_status --owner-id <OWNER_UUID>
python -m ops.reconcile_leads intake <INTAKE_UUID> --owner-id <OWNER_UUID>
python -m ops.reconcile_leads export <JOB_UUID> --owner-id <OWNER_UUID>
```

После проверки истории операции можно передать `--decision`, `--version`
из свежего inspect, `--actor`, `--reason` (10–1000 символов) и `--evidence-ref`
(10–255 символов). В audit указывать ссылку/номер служебного разбирательства,
не API ключи, контакты клиента или тело запроса.

Решения:

- `close_unverified` для intake: только после deadline и пока Lead.PENDING.
  Закрывает intake, сохраняет идемпотентный ответ `validation_closed_unverified`.
  Не делает контакт спамом/отказом, не создаёт отправок. Поздний результат
  прежней валидации больше не сможет примениться.
- `confirm_delivered` для export: только остановленные failed/uncertain jobs
  без lease. При неопределённом receipt нужны подтверждение от провайдера для
  **всех** получателей и неизменные scope/body. Флаг доставки/receipt/job/audit
  обновляются атомарно. При уже подтверждённом receipt восстанавливается только
  потерянное подтверждение job; внешняя отправка не повторяется.
- `close_without_resend`: завершает разбор без повторной отправки и без ложного
  exported flag. Не позволяет понизить уже подтверждённый receipt до closed.

Нельзя сверять живой worker, использовать устаревший version, чужого owner,
подменить получателя/тело или дважды выполнить resolution. CLI не делает
provider calls и не переводит job в queued. Отсутствие записи в логах не является
доказательством отсутствия доставки. Timeout/partial SMTP acceptance — ручная
сверка, а не permission на resend. Audit не удаляется вместе с job/lead.

## Состояния в API и интерфейсе

Список/детали лидов возвращают status + validation_state. Истёкшая processing
заявка отображается как held без фоновой мутации. В таблице: «Проверяется»,
«Требует сверки», «Закрыта без проверки». PENDING не попадает в фильтр
«Отклонены». Приём/отказ определяется итоговым status, а не устаревшим is_valid.
Изменены подписи/бейджи, не раскладка страницы. Browser visual acceptance
в этом прогоне не выполнена; unit tests и Vite build выполнены отдельно.

## Предварительная нагрузка (не dashboard/mixed-load)

Команда в `ops/compose.isolated.yml`: tests `-s tests/test_lead_load_smoke.py`.
Синтетические данные, настоящая изолированная PostgreSQL, 4 владельца/проекта,
100 новых заявок + 100 повторов + 100 dispatch, fake provider latency 25 ms.
Варианты 2 и 8 параллельных threads. Ограничения контейнера тестов: 2 CPU/1 GiB;
PostgreSQL: 1 CPU/768 MiB. Никаких HTTP-клиентов пользователей/реальных providers.

| Метрика | 2 потока | 8 потоков |
|---|---:|---:|
| 100 приёмов + 100 повторов, секунды | 3,020 | 1,813 |
| p95 приёма, мс | 66,61 | 242,74 |
| p95 повторного запроса, мс | 8,34 | 23,04 |
| 100 dispatch, секунды | 2,839 | 1,912 |
| p95 dispatch, мс | 72,37 | 194,59 |
| Повторные внешние отправки | 0 | 0 |

Ровно 100 Lead/100 jobs/100 sent receipts на сценарий, все jobs succeeded,
соединения SQL освобождены. Рост p95 при большей параллельности показывает цену
конкуренции; этот тест **не** определяет число пользователей, скорость дашбордов,
лимит настоящих providers или пропускную способность двух API/Celery replicas.
Проверка не включает HTTP ingress, Redis publication и реальную provider latency.

## Проверки candidate

- Изолированная расширенная регрессия: **260 passed, 31 warnings, 173,97 s**.
  Включает intake/export/reconciliation, legacy adapters, durable work,
  runtime roles, diagnostics, provider transport, reports и worker lifecycle.
- После последней защиты от выключения guard при уже сохранённых admissions:
  **70 passed, 21 warnings, 71,05 s** — reconciliation/intake/runtime roles/
  legacy binding. Это перекрывающийся набор, не ещё 70 уникальных проверок.
- Load smoke вместе с ранним набором reconciliation: **17 passed, 19 warnings,
  31,93 s**; две нагрузочные конфигурации приведены выше.
- Frontend: **2 unit tests passed**, Vite production build — **949 modules,
  2,61 s**, exit 0. В сборке присутствовали и локальные изменения владельца;
  она не является отдельным проверенным deploy artifact этого коммита.
- `git diff --check` пройден. Browser acceptance, полный migration/restore
  rehearsal и общий mixed-load не выполнялись в этом пакете.

## Следующая приёмка

- Проверить final artifact + цепочку миграций на восстановленной БД, rollback.
- Общая нагрузка: дашборды/карточки/периоды одновременно с sync, отчётами,
  очередями и AI; контролируемые сбои Redis/worker и восстановление.
- Operator/browser acceptance и provider sandbox там, где нужны реальные доступы.
- Встроить наблюдение за overdue intakes в общий monitoring; согласовать retention
  audit/closed intake без разрушения idempotency. Общие пункты AI/report/billing
  SQL-over-IO из основного плана этим пакетом не закрываются.

Никаких изменений production и реальных customer sends в этом этапе нет.
