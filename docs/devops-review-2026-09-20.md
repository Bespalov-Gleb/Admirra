# DevOps review — 20.09.2026

## Вердикт и границы

**Полный cutover по master-ТЗ пока не принят.** Предыдущая короткая карта «только alerts, peak и время» не отражала незакрытые части T07–T10. Существующий ограниченный read-canary не равнозначен балансировке всех API/SSE и переносу всего календаря.

Владелец разрешил использовать свой тестовый аккаунт и выбрать проекты. Production switch должен происходить после review, приёмки и отдельно выбранного времени. Пароль аккаунта не сохраняется в Git, artifacts или evidence. Для API smoke используется локальный токен только внутри восстановленного изолированного приложения.

Пользовательские изменения MainLayout/SignIn/landing и untracked файлы не изменены и не включены в backend image.

## Исправлено при ревью

| Проблема | Исправление и проверка |
| --- | --- |
| Квота фоновых задач была по проекту, а не по аккаунту. Один владелец с множеством проектов мог занять все sync workers | `durable_sync` и `backfill_work` используют `client.owner_id`. PostgreSQL-тест: три проекта одного владельца не обходят лимит 2, другой владелец сохраняет возможность запуска; отдельно проверены goals и backfill |
| Resource observer мог вернуть `pass` при нехватке RAM, а длительность не учитывала время измерительных команд | Учитываются wall-clock deadline, expiry утверждённого scope, запас RAM ≥1536 MiB и состояние контейнеров до/после. Явное `provider_peak_accepted=false`: зелёная телеметрия не доказывает успешность бизнес-сценариев |
| Некорректные JSON-поля scope могли приводить к исключениям либо считаться подтверждением | Строгие типы approval/UUID/recipient/count; regression-тесты вложенных списков/объектов/boolean/null |
| Read-load самостоятельно выбирал владельца с наибольшим числом проектов | Только явно заданный разрешённый аккаунт; запуск запрещён вне `WW_TEST=1`, `restore-*`, локальной восстановленной БД |
| Restore smoke использовал другие DB pool limits, чем заявлено в launch budget | Workers: 2+0, API: 5+0. Это соответствие pool settings, а не утверждение об идентичности всего нагрузочного окружения production |
| Два restore drill одного backup могли столкнуться; cleanup был установлен до проверки чужих ресурсов | Уникальное имя запуска; cleanup устанавливается после conflict check. Обычный запуск не удаляет заранее существующий restore namespace |
| Общий test manifest пропускал новые cutover/heartbeat/scope/observer tests | Добавлены в image-only suite вместе с regression-тестами этого review |
| В rollback inventory отсутствовал пользовательский frontend | Добавлен и закреплён digest контейнера `admirra-frontend-1`; внутренняя админка остаётся отдельным artifact |
| Heartbeat мог быть убит systemd раньше окончания собственных retries | `TimeoutStartSec=70`, вместо 40. Максимум запросов/retry delays — 52 s без учёта прочих накладных расходов. Unit установлен на AI gateway, `Result=success`, timer active |
| SSE имел неограниченную очередь и не дожидался отмены агента при disconnect | Очередь 32 события, backpressure, heartbeat сохранён, producer/generator закрываются и ожидаются. Нет отправки `end` из cancellation-finally. Тесты медленного клиента, заполненной очереди, provider wait, нормального завершения |
| Технические исключения AI могли уходить в ответ/лог с внутренними деталями | Убрана интерполяция exception text в наружные сообщения и соответствующие error logs; используются безопасные сообщения и тип ошибки |
| Инструменты Яндекса ассистента обходили общий Redis limiter фоновой синхронизации | Все три HTTP-пути Direct JSON/Reports/Метрики используют `provider_client`. Включение по прежнему `DISTRIBUTED_RATE_LIMITS`; провайдеры, модель и цены не менялись |

Коммиты: `d766df9`, `fa437d7`, `8ca1397`, `45ef70f`.

## Незакрытые существенные findings

### R1 — AI run / quota / idempotency: P0 до полного AI rollout

`ai/assistant/router.py:chat` не вызывает `SubscriptionService.ensure_can_use_ai` / `increment_ai_usage`, в отличие от старого `ai/router.py`. `AiMessage` сохраняет сообщения, но не заменяет durable run/reservation ledger. Нет client request ID + canonical hash + атомарной reservation/settlement; повторный POST может создать новый оплачиваемый provider run. Сохранение tokens финального сообщения также не учитывает все tool-итерации как отдельный полный cost ledger.

Сделанные SSE-исправления **не закрывают** это требование. Нужен отдельный additive пакет по AI-02: ownership/права/тариф, атомарный учёт по account, replay/conflict, interrupted/uncertain outcome, учёт usage и race/failure tests. Нельзя подменять его одним увеличением счётчика после ответа или автоматическим refund при любом disconnect. Лимиты/цены продукта без отдельной необходимости не менять.

### R2 — Scoped provider peak ещё не реализован как законченный test runner

`provider_peak_scope.py` проверяет манифест, `peak_observer.py` только наблюдает. Они не ставят scoped jobs и не ограничивают фактические provider calls. Разрешённый аккаунт теперь известен: это больше не вопрос к владельцу. Следующий технический шаг — bounded launcher на восстановленной БД с проверкой принадлежности project/integration указанному owner, отключённым global scheduler и запрещёнными внешними доставками/списаниями; наблюдение всего worker set и проверка terminal outcomes.

