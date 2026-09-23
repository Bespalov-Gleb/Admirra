# Lead Validator: ограниченная диагностика

Candidate, 23.09.2026. **Production не менялся.** Модуль остаётся в scope релиза
по уточнённому решению владельца; это не его отключение и не завершение всего модуля.

## Изменения

- `/lead/test-telegram`, `/lead/test-captcha-api`, `/lead/test-metrica` требуют
  внутреннего superadmin и явного JWT audience `internal_admin`; обычный токен
  основного приложения не подходит, в том числе у пользователя с ролью superadmin.
  Используются существующие проверки activity/staff status/internal admin enabled.
- Общие probes только читают состояние провайдера. Telegram делает `getMe`,
  **не** отправляет тестовое сообщение. Ответы не содержат token preview, raw
  provider body, exception text, списка клиентских счётчиков/капч или их ключей.
  Нет перезагрузки `.env` во время HTTP-запроса.
- `check-phone` и `test-validate` остаются доступны подтверждённому пользователю.
  `test-validate` — dry-run, не запись заявки/отправка: нет Telegram, CRM,
  чтения общего dedup-кэша, mark_phone/email. Без проекта дополнительные social
  проверки выключены; при явном проекте проверяются owner/activity и связанный
  Client (тот же owner, ACTIVE) **до** обращения к Redis/провайдерам.
- Общий legacy Bitrix из диагностики не вызывается: он не привязан к tenant.
  Проверка через клиентскую CRM требует отдельного scoped binding, это не
  предположение, что общий Bitrix принадлежит каждому пользователю.
- SQL-сессия auth/scope освобождается перед Redis и внешними проверками;
  передаются только identity/settings snapshot. Ограничены длины phone/email/name,
  некорректный нормализованный телефон не вызывает DaData. Ошибки social provider
  не возвращаются наружу в исходном виде.
- Один атомарный Redis Lua reservation на обе API-реплики: 10 запросов/60 секунд,
  100/24 часа на пользователя и 60/60 секунд на все диагностические endpoints.
  Окна начинаются с первого запроса, это не календарные сутки. Исчерпание — 429
  с Retry-After по TTL исчерпанных квот. Нет частичного расхода квот при отказе.
  Redis unavailable/timeout (2 секунды) — 503 и **ни одного** provider call.
  Ключи содержат UUID, а не телефоны/email; старые dedup-ключи не меняются.
- PhoneAPI явно обозначает dry-run без сохранения/уведомлений. 429/503 и другие
  transport errors — «Проверка не выполнена», а не «Лид отклонён». Ошибка любого
  провайдера в dry-run также не записывается в историю как отклонённая заявка.
  Retry-After показан в минутах, raw error/URL не выводятся; защита двойного
  submit и snapshot режима сохраняются до завершения запроса. Сбой localStorage
  не превращает успешную проверку в предложение повторить внешний запрос.

## Проверки

На изолированных PostgreSQL/Redis (internal network, synthetic accounts,
`WW_TEST=1`) промежуточный пакет: **56 passed, 27 warnings**, 44,93 с.
Включены HTTP через реальные auth dependencies, scope/ownership, SQL pool release,
provider errors без секретов, отсутствие отправок и записей, 20 конкурентных
Redis reservations, TTL/суточные/global лимиты, прежние scoped stats/placements,
API role boot.

**Финальный расширенный backend прогон:** 122 passed, 27 warnings, 79,62 с;
добавлены прежние lead alert/durable work/runtime/worker-pool проверки. Lua с
точным Retry-After протестирован на реальном изолированном Redis. Frontend:
4 unit/compile tests passed; Vite build passed. Визуальная браузерная приёмка
не выполнялась; полный regression manifest и нагрузка продукта остаются отдельно.

Первый прогон: 46 passed, 10 failed — исправлен synthetic fixture (verified email),
уточнён 401/403 contract и добавлена явная проверка admin audience, т.к. проверка
JWT audience библиотекой сама по себе разрешает отсутствие claim. Auth-проверки
в тестах не подменялись. Внешние HTTP полностью заменены тестовым transport.

## Включение и оставшееся

Новых миграций/feature flags нет. Перед релизом `REDIS_ENABLED=true`, обе API
используют один Redis/database; иначе диагностика намеренно возвращает 503.
Обновить обе API согласованно: старые endpoints не должны оставаться доступными
через соседнюю реплику. Откат возвращает прежние ограничения безопасности, поэтому
старые диагностические endpoints нельзя открывать без эквивалентной защиты.

**Не закрыто этим пакетом:** реальные `/lead/` и webhook validation/приём,
сохранение ранних отказов, project CAPTCHA, owner-scoped дедупликация,
immediate exports/receipts/CRM URL validation, страницы списков без ограничения,
interactive AI/report, billing offline conversion, общая нагрузка и cutover.
Лимитер здесь защищает диагностику, не весь lead ingestion. Регистрационный бот,
OAuth-телефоны, рекламные лиды и production env не менялись.
