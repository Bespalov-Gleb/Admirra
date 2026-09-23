# Dashboard attribution: SQL отдельно от Метрики

23.09.2026. Код `f460f81`, сборка `e7aaafb`, **не production deployment**.
Production env, ingress, БД и scheduler не изменялись.

## Что исправлено

Три общих builder-а в `backend_api/stats.py` раньше загружали ORM-кампании,
лениво читали integration и держали request SQL transaction во время HTTP:

- `_build_yandex_campaign_conversion_overrides`;
- `_build_yandex_campaign_daily_conversion_overrides`;
- `_build_avito_campaign_conversion_overrides`.

Теперь `backend_api/attribution_read.py` собирает plain-value план в коротком
read-only PostgreSQL snapshot, освобождает SQL перед IO и после ответа заново
проверяет настройки. Во время провайдера ни транзакция, ни pool slot не заняты.
Integration/campaign данные загружаются пакетно, без N+1 ORM relationships.
Подготовка и проверка имеют постоянное число SELECT, не зависящее от числа
интеграций; CPU-группировка кампаний линейная.

Проверка обнаруживает удаление/перенос integration, новые/переименованные
кампании, смену целей, счётчиков, токена/профиля, Avito Metrika grant,
владельца/папки проекта. HTTP callers передают actor ID; до/после IO проверяются
активность пользователя и доступ к исходному набору проектов. Отзыв доступа
даёт 403, изменение attribution contract — 409 с предложением обновить данные,
а не успешный ответ с устаревшими цифрами. Детектор не маскирует эти отказы
fallback-ом на другой источник конверсий. Обычное обновление статистики или
баланса не инвалидирует неизменный attribution contract.

На исключении/отмене SQL освобождается. Pending ORM writes отклоняются до
rollback/autoflush: helper предназначен только для проверенных read paths.
Credential-bearing значения не являются DTO, их repr не содержит токенов.

Потребители общих builder-ов: campaign table, фильтрованные summary/goals,
daily/period dynamics, карточки направлений, campaign highlights. В children
исправлен только вызов общего builder-а, **не весь hierarchy endpoint**.

## Найденные при регрессии ошибки расчёта

1. Фильтрованная таблица кампаний повторно распределяла общий остаток Метрики
   на выбранные строки. Synthetic fixture: 65 лидов проекта, точная атрибуция
   34 и 31; при выборе первой кампании таблица возвращала 65 вместо 34.
   Теперь allocation выполняется по всем кампаниям доступного проекта, а
   display filter применяется к готовым строкам. Provider overrides таблицы
   также собираются для полного scope, включая предыдущий период.
2. В проекте с Яндексом и Авито одинаковые goal IDs могли смешивать суммы двух
   интеграций: чужие визиты становились остатком Яндекса. `get_campaign_stats`
   теперь явно ограничивает Metrika totals каналом каждой рассчитываемой
   секции, в том числе в режиме `all`.

Формулы расхода/CPL и native VK conversions не заменялись. Сохраняются
существующие правила округления, неоднозначных имён и недоступных целей.
Это исправление воспроизводимого кода, не сверка реального рекламного кабинета.

## Проверки и границы

Чистый image `admirra-devops:e7aaafb`:
`sha256:3c89e79d6eaa14ef1e7505a4607ee5d1e54ab87e2cc10eb881e5c1a56307b2c5`.
Архив содержит 601 allowlisted файл из Git, без `.env`, uploads и пользовательских
незакоммиченных изменений. Первая artifact-проверка выявила каталоги с mode 700
после распаковки с umask 077: непривилегированный процесс не мог импортировать
`ops`. В `e7aaafb` Dockerfile нормализует read/traverse права исходников через
`chmod -R a+rX /app`, без новых прав записи и без переноса secrets в образ.
Предыдущий image `f460f81` не принят, в cutover его использовать нельзя.

`tests/test_attribution_read.py`: настоящая isolated PostgreSQL, обычный ORM,
pool_size=1, max_overflow=0, timeout=0,3 s. В проверяемых provider await точках
другой читатель занимает единственное соединение и выполняет SELECT 1.
Метрика заменена синтетическими ответами, клиентские API не вызывались.

Проверяются оба канала, несколько интеграций, предыдущий CPL, сценарий 34/65
на шести consumers, mixed table с одинаковыми goal IDs, смена настроек/доступа,
отмена/ошибка, pending writes, неоднозначные имена, отсутствие vs нулевые
конверсии и постоянное число запросов подготовки.

Финальная artifact-only регрессия `e7aaafb`: **211 passed, 1 skipped,
1 deselected, 53 warnings**, 107,03 s, exit 0. В образе, без source bind,
проверены новые attribution tests, summary/Avito, read snapshot/mixed workload,
assistant VK/DB lifecycle, detector iteration3, Metrika failure/shared cache,
reports, backend packaging и API-role boot. Новых attribution cases — 36.
Skip — опциональное сравнение с previous-release implementation; deselect —
frontend source assertion из `test_reports_final.py`, поскольку backend artifact
намеренно не содержит frontend. Полный isolated manifest не повторялся.

Первая source-overlay попытка: 188 passed, 1 skipped, один отказ из-за того же
отсутствующего frontend-файла (а не backend-ошибки). После нормализации прав
image окончательный целевой прогон выше завершился успешно.

Restore acceptance этого же image: backup `20260922T221413Z-b1eea7ec`,
миграция до `f68b92a3b4c5`, **67 s**, network=none. Worker preflight/boot,
application smoke и **64/64 HTTP 200** прошли. Compact/full metadata contract
совпадает; summary batch — 64 проекта × 4 канала, 12 сравнений с отдельными
чтениями, access guards passed (752,38 ms). Это не проверка реального vendor
API и не рабочая нагрузка Celery: внешние отправки отключены, workers только
запускаются/проверяются. Короткий read smoke: 12,495 s, aggregate p95 1789,94 ms,
по 8 запросов на маршрут, concurrency 4 — недостаточно для принятия SLO.

Логи на сервере 2, root-only:
`/opt/admirra-staging/e7aaafb/attribution-tests.log` и
`/opt/admirra-staging/e7aaafb/restore.log`.
Isolated compose-проект `admirra-attribution-io-review` удалён; restore
containers/volumes и runtime tmpfs отсутствуют. Непринятый image `f460f81`
удалён, принятый `e7aaafb` и логи сохранены. Production контейнеры не трогались.

Это **не** атомарный snapshot всей страницы вместе с внешней Метрикой:
provider и локальная витрина обновляются независимо. Проверяется каждый
provider этап, а не одна глобальная транзакция на все периоды/HTTP-запросы.
Не заявляется уменьшение времени ответа самого API Метрики или доказанное
ускорение всех страниц. При campaign filter расчёт теперь требует полного
набора строк проекта ради корректного allocation; его стоимость тоже нужно
учитывать при финальной mixed-load приёмке.

## Следующая работа

- SQL-over-IO в lazy hierarchy `/campaigns/{id}/children`, audience/top ads
  и других legacy paths; повторная проверка remaining AI/report/billing paths.
- Реальная двухузловая приёмка cache/files/SSE/drain и смешанного потока
  API + очередей синхронизации/отчётов, подтверждение SLO.
- Финальный backup/preflight и контролируемое переключение production.

S3 и две ночи наблюдения остаются отложенными по решению владельца, не
считаются выполненными. Эта работа не изменяет согласованный порядок cutover.
