# Ограниченный snapshot истории Google Sheets

Candidate `b71ec3c`, 21.09.2026. Не production rollout. Изменены только подготовка данных scoped `reports.project` и классификация доказанного отказа до внешних side effects. Формулы метрик, отображаемые колонки и Google SDK отправки не меняются.

## Исправление

`GoogleSheetsService.prepare_snapshot` раньше загружал через ORM `.all()` всю историю Direct/VK/Avito, целей и отчётов, затем создавал ещё и набор списков для Google SDK. Теперь `automation/sheets_snapshot.py`:

- Выбирает только нужные scalar-колонки; server-side cursor/yield_per 128, без накопления ORM identity map. Все запросы ограничены одним project ID; авторизация owner/project остаётся в `calendar_work.export_project`.
- Сохраняет полную историю и прежние четыре листа, платформы, заголовки и преобразования чисел. Одинаковые ключи сортировки дополнены ID для стабильного порядка. Не заменяет исходные числа собственными метриками.
- Имеет общий лимит **50 000 строк данных и 8 MiB сериализованного JSON** на весь snapshot, с учётом ключей/заголовков/ASCII escaping. Это не обещание RSS=8 MiB: Python objects и SDK имеют дополнительные расходы; лимит числа строк и container memory limit действуют отдельно.
- `SHEETS_SNAPSHOT_MAX_ROWS` допускает 1–200 000, `SHEETS_SNAPSHOT_MAX_BYTES` — 1–33 554 432. Неверные значения запрещены, без режима unlimited. Defaults отражены в `.env.example`, worker может получить overrides из `/etc/admirra/worker.env` при будущем rollout.
- Campaign/goal text длиннее 16 384 символов отклоняется. SQL CASE возвращает marker вместо чрезмерно длинной строки, чтобы даже одна порция не принесла гигантские поля в память. Исходная БД не обрезается и не меняется.
- Превышение лимита завершает чтение/закрывает cursors; никакого успешного усечённого snapshot нет. Все четыре листа готовятся **до** создания Google SDK и очистки/записи удалённой таблицы.

## Результат задачи при отказе

`RejectedBeforeExternalIO` — узкий тип доказанного отказа до любой внешней записи/отправки/списания. Только `ExportSnapshotLimitExceeded` использует его в этом пакете. Ledger фиксирует `failed`, без автоматического retry, а не `succeeded` или `uncertain`. Следующий occurrence не блокируется неопределённостью, которой в этом случае нет.

Обычные исключения не переклассифицируются по тексту. Timeout после записи первого листа остаётся `uncertain`, повторная доставка не вызывает новую запись. Нельзя оборачивать в `RejectedBeforeExternalIO` ошибки после предыдущих recipients/листов/provider calls. Изменение не снимает финансовые/reconciliation guards предыдущих пакетов.

## Проверки

Первый targeted прогон: **84 passed**, 70,49 с, изолированные PostgreSQL/Redis. Добавлены ещё два сценария для финального manifest: остановка после limit+1 строки на источнике из миллиона строк и timeout после начала записи через настоящий durable executor.

Проверяется полное совпадение с legacy output для 900 рекламных строк трёх каналов плюс цели/недельный/месячный отчёт; исключение чужого проекта; ровно шесть streaming SELECT без ORM истории; shared row/byte budget; escaped Unicode; oversized names/goal ID; cursor cleanup; no SDK/clear/write на oversized snapshot; failed/uncertain и отсутствие повторных side effects. Все внешние Google-вызовы подменены, реальных клиентских таблиц тесты не меняют.

Полный manifest из чистого Git-артефакта `b71ec3c`: **916 passed, 1 skipped, 1 deselected, 54 warnings, 6 subtests passed**, 297,72 с. 22 новых тестовых случая вошли в общий прогон. Image `admirra-devops:b71ec3c`, digest `sha256:3608daedca371a5619ce1632a09c5b53824d8d11b97873dc750783773efd9294`. Docker test network internal=true, host ports отсутствуют; production credentials не используются. Frontend-source assertion исключён штатно, frontend в backend artifact не входит.

Создан и восстановлен свежий backup `20260921T193554Z-d1d7a3c6`: migration до `cd9e0f1a2b3c`, worker preflight/boot, application и read smoke passed; 52 с, network=none. Чтение разрешённого тестового аккаунта: 40/40 HTTP 200 при concurrency 4, p50 160,91 мс / p95 883,23 мс / max 1027,85 мс. Это не browser timing и не mixed-provider peak. Изолированные containers/network/restore volume удалены.

Production не переключён: backend `4ca866eb…`, frontend `274aad1d…`, automation `33b4ca03…`. После проверки `/projects` HTTP 200, мониторинг 7/7 targets up и 0 active alerts. API-2 по-прежнему только в ранее разрешённом canary. Реальные Google Sheets, платежи и клиентские сообщения в этих проверках не вызывались.

## Что не закрыто

Это ограничение ресурсов, не реализация неограниченно большого экспорта. Истории сверх лимита получают отказ; нужен bounded spool/chunk pipeline с квотами провайдера и явным статусом в UI. Existing legacy interactive `export_all/raw_rows/...` остаются без нового memory bound, пока не переведены на общий pipeline. Google запись по листам не атомарна: возможна частичная внешняя запись, поэтому неопределённость не повторяется автоматически.

Snapshot остаётся снимком данных, последовательно прочитанных в текущей SQL-транзакции; freshness barrier/coverage/revision и согласованный multi-source snapshot этим пакетом не реализованы. Полный REPORT-01/02/03 и общий DevOps cutover остаются открыты. S3 и две ночи наблюдения по-прежнему отложены владельцем.