Нельзя вызывать `work_handlers` → `nightly.enqueue`, `reports.rules`, `reports.export`, `billing.maintenance` как будто они ограничены тестовым аккаунтом: существующие обработчики обходят все подходящие записи. Night sync тестируется отдельными integration jobs, не глобальным calendar handler. Реальные AI provider tests дополнительно ограничиваются числом запросов/стоимостью.

### R3 — Границы транзакций и монолитные calendar jobs: незакрытые T03/T07/T08/T09

В `automation/sync.py:sync_integration` и `automation/backfill_work.py:execute` SQL Session/транзакции ещё соседствуют с внешними ожиданиями. Часть goals/hypotheses уже вынесена; это не полный fetch → short commit pipeline для всех платформ.

`automation/work_handlers.py` вызывает глобальные report/billing/lead passes, а `automation/sync.py:run_post_sync_reports` обходит все проекты/Sheets в одном проходе. Нужны bounded child jobs, отдельные результаты/ключи и failure acceptance. При росте аккаунтов иначе удлиняются задачи, удержание ресурсов и область частичного отказа. Зеленые boot/unit tests это не закрывают.

### R4 — Shared storage / cache / расширение ingress

Наличие adapters и тестов не означает, что все replicas уже используют общее runtime storage или что разрешена балансировка dashboard/mutations/SSE. Master-ТЗ остаётся источником межрепличной матрицы; текущие четыре read routes не расширять без соответствующей проверки файлов, прав, инвалидации и drain. Redis cache нельзя включать как универсальный переключатель ускорения.

## Что отложено по решению владельца

- Доставка alerts человеку пока не подключается. Подготовленный receiver использует Alertmanager-compatible webhook. Для Telegram нужны отдельный bot token + chat ID технической группы/ответственного и настройка Telegram receiver/relay; обычный Telegram `sendMessage` URL не является generic Alertmanager webhook. Секреты — в root-owned файлах, не в Git. После настройки проверяются `firing → resolved` и heartbeat `critical → recovery` реальным получателем.
- Пока alerts отложены, preflight **не должен** содержать выдуманное `firing_delivered=true`. Текущий cutover gate остаётся закрыт по этому пункту; unattended launch не принят.
- Offsite S3/PITR остаётся явным временным исключением, не выполненной задачей. Нужны свежий backup/restore и подтверждение независимой копии recovery key. Два runtime-хоста не заменяют offsite recovery.
- Дата/время пока не назначены; миграции production, отключение legacy и включение candidate workers не выполнялись.

## Evidence итогового candidate

Candidate source: `45ef70f`; image `admirra-devops:45ef70f`, точный Docker image ID `sha256:09413d231901fd31e0eb8b338ce11e86be19eaf0f33ae4f3cf82aa3b0f971e8d`, размер 203 380 223 bytes. Archive — 462 tracked backend/test/ops files, без dirty frontend/landing, credentials и дампов. Сборка: `/opt/admirra-staging/review-45ef70f` на server 2.

- Image-only regression manifest: **718 passed, 1 skipped, 1 deselected, 47 warnings, 6 subtests passed**, 145,07 s. Skip — optional comparison с отдельно подключаемым previous-release source; deselected — тест исходников frontend, которых намеренно нет в backend image. PostgreSQL/Redis synthetic, internal network, non-root/read-only.
- Recovery point `20260920T155915Z-e639b5d3` восстановлена в отдельной БД без внешней сети. Manifest/checksum, пять additive migrations `cc3d4e5f6a7b → bc8d9e0f1a2b`, worker preflight, manual/nightly/reports/maintenance boot, API readiness/auth guard — **passed**. До очистки ресурсов — 47 s. Production БД не мигрировалась.
- Read-load явно разрешённого аккаунта: 40 requests, concurrency 4, **40 HTTP 200**, p50 130,28 ms, p95 768,17 ms, max 890,93 ms, 2,149 s суммарно. Перед этим пять warm-up reads. Routes: auth, clients, folders, notifications, dashboard summary за последние 14 дней. Никаких provider calls, рассылок, платежей и запуска global calendar.
- Это проверка восстановленной копии и API с работающим **idle** worker set. Не real provider peak, не production latency SLO и не окончательная численная приёмка всех dashboard/project/direction consumers.
- После smoke cleanup завершился; production backend/automation сохранены на прежних digests, ingress monitor active, Prometheus alerts в контрольном снимке — 0.

Промежуточные isolated runs: `d766df9` — 707 passed; `fa437d7` — 713 passed. Каждый: 1 optional baseline comparison skipped, 1 frontend-source test deselected, 6 subtests passed. Это не live provider peak.

Production rollback tag пользовательского frontend проверен по точному digest `sha256:1b36b676b9cadca75befb5d03c66ac4c1177b0a7099e652af46360163eba4767`; working container не перезапускался.

## Очерёдность дальше

1. Закрыть AI-02 и scoped peak runner; завершить необходимые bounded handlers/transaction fixes с отказными тестами.
2. Прогнать смешанную нагрузку разрешённого аккаунта, render/AI/billing sandbox, повторный restore и rollback compatibility на точном конечном image.
3. Подключить alerts либо отдельно принять ограниченный attended-only режим; не обходить существующий gate молча. Подтвердить escrow recovery key.
4. Выбрать окно; собрать свежие evidence; выполнить single-API durable-worker cutover с admission/drain и rollback.
5. После стабильности расширять API-2 canary, проверить две ночи и финальный DoD. Массовый rollout и обещание полной готовности до этого преждевременны.
