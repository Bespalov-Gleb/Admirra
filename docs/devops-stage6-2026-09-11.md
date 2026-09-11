# Этап 6A — долговечные ссылки на HTML-отчёты

Дата: 11.09.2026. Продолжение [полного ТЗ](admirra_devops_completion_tz_2026-09-11.md), пакет T02 / FILE-03. Это **часть** общего файлового этапа, не завершение всех FILE-требований.

## Границы

Сделано в коде и проверено на изолированном PostgreSQL сервера 2. Working production API/БД/расписания/отправки не переключались, новая миграция на production не применялась. Внешние AI/почта/MAX/Telegram/платежи в тестах не вызываются.

В этом пакете меняется хранение **снимка HTML-отчёта и bearer-ссылки**, а не PDF/PNG/DOCX, аватаров и всего uploads. JSON-снимки небольшие и хранятся в PostgreSQL; бинарные файлы не переносятся в БД. Приватный файловый API / storage adapter будет следующим отдельным пакетом.

## Что реализовано

- `backend_api/reports/public_links.py`: PostgreSQL `public_report_links` вместо process-local словаря для нового режима создания HTML-ссылок.
- Новая ссылка содержит `r1_` и 32 случайных байта в URL-safe записи. В БД хранится только SHA-256 токена; исходный bearer возвращается один раз при создании. Listing не раскрывает токены, их hashes или содержимое снимка.
- Сохраняются creator/account, точный набор проектов, JSON-снимок, hash/byte length, created/expires/revoked timestamps. Снимок не пересчитывается при открытии.
- JSON сохраняется как TEXT с проверкой валидности/типа на стороне PostgreSQL. Это намеренно: JSONB меняет запись отрицательного нуля/экспонент, а hash должен подтверждать точные байты сохранённого снимка. Размер ограничен 1 MiB, NaN/Infinity не допускаются.
- Срок: 1–86400 секунд, текущий HTTP endpoint сохраняет прежние 24 часа. Время берётся из PostgreSQL, не из часов отдельного API.
- Максимум 100 активных и 200 созданных за скользящие сутки ссылок на создателя. PostgreSQL transaction advisory lock защищает проверку лимита от гонки нескольких API. Отзыв не обходит суточный лимит.
- Capability возвращается только после успешного commit. Ошибка хранилища — 503, не фальшивый 404, не успешная ссылка на process-local fallback.
- Public read повторно проверяет активность создателя и его аккаунта, текущий account context и доступ ко **всем** проектам снимка. Потеря доступа к одному проекту, удаление проекта, блокировка или переход в другой аккаунт закрывают ссылку целиком. Права не берутся из Redis/JWT-снимка.
- Неверная/истёкшая/отозванная/чужая ссылка даёт одинаковый публичный 404 без раскрытия причины или metadata. Ошибка целостности даёт 503 без выдачи повреждённых данных.
- HTML/link responses имеют no-store/private, no-referrer, noindex и CSP без скриптов/внешних источников. Используется прежний HTML-renderer с экранированием комментария; формулы/НДС/модель AI не менялись.
- Синхронные SQL и HTML rendering в этих endpoints переведены в обычные FastAPI `def` handlers, чтобы они выполнялись в threadpool, не напрямую в event loop. Это не общий рефакторинг всех report endpoints/транзакций.

## HTTP-контракты

### Создание

Существующий `POST /api/reports/link`, авторизация прежняя. При включённом новом режиме старые поля сохранены, добавлены `link_id` и `expires_at`:

```json
{
  "url": "/api/reports/view/<одноразово возвращённый bearer>",
  "token": "<тот же bearer>",
  "link_id": "<uuid записи, не публичный токен>",
  "expires_at": "<ISO timestamp>"
}
```

Комментарий берётся уже готовый из запроса; платная LLM-генерация для создания ссылки не добавляется. 429 означает лимит ссылок, 400 — некорректные данные/размер, 403 — недоступный scope, 503 — недоступное хранилище. Фактический snapshot scope возвращается из того же `_get_report_data`, который агрегировал отчёт, а не пересобирается позже по изменившемуся составу проектов.

### Управление

- `GET /api/reports/links?limit=50&before=<link_id>`: только свои ID/timestamps, новые записи первыми. Размер страницы до 100. Cursor чужого владельца — 404; bearer не восстанавливается из listing.
- `DELETE /api/reports/links/{link_id}`: только создатель, идемпотентный отзыв, 204. Ссылка с чужим ID — 404. Даже при потере доступа к проекту создатель может отозвать ранее созданную ссылку.
- UI управления ссылками в этом пакете не добавлен. Авторизованные API endpoints доступны для будущего интерфейса/операционной работы; проверены HTTP-тестами.

