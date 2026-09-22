# Ограниченное обновление данных отчётов и состояния ожидания

Статус: **локальный candidate, не production**. Продолжение `47baf48`; новая миграция не нужна, schema head остаётся `f13c4d5e6f70`. Включается существующим opt-in `REPORT_FRESHNESS_GUARDS`; условия его включения не изменены.

## Реализация

- При нехватке подтверждённого покрытия создаются существующие durable `history.backfill` в низкоприоритетной `sync.backfill`. Producer выполняет только SQL: HTTP остаётся в fetch/apply worker. Текущий watermark и AI enrichment не запускаются этим producer.
- Загружаются только отсутствующие/устаревшие диапазоны, включая сравнительный период. Пересекающиеся пробелы стадий объединяются; один job охватывает максимум 30 дней.
- Не более двух новых задач за проверку, по умолчанию восемь queued/running report-refresh задач глобально и две на владельца источника. `REPORT_REFRESH_GLOBAL_JOBS` имеет диапазон 1–32, `REPORT_REFRESH_OWNER_JOBS` — 1–4. Бюджет сериализован неблокирующим PostgreSQL advisory lock; занятая блокировка оставляет работу следующему poll без ожидания SQL lock.
- Не более 64 receipts на один цикл ожидания. Повторные проверки не создают дубликаты одной integration/settings/date/epoch задачи. Между разными отчётами нет общего coalescing: одинаковый диапазон может загружаться повторно, но ограничение бюджета и integration resource lease сохраняются. Это не отдельный vendor RPS limiter; provider quotas требуют общей приёмки.
- Deadline не продлевается автоматически. Перед HTTP и перед apply проверяются текущие права, активность пользователя, статус отчёта, epoch, настройки интеграции и расписания. Отмена, смена настроек/прав или истечение времени отзывают разрешение на дальнейшую работу.
- API `POST /reports/deliveries/{id}/refresh-data` разрешает новый цикл только для собственного pending/held отчёта с `deadline_expired`, без снимков, утверждения, результатов и любых route attempts. Старые jobs теряют разрешение через новый epoch. Повтор всегда переводится в `source=manual`: после подготовки требуется согласование, автоотправки нет. Неизвестные исходы доставки нельзя стереть этим endpoint.
- UI очереди и окна согласования показывает «Ожидаем данные» / «Нужна проверка», объяснение, срок, ручную проверку статуса, разрешённую сервером повторную подготовку. Нулевые KPI, AI-комментарий и кнопка отправки в этих состояниях не отображаются. Видимая страница очереди обновляется раз в 30 секунд только при waiting; timer снимается при unmount.

## Проверки

- Изолированный synthetic PostgreSQL/Redis на server 2, project `admirra-report-refresh-20260922`, internal network, `WW_TEST=1`. Source `47baf48` + scoped patch, dependencies `admirra-devops:3d65ef3`. Без реальных отправок, платежей и provider API.
- **156 passed, 25 warnings, 120,79 s**: `test_report_refresh`, `test_report_freshness`, `test_integration_work_scope`, `test_calendar_work`, `test_reports_final`, `test_report_route_guards`, `test_sync_coverage`.
- Проверены gaps/дедупликация/30-дневные chunks/owner и global caps; отмена, deadline, смена settings/epoch/доступа/флага до внешнего IO; ручной reset и запрет при uncertain route attempt.
- Frontend readiness helpers: **4 passed**. Vite production build прошёл. Сборка выполнена в текущем рабочем дереве с чужими незакоммиченными правками: это не release artifact.
- Safari, отдельный localhost harness с полностью подменённым axios: визуально проверены desktop held/light и waiting/dark, переход retry → waiting/manual, отсутствие отправки и фиктивных KPI. Harness удалён после проверки. Мобильная визуальная приёмка и реальный end-to-end provider refresh этим прогоном не закрыты.

## Следующий шаг

Подключение остальных consumers (direct exports/Sheets, AI, detector), завершение разделения render/send и ресурсных лимитов; затем полный immutable artifact regression/restore/mixed-load и контролируемое переключение. Старые неподтверждённые снимки требуют отдельной операторской политики, не автоматического reset. Production flags, миграции, workers и canary этим этапом не менялись. S3 и две ночи наблюдения остаются отложенными, а не выполненными.
