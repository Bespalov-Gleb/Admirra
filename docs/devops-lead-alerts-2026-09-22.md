# Уведомления о качестве лидов: DB-backed scoped calendar

Candidate `5a11114` + `f1bfefa`, 22.09.2026. **Не включён в production.** Новая схема `de0f1a2b3c4d`; действующая production-схема не менялась.

## Что изменено

- `lead.daily` и `lead.weekly` теперь только планируют: страницы максимум по 100 активных `PhoneProject` с заданным Telegram-получателем, UUID cursor/upper bound, атомарные children + continuation. Повтор страницы не создаёт повторную рассылку. Час и timezone расписания сохранены.
- Дочерние `lead.daily.project` / `lead.weekly.project` привязаны к owner, phone project, получателю и календарному моменту. При отправке проверяются authoritative job payload/kind/tenant/resource и действующий lease. Смена владельца, связанного клиента, активности или чата требует новой задачи, а не автоматической перепривязки.
- Источник — таблица `leads`, не память API/worker. Данные других проектов не учитываются. Период полуоткрытый `[scheduled_at − days, scheduled_at)`, weekly — семь дней, daily — `ALERT_LOOKBACK_DAYS`. Незавершённые `PENDING` не входят в знаменатель. Отклонение — `INVALID` / `SPAM` или `is_spam`; иначе завершённый `VALID` считается прошедшим проверку.
- Пустые и отсутствующие UTM одинаково нормализуются в `direct` / `none`: это один источник, а не две группы, каждая из которых может оказаться ниже минимального числа заявок. Отдельная regression добавлена в `f1bfefa`.
- Итоги и до 10 худших источников агрегируются SQL; не загружаются телефоны, email, форма или все лиды в память. В тексте явно указаны порог, минимум заявок, границы UTC и ограничение списка. Пустой период и daily без плохих источников не отправляются; healthy weekly содержит общие итоги.
- Используется только `PhoneProject.telegram_chat_id`, без fallback на общий чат. У проекта один такой получатель — отдельная child/receipt на него. Передача в Telegram — plain text с ограничением длины; UTM не интерпретируется как Markdown. Бот должен быть настроен и включён.
- SQL закрывается до HTTP. Короткая fenced-транзакция сохраняет намерение `sending`, затем внешний вызов и отдельная fenced-транзакция подтверждения. Миграция добавляет `lead_alert_deliveries`: hashes scope/body, состояние и timestamps. Исходный текст, chat ID, токен и личные данные в receipt/queue не пишутся.
- `sent` означает **Telegram API подтвердил принятие**, не прочтение человеком. Повтор уже подтверждённой задачи не отправляет сообщение снова. Timeout/read error/5xx/malformed success оставляют неизвестный исход; generic ledger помечает `uncertain` и блокирует ресурс проекта для следующих daily/weekly до сверки. Потеря lease после запроса также не разрешает повтор.
- Доказанный отказ до отправки/4xx/connect error помечается `rejected`/failed. `send_message` теперь передаёт транспортный исход через task-local context; response body/URL с токеном не выводятся в новых error logs.
- Worker startup отказывает при queued/running/uncertain старых глобальных lead jobs с `replay_safe=false`. Их надо сверить, а не преобразовать в новый planner автоматически. Миграция намеренно не удаляет receipts при application rollback; возврат старого scheduler к новой очереди запрещён.

## Границы

Это исправление **периодических quality notifications**, а не всей телефонии. Немедленный экспорт отдельного лида в CRM/email/Telegram, публичные legacy analytics endpoints и глобальный placement blacklist не переписаны. Новый durable путь не вызывает глобальную автоматическую блокировку площадок по смешанной статистике разных проектов. Для неё нужна отдельная tenant-scoped политика.

Авторизация получателя фиксируется в короткой транзакции перед HTTP. Настройки, изменённые уже во время сетевого запроса, не могут отозвать сообщение у Telegram; обработчик оставляет случай на сверку вместо ложного подтверждения. Операторская/UI-сверка неизвестных исходов остаётся общим открытым пунктом. Это не обещание exactly-once внешней доставки.

## Проверки

Targeted PostgreSQL/transport/calendar regression: **111 passed, 1 deselected**, 53,49 с. Проверены границы периода, изоляция проектов, pending/valid/rejected, bounded paging/rollback/dedupe, top-10/Unicode/plain text, scope/recipient/owner/lease drift, подтверждённый повтор, uncertain/no-repeat, transport outcomes, отсутствие занятого SQL-соединения во время отправки и запрет старого глобального planner.

Первый targeted run дал 99 passed и один packaging failure: frontend-source assertion запустили в backend-only artifact. Повтор исключает именно этот frontend test, как и основной manifest; ошибка не выдаётся за функциональный дефект/исправление backend. Реальные Telegram, SMTP, платежи и рекламные API в тестах не вызываются.

Полный manifest первого Git-артефакта `5a11114`: **1035 passed, 1 skipped, 1 deselected, 96 warnings, 6 subtests passed**, 379,28 с. Image `admirra-devops:5a11114`, digest `sha256:ae5541ed498aa0d5922fc1107dfc29ae0cbfc02197e4f7ae777b19167e20a1a8`. Изолированные PostgreSQL/Redis, internal network, без production credentials; 506 файлов clean Git package, без frontend/secrets/uploads/dumps. Optional previous-release comparison пропущен; frontend-source assertion исключён штатно. К предыдущему manifest добавлены 34 тестовых случая.

Backup `20260922T044425Z-8fcea122` восстановлен первым образом `5a11114`: 48 с, network=none, миграции до `de0f1a2b3c4d`, worker preflight/boot всех четырёх групп и API smoke passed. 40/40 HTTP 200 при concurrency 4; p50 115,54 мс, p95 728,21 мс, max 818,60 мс. Это чтение восстановленного snapshot при idle workers, не peak/provider acceptance.

Финальный Git-артефакт `f1bfefa`: **1036 passed, 1 skipped, 1 deselected, 96 warnings, 6 subtests passed**, 374,67 с. Image `admirra-devops:f1bfefa`, digest `sha256:6fb02b263ba2afee32a2ad54a2e76fd61f4d5481c18ccdea919fedbbb6ffd87f`. Добавленная проверка объединения NULL/пустых UTM прошла. Всего пакет добавил 35 случаев к предыдущему baseline 1001.

Повторный restore того же свежего backup **финальным** образом `f1bfefa`: **50 с**, network=none, schema `de0f1a2b3c4d`, worker preflight/boot четырёх групп, application и API load smoke passed. 40/40 HTTP 200, concurrency 4; p50 119,10 мс / p95 825,11 мс / max 1078,89 мс. Это не реальный provider peak и не время браузерного отображения.

Test/restore containers, test network и restore volumes удалены. API-2 healthy; root filesystem 34 GiB, свободно около 18 GiB. Production сохранён на backend `4ca866eb…`, frontend `274aad1d…`, automation `33b4ca03…`; production schema и границы 10% read-canary не менялись. Никакие реальные клиентские уведомления/платежи при проверках не отправлялись.