### Чтение

`GET /api/reports/view/r1_…` всегда использует PostgreSQL, даже если создание новых durable-ссылок временно выключено. Никогда не пытается найти такой token в legacy-словаре. В обоих случаях успешные данные и ошибки private/no-store.

## Миграция и флаги

Новая additive migration `ab7c8d9e0f1a_durable_public_report_links.py`, parent `ff6a7b8c9d0e`. Prepared worker-compose ожидает новый head. Действующие контейнеры этим файлом не менялись.

```text
DURABLE_REPORT_LINKS=false
LEGACY_REPORT_LINK_READS=true
```

Это defaults совместимости, не финальный multi-API режим.

- `DURABLE_REPORT_LINKS=true` включает только создание новых долговечных HTML-ссылок. На startup выполняется read-only проверка существования нужной таблицы/полей; автоматического DDL нет. Перед включением нужны миграция, DB-права и безопасное логирование ingress.
- `LEGACY_REPORT_LINK_READS=true` разрешает старые `/view` и `/file` ссылки из локального словаря. Это временная совместимость одного API, **не** решение балансировки.
- `LEGACY_REPORT_LINK_READS=false` отключает чтение старых process-local HTML/file токенов. Не включать до истечения/переноса/переиздания старых ссылок и решения судьбы legacy файлов.
- После отключения создания durable-ссылок чтение/list/revoke уже созданных продолжают работать, пока таблица существует. Откат на более старый код, который не знает `r1_`, этих гарантий не имеет.
- Если оба флага `false`, новое создание отвечает 503 до расчёта отчёта. Это режим паузы, а не возврат успешной, но неоткрываемой legacy-ссылки. Существующие durable-ссылки читаются и отзываются как прежде.
- Downgrade запрещён при активных durable-ссылках. Перед допустимым downgrade остановить все producers, дождаться expiry/отозвать, сохранить нужный evidence. Проверка миграции не заменяет остановку конкурентных записей.

### Legacy-ссылки: не потерять при реальном переключении

Этот пакет **не экспортирует словари уже работающего старого процесса**. Просто перезапустить его — значит потерять его in-memory ссылки, как и раньше. Перед production release нужен выбранный вариант из FILE-03: закрытый перенос живого состояния с проверкой scope/владельца либо сохранение прежнего read route до максимального TTL и переиздание. Старый формат словаря не хранит creator/scope; нельзя автоматически приписать всем ссылкам произвольного владельца. Уже потерянный в памяти token этот пакет не восстановит.

## Логирование публичных токенов

`core/public_url_logging.py` устанавливает фильтры на `api`, `uvicorn.access`, `uvicorn.error`: скрываются bearer-сегменты report view/file/public delivery paths и новые `r1_` tokens. Типы аргументов Uvicorn AccessFormatter сохранены.

Это **не** настройка внешнего nginx и не универсальное удаление секретов из всех логгеров. До включения на production нужно проверить host nginx access/error logs, промежуточный proxy, telemetry и правила query/body logging. Его конфигурация в этом пакете не менялась. Не запускать feature публично, пока ingress продолжает записывать полные capability URLs. Ошибки новых DB-операций не логируются с SQL parameters/snapshot или traceback, публичный ответ также обезличен.

## Retention и операционная диагностика

Новый `python -m ops.public_report_links` — read-only aggregate count активных ссылок, без tokens/содержимого/имён клиентов. Только внутри правильного container/environment после migration.

`python -m ops.public_report_links --prune --limit 100` — явная одна ограниченная delete-транзакция; удаляются только snapshots, истёкшие либо отозванные более 7 суток назад. `FOR UPDATE SKIP LOCKED` допускает параллельные maintenance workers. Рабочие ссылки, report deliveries, jobs и платёжные ledgers не затрагиваются. Максимальный batch — 1000.

Автоматическое расписание cleanup ещё не включено; подключить к выделенной maintenance-роли после общей карты календаря. Перед массовым включением учитывать storage budget: 100 active × 1 MiB на создателя — верхняя защитная граница, а не типичный размер. По реальным размерам пересмотреть более строгий лимит/retention при необходимости.

## Приёмка

Новые тесты `tests/test_public_report_links.py` используют изолированный настоящий PostgreSQL, реальные FK/constraints и авторизацию проекта/команды:

