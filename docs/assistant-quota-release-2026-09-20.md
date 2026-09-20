# Новый AI-ассистент — учёт запросов, prod hotfix

Статус: выкачен 20.09.2026 около 19:01 UTC (22:01 МСК), код `0e5f031`.

## Что изменено

- OpenRouter оплачивается владельцем сервиса, как раньше. Здесь нет нового денежного списания с карты пользователя: учитывается единица лимита его тарифа.
- До запуска модели резервируется один запрос на аккаунте владельца команды. Повтор идентичного `user + request_id` не создаёт новую генерацию; успешный ответ возвращается из БД. Другой payload с тем же ключом — HTTP 409.
- Все tool/model итерации относятся к одному продуктовому запросу. Каждый начатый вызов и возвращённый usage сохраняются отдельно. Это не обещание полной сверки суммы с инвойсом OpenRouter: при разрыве провайдер мог не вернуть usage.
- Ошибка до первого вызова провайдера возвращает резерв ровно один раз. После начала вызова при неопределённом исходе автоматического refund/повторной генерации нет. Потраченная единица остаётся; это консервативная политика до отдельного reconciliation.
- Максимум три одновременных запроса на аккаунт, один на диалог; deadline 15 минут. Истёкшие записи восстанавливаются при следующем запросе. Лимиты тарифов, модель, провайдер и цены не изменены; существующий admin bypass сохранён.
- Фронт сохраняет ID незавершённой отправки в sessionStorage без текста вопроса; обновление access token не меняет ключ. После завершения обновляется счётчик в хедере. Старой вкладке без request_id API отдаёт 428 с просьбой обновить страницу.
- Включены ранее проверенные bounded SSE queue/cancellation и безопасные сообщения об ошибках. Большой пакет runtime/worker изменений не включён.

## Проверки

1. Полный isolated candidate `admirra-devops:0e5f031` на server 2: **735 passed, 1 skipped, 1 deselected, 6 subtests**, 160,80 s. Это candidate suite, не deployed runtime.
2. Отдельный тестовый derivative точного prod-base hotfix на server 1: **68 passed, 6 subtests**, 20,64 s. Synthetic PostgreSQL/Redis, internal network, no production credentials/source bind. Проверены гонки последнего слота, replay/conflict, команда/владелец, refund/unknown, смена периода, HTTP и SSE, файлы, тарифные guards. Изначально ошибочно включённый VK regression не собрался: `vk_reporting` отсутствует в прежнем prod-base. Его не добавляли в этот hotfix; полный candidate suite его проверяет отдельно.
3. Frontend из чистого Git archive, не dirty working tree: `npm run build` успешен, два Node-теста request identity успешны. Внешний вид не менялся; отдельная визуальная приёмка не выполнялась.
4. Публичный prod API, разрешённый тестовый аккаунт: первый запрос **200**, ответ сохранён, **1 provider call / 1 usage entry**; идентичный повтор **200 replay**, provider_calls/usage не изменились; другой текст с тем же ID **409**; запрос без авторизации **401**.
5. У тестового аккаунта admin bypass, поэтому live delta квоты **0**; replay delta также **0**. Обычная квота +1 и защита её последнего слота проверены PostgreSQL regression-тестами, не выдаются за live-тест обычного пользователя.
6. Корень сайта и новый ассистентский JS — **200**. Backend/front containers running, automation image не изменился; env/port bindings/mounts сравнены автоматически до/после и совпадают.
7. Обновлённые rollback inventory/template: **25 cutover-preflight tests passed**, изолированный image на server 2. Ingress monitor timer active, последний Result=success; новые rollback tags повторно сверены по Image ID.

## Runtime и миграция

- Backend: `admirra-backend:quota-0e5f031`, `sha256:6321c5fb910e9f8e4ff942deffd6bbe63d6285efd05b35b670a192ce780d365d`.
- Frontend: `admirra-frontend:quota-0e5f031`, `sha256:680b8893a1dcfa00460d0c2f591b5e7cb415d047cd9780d566535e6419a04af1`.
- Backend построен поверх предыдущего exact production image; заменены только runs/router/llm/agent/streaming, SubscriptionService и additive migration helper. Frontend — поверх старого image с сохранением public files/старых hashed assets для открытых вкладок.
- `ops.migrate_assistant_runs` добавил одну таблицу с unique user/request, FK и индексами; ограничение lock wait 5 s. **Alembic остаётся `cc3d4e5f6a7b`**. Полная будущая цепочка завершится `cd9e0f1a2b3c`, adoption существующей таблицы повторяемый.
- `/root/Admirra` не подвергался общему pull/build/up: его git hash не является идентификатором текущего overlay. Перед следующим deploy использовать фактические `.Image` и literal compose, не только git HEAD/root .env.
- API-2 canary, automation, цены, ключи и банк не переключались. Yandex shared limiter из полного DevOps candidate этим overlay не выкачивался.

## Backup и rollback

- Fresh pre-rollout encrypted backup: `20260920T185341Z-8636aed0`, schema `cc3d4e5f6a7b`, service success. Предыдущий restore drill описан в DevOps review; свежий backup здесь не выдаётся за заново восстановленный.
- Captured root-only конфигурации: `/root/admirra-assistant-quota/20260920T190057Z/{backend,frontend}-{previous,active}.json`. Копия включена в runtime backup через `/etc/admirra/releases/assistant-quota-20260920T190057Z`; файлы содержат секреты, не публиковать.
- Post-rollout backup с ledger и сохранёнными конфигурациями: `20260920T190219Z-a6b49102`, service success. Новый restore drill этой recovery point пока не проводился.
- Откат: каждый `*-previous.json` запускать через `docker compose -p admirra --project-directory /root/Admirra -f <file> up -d --no-deps --no-build --pull never <service>`; затем проверить readiness/public HTTP. Не удалять ledger и не повторять автоматически interrupted/uncertain AI runs. Большая DevOps-миграция для отката не нужна.
- Старые pre-cutover images не удалены. Дополнительно закреплены новые `admirra-rollback/{backend,frontend}:quota-0e5f031` для будущего cutover.

## Что это не закрывает

Полный двухсерверный cutover, provider peak acceptance, транзакционные/глобальные scheduler handlers, alert delivery человеку, offsite/PITR и полный provider-cost reconciliation остаются отдельными задачами. Их статус нельзя повышать на основании этого узкого hotfix.
