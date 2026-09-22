# Регистрации → Telegram: подключено 22.09.2026

Реализация: `8419336`. Инструкция и ограничения:
[ops/registration-notifier/README.md](../ops/registration-notifier/README.md).

## Production

- Отдельный бот `admirra_notifications_bot`, отдельная группа **AdMirra Notifications**,
  chat_id `-5380035031`. Группа определена по обновлению после команды владельца.
  Webhook не настроен и не изменялся; pending updates не подтверждались.
- API-1 release: `/opt/admirra-registration-notifier/releases/20260922-v1`.
  Compose project `admirra-registration-notifier`, container того же имени.
- Pinned Python runtime: существующий backend image
  `sha256:4ca866ebddc4c3af8b1ef4d2905e099453c6e8b6b768192508991b89e8421219`.
  Entry point независимый; основные процессы приложения из image не запускаются.
- Секреты только `/etc/admirra/registration-notifier`, права 0750/0440,
  owner root:65534; role БД не superuser/createdb/createrole, connection limit 2.
- Установлен только additive outbox/trigger в собственной схеме,
  `admirra_registration_notify` enabled (`O`). Alembic head не менялся.
  Старые аккаунты не ставились в очередь. На финальной проверке очередь пустая.
- Consumer `running/healthy`, restart count 0. Сайт HTTP 200.

## Проверки

- 17/17 unit + isolated PostgreSQL cases: email / Yandex / VK / MAX,
  неуведомление о старых пользователях, rollback, отсутствие события при
  обновлении/повторном входе, restricted SQL permissions, claim/lease,
  ограниченные retry, uncertain outcome, formatter, отсутствие открытого SQL
  соединения во время HTTP, сохранение message_id после доставки.
- Изолированные контейнер и internal network удалены; реальные аккаунты для
  проверки не создавались. В production нет синтетических пользователей.
- Реальный `--smoke` через контейнер/приватный gateway/нового бота:
  `sent`, Telegram message_id **4**. Текст явно помечен тестовым,
  содержит `test@example.invalid`, не персональные данные клиентов.
  Это проверка доставки, не наблюдение реальной последующей регистрации.
- Backend/frontend/automation image digest и StartedAt после установки
  совпадают с предустановочным снимком:
  - backend `4ca866eb…`, 2026-09-20T22:47:57.143428525Z;
  - frontend `274aad1d…`, 2026-09-20T23:17:26.310666348Z;
  - automation `33b4ca03…`, 2026-09-16T07:19:56.221802411Z.

## Содержимое уведомления

«Способ» — email/создание аккаунта или связанные провайдеры Яндекс ID, VK ID,
MAX. В тестовом сообщении специально использован сценарий Email.
«Источник» — сохранённый UTM source, не OAuth-провайдер и не предположение о
прямом заходе. Телефон только если уже есть в users.phone. First landing,
referrer и страница регистрации сейчас не собираются этим изменением.

Новые мобильные правки карточек остаются локальными: этот узкий rollout
не включает фронтенд, остальные незавершённые DevOps-изменения или новую
общую миграционную цепочку.
