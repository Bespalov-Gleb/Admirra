# UTM в уведомлениях о регистрации — 28.09.2026

## Причина

У 15 новых пользователей за последние 7 дней поля registration_utm_source,
registration_utm_medium и registration_utm_campaign были пустыми. Доставка
уведомлений работала: за последние 3 дня все 6 сообщений имели статус sent.
Бот уже умел отображать эти поля, но сквозной сбор отсутствовал: ссылки
лендинга на /signup не сохраняли query, email-фронтенд не передавал UTM,
OAuth создавал аккаунт без этих полей.

## Исправление

- Один небольшой same-origin скрипт подключён в head лендинга и SPA.
- Первый визит с непустыми UTM сохраняется на 30 дней в cookie
  admirra_signup_utm: Path=/, SameSite=Lax, Secure на HTTPS.
- Запоминаются source/medium/campaign, до 120 символов каждое. Прямой визит,
  возврат из OAuth и последующая рекламная ссылка не переписывают первый источник.
- Backend сохраняет метки при INSERT нового пользователя для Email, Яндекса,
  VK ID и MAX, до возникновения уведомления в outbox.
- MAX хранит метки в попытке авторизации до webhook, где браузерных cookie нет.
- Повторный вход и привязка провайдера не меняют источник существующего аккаунта.
- Невалидные cookie игнорируются; эти данные не используются для авторизации.
- Нет новых внешних API-вызовов, запросов к Метрике или отдельной очереди.
  Бот и его конфигурация не менялись. Метки не восстанавливаются из способа входа.

## Проверки

- 125 backend-тестов passed на изолированном PostgreSQL с candidate image:
  все способы регистрации, запись меток до INSERT/outbox, повторный вход,
  MAX webhook, старые попытки MAX, форматирование сообщения бота, некорректные
  cookie, совместимая миграция и регрессия оплаты/онбординга.
- 4 Node-теста passed: первый источник, прямой/yclid-only визит, Unicode/размер
  cookie, отключённые cookie.
- Изолированный браузер: реальный collector и ссылка лендинга, четыре сценария,
  имитация OAuth round-trip и проверка отправленного Cookie. Весь HTTP замокан;
  реальные аккаунты, уведомления и рекламные конверсии не создавались.
- На runtime API проверено внедрение Request в /register, без изменения body.
- После выкладки оба readiness=ok, активных Prometheus alerts нет,
  restart_count=0, notifier работает, старая automation остаётся остановлена.
- Проверены публичные HTML / и /ai и байты /signup-attribution.js?v=1.

## Production

- API source: **183c66d**, оба узла. Образы собраны на прежнем runtime 32a8d9e.
  API1 image b4e702e50895ea362a514a099d940b84f0de8bce07c6f11156206b3ccc3a9311;
  API2 image f109c8ed8c93df2b1c82699fcae466437fa71f58c14f3af6cbee4495019b7c4c.
- Frontend overlay: **a03d2e1**, image
  2d03fa14f595accabe8e11b39365a08531979a99f825357ea38526d897447f83.
  Существующий entry /assets/index-7jLsuM6R.js и все assets сохранены.
  Только две HTML-вставки collector и сам JS. Legal/nginx без изменений.
- Nullable json max_oauth_login_attempts.registration_attribution добавлен
  ограниченной транзакцией владельца таблицы; lock_timeout 2s, statement_timeout
  10s, advisory lock. **alembic_version остаётся f68b92a3b4c5**.
  Миграция f8ad4b5c6d7e идемпотентна при позднейшем согласованном продвижении схемы.
- API выкатывались по одному, с drain upstream и завершением старых Nginx workers.
  Исходная конфигурация ingress восстановлена. Env/порты/сети/mounts проверены,
  SHARED_READ_CACHE=true сохранён. Рабочие процессы и БД не перезапускались.
- Snapshot API на обоих узлах: /etc/admirra/releases/signup-utm-183c66d.
  Snapshot frontend: /etc/admirra/releases/frontend-readiness-a03d2e1.
  Откат API через ops.deploy_dashboard_lockfix после drain; frontend — сохранённый
  frontend-previous.json. При откате оставить nullable-колонку и текущую schema revision.

## Границы и последующая проверка

Нужно проверить следующую **реальную новую регистрацию с URL, содержащего UTM**:
в Telegram должны появиться источник, medium и кампания. Без UTM, с одним yclid,
при блокировке cookie, смене браузера/устройства или после истечения 30 дней
источник может отсутствовать. Существующих пользователей не обновляли.

Незакоммиченный пользовательский черновик landing/index.html не трогали и не
деплоили. При его будущей публикации сохранить подключение signup-attribution.js;
в отслеживаемом public/landing-new/index.html и SPA index.html оно уже есть.
