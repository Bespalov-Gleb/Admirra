# Уведомления о новых аккаунтах AdMirra

Отдельный потребитель PostgreSQL outbox → бот `admirra_notifications_bot` →
группа **AdMirra Notifications** (`-5380035031`). Это не бот технических алертов
и не бот клиентских отчётов. Токен/пароль БД не хранить в Git, CLI или логах.

## Что считается регистрацией

Новая строка `public.users`. Один `AFTER INSERT` trigger создаёт запись с UUID
в `registration_notifier.outbox` **в той же транзакции**. Откат регистрации
откатывает событие. Повторный вход, редактирование профиля, подключение OAuth
существующему пользователю не создают событие. Новые пользователи, созданные
через приглашение/админку, также учитываются; это не только `/auth/register`.
Существующие аккаунты не импортируются. Первоначальная задержка 10 секунд.
Email-регистрация ещё может быть не подтверждена — сообщение указывает это.

В сообщении: имя, настоящий email, телефон при наличии, текущие связанные
провайдеры авторизации, сохранённые UTM source/medium/campaign, время МСК и UUID.
Служебные OAuth email не выдаются за контакты. Отсутствие UTM не означает
«прямой заход»: источник помечается неизвестным. Страница регистрации,
первый landing/referrer сейчас не сохраняются и не выдумываются. Никаких
паролей, IP, сессий или рекламных токенов отправщик не читает.

## Изоляция и доставка

- Независимый Compose project, pinned существующий Python/psycopg2 image;
  не обновляет backend/frontend/automation и не запускает pending Alembic head.
- Additive SQL в собственной схеме. При DDL lock timeout 2s установка
  откатывается, а не ждёт бесконечно. SQL trigger добавляет одну небольшую
  запись при создании аккаунта; HTTP никогда не выполняется из транзакции.
  Отказ Telegram не мешает регистрации. Как у любого транзакционного outbox,
  **ошибка самой БД/таблицы outbox может откатить регистрацию**; rollback ниже.
- Role `admirra_registration_notifier`: только SELECT разрешённых колонок
  `users`/`user_oauth_identities`, SELECT/UPDATE собственной очереди, максимум
  2 подключения. Никакого доступа к password_hash или записи пользователей.
- HTTP после закрытия SQL. SKIP LOCKED, отдельный lease, повторная проверка
  токена при фиксации результата. Очередь сохраняется в PostgreSQL/его backup.
- Один consumer, пауза 3.2s: меньше 20 сообщений в минуту на группу.
  Только явные 429 и доказанные отказы соединения до отправки повторяются,
  максимум 12 попыток. HTTP timeout, 5xx, crash между отправкой и подтверждением
  дают `uncertain`: автоматического дубля нет, но нужно ручное выяснение исхода.
  Это **не обещание exactly-once** и не гарантированная доставка без участия
  оператора при неопределённом результате.
- `failed`, `uncertain` и просроченная pending-очередь делают consumer unhealthy;
  журнал содержит только статусы/коды/количества, без текста сообщения/URL/PII.
  Docker health сам по себе не равен отдельному настроенному Prometheus alert.
- Транспорт с API-1: существующий WireGuard gateway
  `http://10.78.0.3:8080/telegram` → HTTPS Telegram. Без изменений gateway/ACL.
  Нет proxy-env, redirect или повторов неизвестных HTTP результатов.
- Непривилегированный контейнер, read-only FS, no-new-privileges, caps=none,
  128 MiB RAM / 0.25 CPU. Секреты root:65534 0440, каталог 0750.

## Проверка и установка

1. Проверить нового бота и группу через `getMe/getUpdates`, не меняя webhook
   и не подтверждая чужие pending updates. Группа должна быть однозначной.
2. Скопировать этот каталог в отдельный `/opt/admirra-registration-notifier/releases/<release>`.
3. `NOTIFIER_IMAGE=sha256:<tested-image> python3 isolated_test.py`.
   Создаёт собственный временный Postgres на internal Docker network, без
   production mount/портов/интернета; удаляет только свои контейнер/network.
4. `python3 install.py --chat-id=-5380035031 --bot-id=8913695008 --image=sha256:<tested-image>`.
   Токен — через скрытый prompt. Создаёт ограниченную роль, outbox/trigger,
   защищённые файлы `/etc/admirra/registration-notifier` и локальный `.env`
   **этого release**, содержащий только image digest. Сохраняет schema-only
   snapshot прежних users/OAuth. Не запускает consumer. Повторная установка
   не перезаписывает существующие секреты — сначала проверить состояние.
5. `docker compose -p admirra-registration-notifier -f compose.yml config --quiet`.
6. `docker compose -p admirra-registration-notifier -f compose.yml run --rm --no-deps notifier --smoke`.
   Одно явно помеченное тестовое сообщение без настоящих пользователей;
   проверяет реальный egress/бота/группу, **не создаёт аккаунт в production**.
7. `docker compose -p admirra-registration-notifier -f compose.yml up -d --no-build notifier`.
   Проверить health, ошибочные состояния очереди, неизменность app images/start
   times, HTTP сайта. Отдельно получить подтверждение видимости сообщения.

Официальные ограничения/поля: [Bot API](https://core.telegram.org/bots/api#sendmessage),
[лимиты групп](https://core.telegram.org/bots/faq#my-bot-is-hitting-limits-how-do-i-avoid-this).

## Откат / ротация / сопровождение

- Остановка только `admirra-registration-notifier` не мешает сайту, новые события
  остаются pending. Для полного отключения в короткой транзакции с lock_timeout
  2s выполнить `DROP TRIGGER admirra_registration_notify ON public.users`.
  Не удалять пользователей/очередь/схему для обычного отката.
- Повторно включать trigger по `schema.sql` только после проверки очереди.
  События за время, когда trigger отключён, автоматически не восстанавливаются.
- Ротация токена: заменить только `bot-token` в защищённом каталоге, проверить
  права, выполнить один `--smoke`. Файл читается для каждой отправки. Новый
  token того же бота не меняет chat_id. При переносе в супергруппу сначала
  проверить новый chat_id вручную; не перенаправлять контакты автоматически.
- Для `uncertain` сверить сообщение по UUID в группе. Если доставлено — отметить
  `sent`; если достоверно нет — вернуть `pending` с новым available_at.
  Автоматическая очистка failed/uncertain отсутствует, чтобы не скрывать потери.
- После восстановления БД отдельно восстановить ограниченную роль/пароль и
  применить `grants.sql`, если restore использовал `--no-acl`/не переносил роли.
  Проверить уже отправленные события, прежде чем включать consumer на restore:
  восстановление старого backup может вернуть доставленные сообщения в pending.
- Схема независима от Alembic и должна сохраняться в полном backup PostgreSQL.
  При будущей интеграции в общий durable worker отключить этот consumer/trigger,
  сверить очередь и не включать два разных источника одного события.
