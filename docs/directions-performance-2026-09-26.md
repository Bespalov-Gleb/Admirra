# Направления: раздельные загрузки и кеш Метрики

## Диагностика

26.09, ЛидерСтрой / Иркутск: `/directions/` 14–73 ms, `/directions/stats`
до 21.056 s (04:30:20 UTC). В тот же период повторялись одинаковые Metrika GET.
Desktop/mobile selector ждал `directionStats.items`, хотя быстрый endpoint уже
возвращал названия и campaign_ids. Два watcher повторно запускали list+stats при
смене проекта; смена периода также перезагружала независимые от дат определения.
Модальное окно не отличало загрузку/ошибку от действительно пустого списка.

## Изменения

- `useDirectionData`: отдельные scope ключи project/channel и project/channel/dates;
  один in-flight read на ключ, отмена старого scope, защита от поздних ответов.
- Desktop/mobile selector использует определения; статистика карточек остаётся
  серверной. «Без направления» добавляется только после ответа статистики.
- Определения текущего scope переиспользуются 30 s при повторном открытии; смена
  проекта/канала, CRUD/reorder и окончание sync обновляют их. Между scope кеша нет.
- Явные loading/error/retry состояния. Ошибка статистики не удаляет определения.
- Переименование блока больше не запускает повторный расчёт лидов.
- Исправлен overflow настройки названия блока внутри мобильной модалки.
- Формулы, атрибуция, БД, worker-код не менялись.

## Read-cache rollout

Существующий `core.shared_read_cache` используется **только** Metrika GET:
conversions-by-dimension 60 s, goals 30 s. Это не общий кеш дашборда/авторизации.
Ключ: credential fingerprint, профиль, endpoint и все параметры (цели, даты,
счётчик, фильтр, attribution, dimension). Доступ к проекту проверяется до вызова.
Ошибки не кешируются; Redis failure возвращает к обычному provider read.
Redis отдельный от брокера, API endpoint private 10.77.0.2:6380.

Включение только на API1/2 через explicit `--shared-read-cache true` в
`ops.deploy_dashboard_lockfix.py`; pinned API image/release остаются 32a8d9e.
Worker runtime не менять. `ops/launch_flags.json` остаётся консервативным baseline;
при будущем render нового API сохранить accepted override SHARED_READ_CACHE=true.
Каждую ноду сначала drain через `ops.onboarding_ingress` с НОВЫМ snapshot; дождаться
завершения старых Nginx workers, затем activate, readiness, restore ingress.
Rollback — previous.json этого rollout с прежним false; Redis flush не требуется.

## Проверки до rollout

- 8 direction unit + AI/polling regression: 38 tests passed.
- Изолированный Chromium: реальная разметка dropdown/modal + composable,
  медленный stats не блокирует четыре направления, selection работает, repeated
  open без нового GET, scope switch/error/retry, мобильный overflow отсутствует.
  Это fragment QA, не полный authenticated E2E dashboard.
- 16 shared-cache pytest на отдельном internal-network Redis: cross-loop
  coalescing, isolation, credentials rotation, errors, cancellation, lock expiry,
  bounded TTL, invalid response rejection. Никаких production credentials/network.
- Read-only probe с PostgreSQL `default_transaction_read_only=on`, период
  21–25.09.2026: no-cache 6.490 s, cached repeat 0.072 s на API1, API2 0.729 s.
  Все четыре результата совпали (SHA256
  `391071dfe7dbcc7ae93c5ecaa2f242cafa385f0968b311fda084be31abdcdc73`).
  Первый кеширующий запрос мог частично использовать записи предыдущего probe:
  1.944 s не заявляется как cold-cache benchmark. Cold reads всё ещё зависят от
  времени ответа Метрики; 0.072 s не обещание для любой загрузки дашборда.

Production acceptance дописывается после фактического rollout.
