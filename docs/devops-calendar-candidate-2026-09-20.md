# DevOps: bounded calendar candidate 3e5ddae

Статус: реализован, закоммичен, проверен в изоляции. **Не выкачен на production.** Разрешение владельца на deploy получено, но техническая приёмка полного переключения ещё не завершена. Не заменять её одним разрешением или зелёным unit suite.

## Сделано

- `nightly.enqueue` и `reports.rules` больше не выполняют весь календарь внутри одного долгого handler. Parent планирует максимум 100 scoped children и одну continuation; обе части атомарно фиксируются вместе с outbox.
- Keyset pagination с верхней границей в continuation, детерминированные operation keys, повтор/конкурентное планирование без дубликатов. Каждый child привязан к владельцу и конкретному integration/schedule.
- Ночной child перед enqueue повторно проверяет владельца, статус проекта и подключения. Порядок row locks — Client → Integration, как в guarded sync. Смена владельца, отключение или удаление не запускают прежний scope.
- Report child повторно проверяет enabled/day/time/owner и ограничивает обработку одним schedule. Approval-required остаётся approval-required. Старше 15 минут / неприемлемая будущая дата — пропуск без отправки.
- Parents replay-safe; report children, выполняющие внешние отправки, не replay-safe. Ошибка snapshot или неуспешная отправка больше не маскируется успешным завершением child. Уже созданная failed delivery не отправляется повторно при повторном вызове расписания за тот же период.
- Существующая политика маркировки прерванной отправки сохранена, но reconciliation ограничен 100 строками и `SKIP LOCKED`. Scoped обработка не меняет чужие delivery.
- Legacy scheduler сохраняет свой интерфейс. Новый fan-out вызывается только подготовленными durable handlers; production по-прежнему не переведён на них.

## Проверки

- 13 новых PostgreSQL cases: 205 scopes/несколько страниц; replay; четыре конкурентных planner; rollback всей страницы при сбое; tenant scope и disabled schedules; expired/future occurrence; отсутствие timezone; nightly dedupe/смена владельца; approval; failure propagation; failed-send non-replay; bounded reconciliation.
- Полный image-only manifest: **748 passed, 1 skipped, 1 deselected, 47 warnings, 6 subtests passed**, 173,83 s. Skip — optional previous-release comparison; deselected — frontend source assertion, так как frontend намеренно не входит в backend archive.
- Во время разработки исправлен тестовый fixture без обязательных start/end dates. Отдельный targeted run ошибочно включил frontend-source assertion и получил FileNotFoundError; полный правильный manifest прошёл. Эти промежуточные ошибки не выдаются за production-дефекты.
- Candidate: `admirra-devops:3e5ddae`, Image ID `sha256:aca3d4f75e379c8192f44399c7308ea2c133b0ab2f66cbe3ab8a285697993ae1`. Сборка из Git archive (474 разрешённых runtime/test/ops файла), не dirty frontend/landing.
- Свежая post-AI-hotfix recovery point `20260920T190219Z-a6b49102` восстановлена на server 2 в отдельной БД, `network=none`. Все шесть migrations `cc3d4e5f6a7b → cd9e0f1a2b3c` прошли, включая adoption уже существующей assistant ledger. Manifest/checksum, worker preflight, четыре idle worker и API readiness/auth guard — pass; весь drill 46 s. Временные контейнеры/volume удалены.
- Read-load разрешённого аккаунта на восстановленной копии: **40/40 HTTP 200**, concurrency 4, p50 133,74 ms, p95 654,16 ms, max 789,08 ms. Никаких provider calls, клиентских отправок и банковских действий. **Это не peak acceptance активных sync/report workers.**

## Production baseline не изменён

Повторно проверены: backend `6321c5fb…`, frontend `680b8893…`, automation `33b4ca03…`; контейнеры running, public HTTP 200, ingress monitor timer active. Точные digests — `ops/rollback_images.json`. В проде остался AI hotfix; новый calendar и общая миграционная цепочка туда не включались.

## Что не закрыто этой итерацией

1. Короткие транзакции и settings/coverage guards полного sync/history по всем каналам, широкий follow-up диапазонов. Нельзя считать их исправленными за счёт нового enqueue.
2. `reports.export`, billing, lead notifications и prewarm пока используют прежние общие handlers. Render/send stages и report freshness barrier также не завершены. Эта итерация закрывает только два calendar entry points, не весь T08/T09.
3. Scoped provider peak launcher с фактическим ограничением внешних действий и финальная mixed-load acceptance. Scope validator/observer и idle-worker smoke его не заменяют.
4. Доставка alerts человеку отложена. Задан вопрос владельцу о техническом чате либо его присутствии всё окно; ответ ещё не зафиксирован. Отсутствие ответа не является согласованным attended-only исключением. Офлайн-копию recovery key также нельзя считать подтверждённой автоматически.
5. Итоговое окно переключения, проверка rollback после появления новых child kinds, расширение API-2 и две ночи наблюдения. До полного gate нельзя останавливать legacy или запускать новые consumers с production credentials.

Parent success здесь означает **планирование**, не успешную доставку всех children. Отдельного агрегированного batch result UI пока нет; возвращаемые причины skip ещё не отдельное persistent outcome поле. Не обещать этого пользователю как реализованную функцию.
