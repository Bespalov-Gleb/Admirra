# Пункт 2: единая очередь CloudPayments — candidate

Production не менялся, реальные платежи/рассылки не выполнялись. Флаг
`BILLING_PROVIDER_QUEUE=false` по умолчанию; включать только вместе с
`DURABLE_TASKS=true` на всех API и workers одного candidate release.
Schema head `f35e6f708192`, parent `f24d5e6f7081`.

## Реализация

- Interactive API, webhook смены подписки и recurring maintenance сохраняют
  финансовое намерение вместе с изменением подписки. HTTP к CP выполняет
  только `billing.provider`, очередь maintenance, resource владельца аккаунта.
- Порядок определяется DB identity ordinal; выдача ordinal сериализована
  advisory lock аккаунта до commit. Неподтверждённая более ранняя операция
  блокирует последующие, включая новые календарные occurrences.
- Update берёт текущие сохранённые тариф/период/price-book/слоты/чек при
  выполнении, не параметры старого HTTP-запроса. Отмена побеждает устаревший
  update. Update никогда не активирует отменённую у CP подписку.
- Не более 32 открытых операций аккаунта и 20 provider subscriptions за
  выполнение. Неизвестный/отклонённый результат — остановка, не молчаливый пропуск.
- SQL prepare → commit/release → CP → fenced confirmation. Перед каждым
  запросом сохраняется receipt `sending`, после подтверждения — `confirmed`.
  Provider body с нестрогим/отсутствующим `Success:true` не считается успехом.
- Таймаут, падение после отправки или потеря lease не дают права повторить
  запрос. Подтверждённый финальный SQL receipt позволяет восстановить только
  acknowledgement job после падения, без второго HTTP.
- Если локальные условия изменились за время HTTP, создаётся новое намерение
  по текущим данным; исходная операция не переигрывается. Старые Recurrent
  webhook заменённого CP ID игнорируются; поздний Active/Pay не отменяет
  более новое решение пользователя отключить автопродление.
- Checkout заблокирован, пока есть нерешённая операция. Карта/provider ID
  сохраняются до подтверждения отмены. Браузер показывает ожидание/неизвестный
  исход; poll только чтения раз в 10 секунд, максимум 30 запросов, прекращается
  при ошибке, неизвестном исходе и unmount. Кнопка проверки не повторяет платёж.
- CP mutation SDK требует контекст разрешённой worker-операции. Финансовые
  receipts и связанные jobs не удаляются обычным retention. Отдельная политика
  финансового архива нужна при дальнейшем росте, не удалять их вручную.

## Сверка неизвестного результата

Доступна операторская команда, **не автоматический retry**:

```sh
python -m ops.billing.reconcile_operations OPERATION_UUID
```

Она читает ledger и актуальные подписки CP без удержания SQL. Вывод содержит
статусы, технические ID и fingerprint, но не токены/карты/email/raw provider body.
Доступ — только оператор с доступом к application environment на сервере.

Если операция stopped (`failed/uncertain`), оператор обязан установить, что
старый запрос окончательно завершён и не может примениться позже. Для update
сверить также чек, период, валюту и сумму, а не одну сумму. HTTP 200, истечение
lease или отсутствие записи в логах не являются такой сверкой.

После подтверждения в CP/support допускается **новое** намерение:

```sh
python -m ops.billing.reconcile_operations OPERATION_UUID --retry-current \
  --version VERSION_FROM_INSPECT --provider-fingerprint FINGERPRINT_FROM_INSPECT \
  --actor 'имя оператора' --reason 'обоснование решения' \
  --settled-reference 'ссылка на проверку/обращение CP и окончательный результат'
```

Команда заново читает CP и проверяет неизменность операции. Не отправляет
изменений в CP; атомарно оставляет аудит, закрывает старое намерение как
`superseded` и создаёт/объединяет новое. Не разрешает действующий worker,
неизменённую историю не стирает. Без достоверной сверки оставить `uncertain`.
Это CLI-runbook; отдельный экран супер-админки пока не реализован.

## Rollout и rollback

1. Проверить backup/restore конечного schema head и весь regression manifest.
2. Закрыть новые billing mutations/checkout на admission, дождаться старых
   API/worker HTTP; webhook не терять, обеспечить retry провайдера.
3. Разобрать старые `billing.recurring=uncertain`; они блокируют включение.
4. Применить additive migration, выпустить все writers одной версии,
   выставить одинаковый флаг, head и immutable release, затем открыть admission.
5. Проверить sandbox E2E смены тарифа/слотов/карты, отмену и webhook reorder.

Нельзя смешивать старые прямые CP writers с новой очередью. Startup candidate
отказывается отключать флаг при открытых намерениях. Downgrade не удаляет
финансовые evidence. Старый image, не знающий нового ledger, не является
допустимым rollback при незавершённых операциях; сначала остановить admission,
дождаться/сверить операции и только затем принять отдельное решение отката.

## Проверки и оставшиеся границы

Изолированные PostgreSQL/Redis, синтетические аккаунты, internal Docker network;
CP полностью замокан. Пройдены FIFO, atomic rollback, no-SQL-over-HTTP,
таймаут/частичная отмена, отсутствие реактивации, lost lease, crash-after-commit,
смена условий в полёте, чужой scope, CLI audit/stale observation, миграция,
preflight и совместимость legacy flag=false. UI: 5 lifecycle tests и Vite build.
Расширенный backend-прогон: **171 passed**, включая действующий signup-discount
flow, billing guards и failure tests. Общий isolated manifest после этого пакета:
**1281 passed, 1 skipped, 1 deselected, 209 warnings, 6 subtests passed**,
725,46 с; внешние провайдеры заменены тестовыми транспортами.

Не считать этот пакет полным закрытием пунктов 1–4: остаются немедленные lead
exports/validation, legacy analytics/blacklist scopes, оставшиеся report/AI
SQL-over-IO пути, общая операторская UX-приёмка и затем пункты 5–8. Визуальная
приёмка страницы тарифов и настоящий CP sandbox нужны перед включением флага;
реальные пользовательские списания не являются тестовым сценарием.
