# Привязка отложенных integration jobs к владельцу и проекту

Candidate `c27876e` + `ac01ed8`, 21.09.2026. Новые workers, миграции и расширение API-2 этим пакетом в production не включаются.

## Найденный риск и исправление

Goals-only job раньше сохранял только integration ID и даты; history backfill сохранял project ID, но не owner ID. Перенос проекта другому владельцу между постановкой и запуском позволял старой задаче принять текущего владельца как своего.

- Новые goals/history payload сохраняют `integration_id`, `client_id`, `owner_id`. Credentials туда не добавляются. Goals enqueue берёт короткие locks в порядке client → integration и не ставит работу для отключённого/неактивного источника.
- `automation/integration_work_scope.py` проверяет настоящую строку `background_jobs`: действующий lease/token, running state, kind, canonical resource, tenant и полное совпадение payload. Аргументы вызова сами по себе не дают права работать с integration.
- Перед preparation/legacy sync проверяется текущая связь integration → active project → owner. Изменённая связь, удаление, пауза или отключение приводят к отказу до provider IO. `IntegrationScopeChanged` наследует `RejectedBeforeExternalIO`: это явный `failed`, не успешный пропуск и не неопределённая внешняя запись.
- Goals preparation дополнительно сверяет owner/project полученного snapshot с исходной задачей: READ COMMITTED может увидеть перенос между первым guard и следующим SELECT. Эту гонку закрывает отдельный commit `ac01ed8`.
- После сетевого сбора goals существующий apply повторно проверяет settings/owner/status под короткими locks. Новая проверка подтверждает, что смена владельца во время HTTP не публикует результат в новом scope и сохраняет прежние данные.
- Worker preflight блокирует запуск при незавершённых старых goals/history jobs без owner/project binding либо с противоречивым resource/tenant. Автоматической перепривязки к текущему владельцу нет: старые задачи нужно явно сверить и при необходимости поставить заново. Terminal records можно сохранить как evidence.

## Проверки

Targeted: **93 passed**, 91,43 с. Первый прогон выявил ошибку тестового fixture: history task ошибочно попал в manual queue и блокировался механизмом приоритетов; исправлен fixture, production priority logic не менялась.

Проверяются два kind, корректный scope, перенос integration между проектами одного/разных владельцев, смена owner, удаление/пауза/отключение, подмена tenant/resource/kind/payload, просроченный/чужой lease, исчезнувшая задача и вызов без fence. Отдельно проверены enqueue без credentials, legacy preflight и сохранность 34 старых конверсий при конфликте во время сбора.

Полный manifest чистого Git-артефакта `ac01ed8`: **963 passed, 1 skipped, 1 deselected, 54 warnings, 6 subtests passed**, 368,17 с. Image `admirra-devops:ac01ed8`, digest `sha256:d19f17398ee55d2f9c379b7817c6975b11c0b29ceccd5b121ebd162a77bf6fdf`. 47 новых случаев относительно предыдущих 916 вошли в общий прогон. Docker test network internal=true, synthetic PostgreSQL/Redis, non-root/read-only, без production credentials. Промежуточный полный прогон `c27876e` остановлен намеренно после дополнительного исправления гонки подготовки; его нельзя считать успешной приёмкой. Frontend-source test исключён штатно, frontend не входит в backend artifact; optional baseline comparison пропущен.

Свежий backup `20260921T200100Z-b4397303` восстановлен и мигрирован до `cd9e0f1a2b3c` тем же финальным образом: **51 с, network=none**, worker preflight, boot четырёх групп workers, application readiness/auth guard и read smoke passed. На разрешённом тестовом аккаунте 40/40 HTTP 200, concurrency 4, p50 158,65 мс / p95 1072,03 мс / max 1371,02 мс. Summary p95 389,16 мс; clients p95 1371,02 мс. Это чтение восстановленной копии при idle workers, не browser timing, не доказательство ускорения относительно предыдущего прогона и не real-provider peak.

После smoke удалены test containers/network и restore containers/volume. Проверено: API-2 backend healthy; production backend `4ca866eb…`, frontend `274aad1d…`, automation `33b4ca03…` не изменены, `/projects` HTTP 200, мониторинг 7/7 targets up, 0 active alerts. Реальных provider calls, клиентских сообщений и банковских операций при проверках не было.

## Границы

History handler всё ещё использует legacy `sync_integration` с долгой SQL-сессией. Новый входной guard **не** закрывает смену owner/settings во время всех внутренних HTTP/commit этого legacy пути. Полный fetch → validate → apply, coverage/settings guards по каналам и failure matrix остаются обязательными до переключения новых workers.

Это correctness/security задачи очереди, не новый frontend performance rollout. Прямые legacy sync/API пути не переводятся автоматически на этот guard. Mixed-provider peak, shared files/cache/SSE/drain и общий cutover остаются открыты. S3 и две ночи наблюдения отложены владельцем, не отмечены выполненными.