- независимые соединения и два свежих Python-процесса читают тот же snapshot без словаря;
- scope снимка возвращается из той же агрегации (обычный и folder режимы); прежние callers получают исходный шестипольный результат;
- два экземпляра FastAPI: create на первом, view/revoke на втором; читается и после выключения флага создания;
- token hash вместо plaintext в DB/list, TTL/invalid/revoke, quota race и запрет обхода через revoke;
- rollback/failed commit не возвращает успешную ссылку;
- отзыв project share/membership, смена account, блокировки и удаление creator/project закрывают публичный доступ;
- JSON bounds, Decimal/date, exponent/negative zero, corruption detection;
- paginated owner-only listing, bounded retention, downgrade guard и повторная upgrade;
- 503 при DB outage, private headers, HTML escaping и redaction Uvicorn/application records.

Это не двуххостовый production LB-test и не весь FILE acceptance. Часть HTTP-данных строится из synthetic fixtures без обращения к внешним рекламным API; реальный stats correctness остаётся в отдельном существующем regression suite/пакете DATA.

### Результат source-проверки

Штатный backend-набор на изолированном PostgreSQL/Redis: **318 passed, 1 skipped, 1 deselected**, 47 warnings, 52,11 s. После этого добавлены ещё два теста точного scope, которые также войдут в финальную проверку образа.

Skipped — optional differential comparison с предыдущим release, проверявшийся на этапе 4. Deselected — проверка Vue-файла, который намеренно не входит в backend-артефакт. Дополнительный запуск автоматического discovery дал 335 passed / 1 skipped и один `FileNotFoundError` именно этого Vue-файла; это не объявляется зелёным полным прогоном. Штатный список и его прежнее исключение frontend-проверки не расширялись ради скрытия ошибки.

Контроль production в 18:12 МСК: HEAD `cdf0a4d`, прежние backend/automation/frontend/admin_frontend/db running, DB healthy, приватный gateway работает; публичная главная отвечает HTTP 200. Перезапусков или SQL migrations на production в этом пакете не было.

### Проверка итогового образа

Код пакета закоммичен: `90cb658`. Артефакт получен через `python3 -m ops.package_backend … --revision 90cb658` из этого коммита, а не из оставшихся пользовательских изменений. 321 разрешённый backend/runtime/test файл.

На сервере 2 собран `admirra-devops:90cb658`, OCI revision `90cb658`, image ID:

```text
sha256:f07b563386a69e6c397559ff26503d9723c175e1d575250849e63a512522860b
```

Комбинация `compose.isolated.yml` + `compose.artifact-tests.yml` удаляет source bind; фактический `docker inspect` тестового контейнера подтвердил `Mounts: []`. Полный штатный прогон **из образа**: **320 passed, 1 skipped, 1 deselected**, 47 warnings, 59,35 s. Включает 29 новых сценариев этого пакета. Дополнительно отдельно проверен HTTP rollback/pause: оба флага false → 503 на создание, existing durable view/revoke доступны.

`pip check` — конфликтов нет. Проверены отсутствующие `/app/.env`, `/app/.git`, `/app/uploads`, `/app/admin-panel-vue-main`, `/app/landing`. Проверки запущены non-root, read-only, без production credentials; test network internal, синтетическая БД/Redis отдельно от действующих сервисов.

Новый образ **не установлен** как production backend/automation. Remote ветка повторно сверена: `cdf0a4d`; коммиты текущего пакета локальные, push не выполнялся. Рабочие Redis/gateway сохраняют конфигурацию предыдущего инфраструктурного этапа.

После приёмки остановлен и удалён только Compose-проект `admirra-devops-test` (его синтетические tmpfs PostgreSQL/Redis и internal network). На сервере 2 остались `admirra-workers-broker-1` и `admirra-workers-cache-1`, оба healthy. Их данные/тома не удалялись; новые workers/расписания/API там не запускались.

Финальная read-only проверка 11.09.2026, 23:00 МСК: production HEAD `cdf0a4d`, прежние пять сервисов и приватный gateway running, DB healthy, `https://admirra.ru/` → HTTP 200. SSH ControlMaster сервера 2 после работы закрыт.

## Что ещё остаётся по T02 / FILE

1. Shared binary storage adapter/private file API на имеющихся узлах либо предоставленное хранилище.
2. PDF/PNG/DOCX artifacts, аватары/uploads/rejected leads: producers/consumers/GC/checksums/retention/migration.
3. Общий pipeline immutable snapshot → render → artifact → recipient send, включая существующий DB-backed public delivery PDF.
4. Production-стратегия старых in-memory ссылок, ingress token redaction и ограничение публичных запросов.
5. Backup consistency, restore drill, межхостовый API-1/API-2/worker тест и затем безопасное включение.

Основной сайт не получает ускорение или новый режим ссылок от одного коммита: feature defaults выключены и migrations на production не применялись.
