# DevOps: follow-up синхронизаций, scoped export и AI-сеть API-2

Состояние на 21.09.2026, МСК. S3 по решению владельца не внедряем в этой итерации. Это отчёт о конкретном этапе, **не подтверждение полного production cutover**.

## Изменения приложения — candidate, не production

- `7f87205`: диапазон sync фиксируется при приёме запроса; совпадающий запрос объединяется, более широкий не теряется. Не запущенная задача расширяется, для уже исполняемой создаётся последовательный follow-up. Повтор ночного planner не порождает новую синхронизацию после завершения присоединённой manual job. Приоритет ещё не занятой ночной задачи повышается при ручном запросе. При завершении предыдущей задачи интеграция остаётся pending, если есть продолжение. В API статуса доступна связь `request.after_sync_job_id`; отдельный UI индикатор не добавлен.
- `e98636a`: при расширении ручной задачи ночным запросом сохраняется не только manual queue, но и пометка ручного запуска для интерфейса/истории.
- `11f935d`: `reports.export` планирует максимум 100 project children за страницу. Подготовка данных одного проекта отделена от Google Sheets IO; при создании SDK и внешней записи SQL-соединение уже освобождено. Владелец, активность проекта и destination повторно проверяются перед отправкой. Ошибка одного проекта больше не прерывает глобальный проход. Parent success означает планирование, не доставку children.
- `c45b407`: операция с неопределённым внешним исходом удерживает свой resource. Новый календарный идентификатор не позволяет автоматически обойти `uncertain` и повторить side effect. Другие resources продолжают работу. Нужна явная сверка результата; новая UI/операторская процедура reconciliation этим изменением не реализована.
- `e080b13`, `a6935a2`: сбой выбранных целей Метрики в Direct (в том числе при пустом отчёте) и в связке с Avito не маскируется SUCCESS. Дата последней успешной синхронизации не продвигается; детектор не запускается по этому незавершённому пути. Ошибка Метрики не интерпретируется как повод повторно обновлять Direct-токен. Если Direct-токен действительно обновлён, дальнейший запрос целей использует новый токен.

Границы: digest настроек при enqueue — **не** полный settings guard на commit. Полная синхронизация всё ещё содержит долгие SQL-транзакции и частичные коммиты. Изменение статуса при ошибке целей не превращает уже сохранённые рекламные данные и старые цели в атомарный общий snapshot. Исправление атомарной замены standalone Метрики описано ниже; её полный settings/coverage контракт и остальные обязательные/необязательные стадии ещё требуют работы. Google Sheets snapshot по одному проекту всё ещё читает историю целиком; строгий memory bound, freshness barrier и пооперационный ledger записи листов не завершены.

## Инфраструктура — уже применено

`f764bcb`: сервер 2 получил отдельный WireGuard peer:

```text
API-1 10.78.0.1 ─┐
                 ├─ AI gateway 10.78.0.3:8080 → OpenRouter HTTPS
API-2 10.78.0.2 ─┘
```

- На API-2 включён `wg-quick@admirraai`, ключ генерировался локально на сервере. Private key не копировался в Git/чат.
- На gateway добавлен ровно один peer и маршрут `10.78.0.2/32`; существующий API-1 peer не менялся. Без рестарта интерфейса/nginx, изменения default route, DNS, firewall и `admirra0` (БД/Redis).
- Скрипт `ops/ai-gateway/add_api2_peer.py` проверяет адрес узла, конфликт ключа/маршрута и drift runtime/config; сохраняет исходный root-only backup и атомарно записывает конфигурацию. Повторный запуск не добавляет второй peer. После прерывания между сохранением конфигурации и применением runtime можно повторить тот же запуск; при существующем backup до записи новой конфигурации нужна ручная проверка, файл не затирается.
- Gateway backup: `/etc/wireguard/admirraai.before-api2.conf`, mode 0600. API-2 config/key: `/etc/wireguard/admirraai.conf` и `.key`, mode 0600. Эти файлы нельзя печатать в диагностике.
- Проверены enabled/active, свежие handshakes обоих peers, private health с двух узлов, OpenRouter catalog **HTTP 200 из действующего API-2 backend-контейнера**. Платные генерации в этой проверке не выполнялись.
- Повтор реального setup идемпотентен; запрещённый POST `/healthz` возвращает 403, неизвестный путь — 404. Права ключа/конфигурации API-2 проверены: 0600.
- API-1 private health и публичный сайт HTTP 200; gateway health check, nginx и внешний heartbeat active. Default routes прежние; API-2 root свободно около 19 GiB.

