# Проектный приём заявок и durable exports — candidate 23.09.2026

Статус: **локальный opt-in candidate, не production**. Этот пакет не выключает
Lead Validator. Старый production path остаётся при `LEAD_DELIVERY_GUARDS=false`.
Бот регистраций AdMirra и рекламные лиды дашбордов не изменены.

## Реализованный контракт

- `POST /api/webhook/phone/{project_id}` при включённом guard требует секрет
  конкретного активного проекта независимо от legacy secret-check flag.
- До provider calls создаются `Lead(PENDING)` и `LeadIntake(processing)`.
  Ранние отказы CAPTCHA/headers/antibot/data quality/DaData/spam/UTM сохраняются,
  возвращают lead_id и не теряются из статистики качества. PENDING не является
  ни валидной заявкой, ни отказом.
- SQL snapshot → provider IO без удержания SQL → повторная проверка owner,
  active project, linked client, settings digest и 5-минутного deadline.
  Обогащение и скоринг также выполняются вне SQL. MX DNS у guarded path вынесен
  из event loop в thread.
- Проектная CAPTCHA использует только выбранный provider/key проекта. Нет
  fallback на общий секрет. Ошибка конфигурации/transport/malformed response —
  503, а не отрицательное решение о качестве контакта.
- Общий Redis Lua limiter: owner 60/min, 1000/hour; global 600/min по умолчанию.
  Параметры `LEAD_INTAKE_PER_MINUTE`, `LEAD_INTAKE_PER_HOUR`,
  `LEAD_INTAKE_GLOBAL_PER_MINUTE`; лимит 429 с Retry-After, отказ Redis 503.
  Обе API должны использовать один исправный Redis, `REDIS_ENABLED=true`.
- `Idempotency-Key` 1–200 символов. Тот же key + тот же payload возвращает
  сохранённый результат; другой payload — 409. Без header используется HMAC
  нормализованного содержимого. Серверный client_ip не участвует в digest;
  исходное тело формы участвует. Для двух **новых** событий с одинаковым телом
  отправитель обязан передать разные event keys. Автоматического TTL/replay нет.
  При ротации SECRET_KEY необходим план миграции ключей ledger: менять его
  вместе с этим rollout нельзя.
- Финальный dedup phone/email — project-scoped SQL под блокировкой проекта;
  применяется к ранее VALID/non-spam контактам в PHONE_DUPLICATE_TTL_SEC.
  Проверяется текущий placement blacklist; ручное изменение статуса PENDING
  не перезаписывается поздним результатом валидации.
- Решение, результат idempotency и все recipient jobs коммитятся атомарно.
  Queue payload: только IDs, channel и digest, без телефона/email/секретов.
- Один `lead.export` на lead/channel, `replay_safe=false`, одна попытка.
  `lead_export_receipts(sending)` коммитится до отправки. Внешний вызов не
  держит SQL; после ответа заново проверяются lease и актуальный scope/body.
- Успех отмечает exported flag и receipt атомарно. Timeout, потеря ответа,
  partial acceptance и смена scope после отправки не приводят к blind resend.
  Подтверждённый receipt восстанавливает succeeded после потери worker ACK,
  не повторяя внешнюю отправку. Completed lead.export не удаляются общим prune
  до отдельной политики хранения evidence.
- CRM: HTTPS/443, без credentials в URL и redirects, public DNS/IP checks,
  соединение с проверенным IP, TLS SNI/certificate по исходному hostname.
  Служебные/private/mixed DNS destinations запрещены. Отправка в thread.
- SMTP: результат из thread сохраняет delivery evidence. Отказ части адресатов
  не трактуется как полный успех и не повторяет письмо всем адресатам.
- Telegram: только chat_id проекта, plain text и ограниченные поля.
- Метрика: одна однозначная active Direct integration связанного client,
  один явный counter и её OAuth token; общего token/counter fallback нет.
  Нужен реальный ym_uid. Две существующие цели передаются одним CSV upload;
  receipt хранит uploading.id при подтверждении обеих строк. Это подтверждение
  **приёма файла**, не доказательство сопоставления с визитами.
  [Контракт API Метрики](https://yandex.ru/dev/metrika/ru/management/openapi/offline_conversions/upload_1).

## Схема, rollout и read-only диагностика

Новый additive head `f57a8192a3b4`, parent `f46f708192a3`: lead_intakes,
lead_export_receipts, индексы project/phone/date и project/lower(email)/date.
Downgrade не удаляет evidence. Перед реальным применением нужны оценка размеров
leads/блокировок индексов, backup/restore и проверка final artifact.

Worker/API preflight требует обе таблицы при включённом флаге и запрещает
выключение с unresolved intake/export. Guard требует DURABLE_TASKS.
Сначала согласованно обновить схему, API и workers, затем включать intake;
старую реплику нельзя оставить принимать те же вебхуки по legacy path.

Read-only операторская проверка (без контактных данных/секретов, limit 1–200):

```sh
python -m ops.lead_status --limit 50
python -m ops.lead_status --owner-id <UUID> --limit 50
```

Состояния processing/held и sending/uncertain не разрешают повторить запрос.
Не переводить jobs обратно в queued вручную. Не удалять записи для «сброса».

## Незакрытые границы — обязательны до включения в production

1. Legacy `/lead/`, `/webhook/tilda/`, `/webhook/marquiz/` без project binding
   ещё не переведены. Нужен inventory действующих URL и миграция на signed
   project endpoint без отключения модуля/потери заявок.
2. `enable_bitrix_check=true` на guarded intake пока даёт явный 409:
   существующий global Bitrix нельзя использовать между владельцами.
   Нужна проектная credential binding и проверка совместимости.
3. После прерванной validation сохраняется PENDING/processing; после истечения
   deadline тот же key не запускает её повторно. Read-only evidence готова,
   но операторское завершение/reconciliation, audit trail, UI pending/uncertain,
   retention и alerts по зависшим admissions ещё нужны.
4. Business/provider sandbox acceptance (включая доступы Метрики/SMTP/CRM),
   оценка admission limits и mixed-load на окончательном артефакте.
5. Общие AI/report/billing SQL-over-IO, двухсерверная приёмка, restore/load,
   operator cutover из основного плана этим пакетом не закрываются.

Ни production env, ни реальные кабинеты/рассылки в ходе этих тестов не менялись.

## Проверки

Тесты `test_lead_intake.py` / `test_lead_export_work.py`: настоящий изолированный
PostgreSQL/Redis, синтетические владельцы, mocked external providers. Проверяются
идемпотентность/конкурентность, early rejection, atomic rollback, scoped dedup,
получатели/lease, отсутствие SQL при IO, receipt replay, SMTP partial rejection,
SSRF/DNS pinning, проектные CAPTCHA/Мetрика, миграция/preflight и redacted status.
Финальный прогон: **228 passed, 29 warnings, 132.41s**, exit 0. Вместе с новыми
тестами проверены lead diagnostics/placements/scoped stats/alerts, durable ledger,
runtime roles/API boot, provider transport, reports final и worker pool lifecycle.
Первый расширенный прогон выявил ошибку синтетической фикстуры SocialCheckResult
(не передан обязательный phone); фикстура исправлена, финальный набор повторён.
`git diff --check` и компиляция изменённых Python-модулей также прошли.

Тестовый image `admirra-devops:3d65ef3`, исходники candidate смонтированы read-only;
`WW_TEST=1`, отдельные schemas, internal Docker network без внешних API. Это
targeted regression, **не** общая mixed-load/restore/sandbox приёмка production.
