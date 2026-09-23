# Bounded consumer refresh — candidate, не production

## Область изменений

Продолжение `0e96d35`: проверка покрытия теперь может поставить недостающую
историю в durable queue для DB-backed AI, Google Sheets и детектора.
Миграция `f24d5e6f7081` добавляет `data_refresh_requests`, parent
`f13c4d5e6f70`. Производственная БД, сервисы, внешние рассылки и платежи
при разработке не менялись.

`CONSUMER_REFRESH_ENABLED=false` по умолчанию. Для включения нужны durable
writers, `REPORT_FRESHNESS_GUARDS`, `REPORT_DELIVERY_GUARDS` и индивидуальный
флаг соответствующего consumer. Старый и новый календарь параллельно не запускать.

## Контракт

- Запрос содержит разрешённый scope пользователя, период, настройки источников,
  неизменяемый deadline текущей попытки, epoch и список durable job IDs.
- Только `missing_or_stale` запускает догрузку. Отсутствующие подключения,
  неверные настройки, orphan/raw history и превышение лимитов не маскируются нулями.
- История загружается через существующий `history.backfill` / `sync.backfill`,
  в кусках не более 30 дней. Не более двух новых jobs за проход,
  по умолчанию 8 активных history jobs глобально и 2 на владельца.
  Бюджет общий с report refresh; ручная backfill-нагрузка также учитывается.
- Не более 128 ожидающих запросов глобально, 8 на пользователя, 64 receipts
  на запрос. Ожидание по умолчанию 30 минут, допустимая настройка 1–120 минут.
- Повторы одного scope/settings/периода используют тот же запрос. Совпадающие
  активные consumer history jobs объединяются между AI/Sheets/detector.
  ReportDelivery сохраняет собственные receipts/authorization; его очередь
  разделяет бюджет, но межотчётное объединение этим пакетом не заявляется.
- Перед fetch и apply воркер проверяет durable execution, настройки источника,
  активность проекта и наличие хотя бы одного действующего разрешённого запроса.
  Отзыв доступа, смена настроек или истечение срока не дают задаче права применить данные.
- Контроллер проверяет до пяти due requests за проход в отдельной SQL-транзакции.
  Занятые источники пропускаются; ошибка производного расчёта останавливает только
  его подготовку, а не публикацию всех остальных очередей.
- Старые неактивные запросы удаляются ограниченными пачками после 30 дней.
  Повтор подготовки создаёт новый epoch, не стирая evidence предыдущих jobs.
- Готовность означает повторную успешную проверку полного покрытия, а не просто
  завершение очереди. Ошибка/неизвестный исход job останавливает подготовку.

## UI и границы автоматизации

`GET /api/data-refresh/{id}` показывает статус; `POST /{id}/retry` повторяет
только подготовку. Доступ проверяется по пользователю и всем проектам scope.
Подготовка детектора общая для владельца и имеющих доступ участников команды.

AI-комментарий, старый DB-backed чат, Google Sheets и нейтральный баннер детектора
показывают конечные waiting/held/ready состояния. Poll раз в 30 секунд, прекращается
при deadline, ошибке, готовности или закрытии компонента. Поздний ответ прошлого
компонента/проекта не возвращает его состояние на текущий экран.

После готовности **не** запускаются автоматически платный AI, Google export или
отправка клиенту. Для них остаётся явное действие пользователя. Детектор может
пересчитать SQL-выводы после подтверждения покрытия без LLM/внешнего отправления.
Существующая политика ReportDelivery resume этим не заменяется.

UI-сборка и модульные тесты не заменяют визуальную приёмку и проверку браузером
на candidate. Полный release regression, restore, mixed load и cutover остаются
отдельным этапом.

## Сопутствующие точечные исправления пунктов 2–3

- Email report guard материализует значения до commit и истечения ORM-объекта:
  SMTP/Unisender больше не открывает лениво SQL-транзакцию из `delivery`.
  Отдельный тест проверяет ноль занятых соединений непосредственно в transport
  и отсутствие повторной отправки уже принятому получателю.
- CloudPayments `/subscriptions/find`: HTTP 200 с `Success:false`, неверной
  структурой или чужим AccountId больше не считается пустым списком подписок.
  При неподтверждённой отмене сохраняются provider ID и данные привязанной карты
  для сверки; ответ содержит `cancellation_pending=true`.

Контракт lookup сверён с [официальной документацией CloudPayments](https://developers.cloudpayments.ru/#poisk-podpisok).
Это **не** полное закрытие BILL-01: общий durable порядок interactive update/cancel,
webhook и recurring worker, provider-state reconciliation и операторское разрешение
неизвестных исходов ещё нужны. Старые немедленные lead exports и оставшиеся
report/lead SQL-over-IO пути также не объявляются исправленными этой email-правкой.

## Проверки

Изолированные PostgreSQL/Redis на server 2, internal network, `WW_TEST=1`,
синтетические пользователи/источники, provider transports замоканы. Никаких
реальных банковских списаний, CRM/Telegram/email-отправок.

- Первый consumer/coverage/report прогон: 55 passed.
- Расширение coverage/source scope/migration/runtime regression: 186 passed.
- Промежуточный report/billing прогон: 97 passed, 1 packaging failure — проверка
  читала frontend `Reports.vue`, которого не было в backend-only archive.
  Файл добавлен из Git для повторного запуска; assertion не ослаблен.
- Frontend: 8 readiness tests passed; Vite production build passed.
- Объединённый backend regression: **267 passed, 28 warnings**, 209,48 с
  (consumer refresh, runtime, coverage, freshness, scopes, report guards,
  CloudPayments lookup/cancel, billing workers, reports).
- После последней правки явного retry без scheduler: **58 passed, 16 warnings**,
  30,88 с (consumer refresh + report guards + CloudPayments lookup/cancel).

## Остаток по согласованным восьми пунктам

1. Bounded history refresh для consumers реализован в candidate; rollout ещё не выполнен.
2. Сериализация финансовых операций реализована в candidate `f81e774`:
   account-scoped CP intents, receipts, сверка через CLI и pending/uncertain UI.
   Перед включением нужны sandbox E2E и операторская приёмка.
   [Контракт и rollout](devops-billing-order-2026-09-22.md).
3. Legacy SQL-over-IO: исправлены email report transport и automatic AI report
   (`14c6131`, immutable snapshot, один AI attempt, release SQL до AI/render).
   Scoped analytics/blacklist закрыты отдельным candidate 23.09
   ([контракт](devops-lead-placements-2026-09-23.md)). Модуль проверки заявок,
   включая immediate lead exports/validation, ранние отказы и его diagnostics,
   **возвращён владельцем в объём релиза 23.09**: не отключать, закончить проверки.
   В активном плане также interactive report/AI пути и offline conversion
   Метрики в billing webhook.
   [Проверки и границы отчётов](devops-report-comment-2026-09-22.md).
4. Waiting/error/retry для data readiness реализованы; визуальная приёмка и UI
   разрешения финансовых/внешних uncertain исходов ещё не пройдены. Для CP уже есть
   операторская CLI и ограниченный read-only polling; это не полная UX-приёмка.
5. Shared state двух API: files/cache/upload/SSE и drain — предпродовая проверка.
6. Финальные artifact regression, restore/migrations, mixed load/recovery — предпродовая проверка.
7. Human acceptance алертов, offline recovery key и ответственный — подготовка.
8. Только здесь контролируемый production cutover с backup/drain/admission и наблюдением.

S3 и две ночи наблюдения по-прежнему отложены владельцем, а не отмечены выполненными.