Это только сетевой путь. Распределение AI/SSE между API-1/API-2, конфигурация приложения и полный canary этим этапом не включены. Telegram relay по-прежнему разрешён только API-1; новый peer автоматически не получает права отправки Telegram через relay.

Механизм добавления peer без замены остальных — официальный [`wg set`](https://man7.org/linux/man-pages/man8/wg.8.html). В отличие от перезапуска интерфейса, остальные peer-сессии сохраняются.

### Откат только нового сетевого подключения

Выполнять, только убедившись, что пользовательский AI-трафик ещё не направлен через API-2. На API-2 остановить/disable **только** `wg-quick@admirraai`. На gateway удалить только API-2 public key через `wg set admirraai peer <API2_PUBLIC_KEY> remove` и маршрут `10.78.0.2/32 dev admirraai`; убрать его `[Peer]` из persistent config. Не перезапускать gateway-интерфейс, не удалять API-1 peer, не трогать `admirra0`. Исходный backup использовать после проверки, что после этой итерации не добавлялись другие peers. Private keys в командах не нужны.

## Проверки

- `11f935d`: 68 targeted tests passed. Полный штатный image-only manifest: **782 passed, 1 skipped, 1 deselected, 6 subtests passed**, 185,78 s.
- Отдельный широкодискаверный запуск по ошибке включил frontend-source assertion: 790 passed / 1 failed (frontend намеренно не входит в backend archive). Assertion проверен по локальному `Reports.vue`, правильный backend manifest прошёл. Это не скрытая ошибка production.
- `c45b407`: **784 passed, 1 skipped, 1 deselected, 6 subtests passed**, 185,27 s. Реальный synthetic PostgreSQL и Redis, internal network, без production credentials/отправок.
- Gateway: 5 новых изолированных peer tests и 8 существующих config/security tests passed. В этих тестах network/kernel commands подменены; реальный новый маршрут отдельно проверен выше.
- `a6935a2`: 58 targeted tests passed; полный manifest **788 passed, 1 skipped, 1 deselected, 48 warnings, 6 subtests passed**, 183,73 s. Image `sha256:8ec2480c2cb4a761d21aa6f0e31af435d8f8610884adc7365a7a36f68e837c10`.
- Его restore из `20260920T190219Z-a6b49102`: schema `cd9e0f1a2b3c`, migration/worker preflight/worker boot/application/read-load passed, 45 s, network=none. 40/40 HTTP 200, concurrency 4, p50 151,64 ms / p95 778,43 ms / max 939,10 ms. Только разрешённый аккаунт на восстановленной копии; providers, рассылки, банковские операции недоступны. Это не mixed-provider peak.
- `e98636a`: полный manifest **789 passed, 1 skipped, 1 deselected, 48 warnings, 6 subtests passed**, 185,98 s. Image `sha256:d27d9c89ce313503faf09c5b5720f38b1b8f8dac735afe189268c47b70739a1e`.
- Его повторный restore того же backup до `cd9e0f1a2b3c` прошёл за 45 s: миграции, preflight/boot workers, API и read-load. **40/40 HTTP 200**, concurrency 4, p50 126,23 ms / p95 675,36 ms / max 798,16 ms. Изолированные контейнеры/volume удалены; production schema/runtime не менялись.

## Следующий пакет: billing fan-out

`286b58b` (92 targeted tests passed, не production): parent `billing.maintenance` теперь планирует до 100 подписок / 200 children за страницу. `billing.warning` и `billing.recurring` имеют отдельные tenant/resource keys, не replay-safe; родитель и continuation — replay-safe. Повтор occurrence идемпотентен, children/continuation фиксируются одной транзакцией.

Children ограничены subscription ID + owner ID. Warning дополнительно сверяет зафиксированный конец периода; recurring повторно фильтрует `recurring_sync_required` / отменённое автопродление. Старше 24 часов или более чем на минуту в будущем — skip без внешнего запроса. Неподтверждённая отправка/обновление суммы не превращается в успешный child: состояние `uncertain` блокирует следующий side effect этого resource до сверки. Legacy функции сохраняют прежний общий интерфейс, пока старый scheduler не выключен.

`6d41b24`, `11d9e40`: scoped warning рассчитывает тариф именно своей подписки, освобождает SQL-сессию до SMTP и подтверждает отправку отдельной короткой транзакцией только для прежнего owner/period. Смена периода во время отправки или истечение worker lease не позволяют отметить новый период как уведомлённый. Для этого пакета добавлены pool-checkout=0 и failure-path tests; **95 targeted tests passed** (billing, durable/calendar и тарифные регрессии).

Полный manifest `11d9e40`: **803 passed, 1 skipped, 1 deselected, 48 warnings, 6 subtests passed**, 196,38 s. Image `sha256:701e2e372c55fc05dccf21d762197b055c90f08096ac9216cafc3381fac8c6b6`. Restore того же backup до `cd9e0f1a2b3c`: все migration/worker/API проверки passed, 45 s; 40/40 HTTP 200, concurrency 4, p50 115,30 ms / p95 742,70 ms / max 832,59 ms. Production не переключён.

**Граница:** этот пакет не меняет цены, суммы, правила автопродления и не выполняет реальные списания/письма в тестах. SQL/HTTP overlap recurring reconciliation и гонки отмены/смены тарифного состояния во время внешнего платёжного запроса ещё не устранены. Старый общий warning handler тоже сохранён до отключения legacy. Не считать этот fan-out полным выполнением BILL-01.

## SQL-only обслуживание VK

`9eb6015` (7 targeted tests passed; не production): новый durable handler `vk.maintenance` обрабатывает не более 100 pending/expired drafts за одну короткую SQL-транзакцию. Продолжение с keyset cursor/upper bound ставится атомарно вместе с изменениями; ошибки не скрываются успешным результатом. Идемпотентные expiry/delete сохраняют прежние сроки 7/30 дней. Никаких provider requests в этом kind нет.

Полный manifest: **807 passed, 1 skipped, 1 deselected, 48 warnings, 6 subtests passed**, 202,94 s. Image `sha256:c630532613f113d0495cf4b0a62b58bf1562e43e30899e5b6f195d36d89ede96`. Restore backup `20260920T190219Z-a6b49102` до `cd9e0f1a2b3c`: migration/worker preflight/worker boot/application/read-load passed, 47 s, network=none. **40/40 HTTP 200**, concurrency 4, p50 119,55 ms / p95 881,28 ms / max 1051,73 ms. Изолированные контейнеры и volume удалены. После проверки public HTTP 200, Prometheus 7 targets up, firing alerts отсутствуют. Production runtime/schema не переключались.

Активные интеграции исключены SQL-фильтром. `FOR UPDATE SKIP LOCKED` не мешает уже заблокированной строке OAuth callback; пропущенная запись снова рассматривается при следующем часовом occurrence. Это SQL maintenance batch, а не ложное утверждение о новом per-user внешнем API task. Старый глобальный handler не меняется до отключения legacy API scheduler.

Отдельный следующий gap обнаружен в lead notifications: `analytics_service` держит статистику в памяти API-процесса. Новый worker не получит её автоматически. Поэтому перенос daily/weekly уведомлений требует согласованного DB-backed источника/tenant scope и recipient ledger, а не простого вызова прежней функции в Celery. Пока этот пункт не закрыт.

## Standalone Метрика: не стирать прежние факты при сбое

`7e49990`: отдельное подключение Метрики использует общий строгий collector и атомарную замену окна через SAVEPOINT. Удаление старых строк происходит только после получения **всех** batches и проверки результата. Ошибка metadata, timeout второго batch, неверная дата/размер массива метрик не превращаются в успешные нули. Старые факты сохраняются даже если вызывающий код ловит исключение и коммитит другую работу. Success watermark не продвигается.

Режим «все цели» задан явно (`goal_ids=None`); пустой список у связанной рекламной интеграции не означает «включить всё». Сохранились выбор основной цели, историческое окно первого запуска и attribution lookback. Подтверждённый пустой stats response даёт реальные нули. Повтор успешного окна не удваивает данные. Исторические названия читаются до замены и берутся из последней записи.

`dbb3e96`: на самом HTTP-адаптере отклоняются неверные/внеоконные даты, нечисловые/неfinite метрики и дробные goal visits **до** группировки источников трафика. Две ошибочные величины 0,5 больше не округляются/суммируются в правдоподобный целый результат. Несколько корректных источников за один день по-прежнему суммируются. Дни без строк заполняются нулями лишь в валидном полном ответе.

Структура metadata проверяется по [официальному контракту целей Метрики](https://yandex.ru/dev/metrika/ru/management/openapi/goal/goals): список объектов, числовые ID, строковые названия; ошибка структуры не означает отсутствие целей. Провайдер в тестах заменён HTTP MockTransport/синтетическими ответами, production sync не запускался. Первый пакет: **77 targeted tests passed**, 16,74 s. Финальный `dbb3e96`: **87 targeted tests passed**, 17,01 s; полный manifest — **837 passed, 1 skipped, 1 deselected, 54 warnings, 6 subtests passed**, 202,49 s. Image `sha256:372962fb0715396a2bf74f24a37be07c6de10e4ab63ada99029bd9f7a95c1727`.

Финальный restore из `20260920T190219Z-a6b49102`: **passed**, 47 s, network=none, schema `cd9e0f1a2b3c`; migration/worker preflight/worker boot/application/read-load passed. **40/40 HTTP 200**, concurrency 4, p50 150,38 ms / p95 751,73 ms / max 896,35 ms. Это восстановленная изолированная копия, не production mixed-provider peak. Контейнеры теста и его volume удалены. Production backend/automation/frontend повторно сверены с прежними digests, таймеры backup и ingress-monitor active.

**Не закрыто этим пакетом:** SQL-соединение полного legacy sync всё ещё может удерживаться во время HTTP; нет полноценной защиты от смены настроек/владельца во время этого пути, stage coverage ledger и общего атомарного multi-channel snapshot. Поведение фильтра источников Метрики не менялось. Это частичное закрытие SYNC-02, не всего T07.

## Что осталось до полного закрытия

1. Полный fetch/apply/settings/coverage контракт sync/history; финансовый commit/IO контракт recurring reconciliation; DB-backed scoped lead notifications / prewarm; freshness barrier отчётов, ограничение ресурсов экспорта и сверка side effects. Нельзя включать весь новый календарь, объявив этот пакет завершением T07–T10.
2. Scoped provider peak runner и смешанная нагрузка с фактическими лимитами внешних вызовов. Shared files/cache revisions/upload/SSE/drain, проверка rollback совместимости старых/new job kinds.
3. Подтверждение человеком четырёх тестовых Telegram сообщений и ответственного; offline recovery key вне серверов. Вопросы владельцу заданы, ответа на момент записи нет.
4. Свежая финальная приёмка → контролируемое переключение → расширение canary → две реальные ночи наблюдения. Ночной прогон не заменяется коротким smoke.

S3/PITR остаются документированным временным исключением. Daily encrypted backup на server 2 — не независимый offsite и не HA PostgreSQL. Актуальная карта: [остаток DevOps](devops-remaining-2026-09-20.md).
