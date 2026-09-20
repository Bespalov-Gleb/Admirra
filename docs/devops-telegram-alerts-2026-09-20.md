# Telegram alerts: подключение

Получатель выбран владельцем: техническая группа AdMirra Alerts. Токен хранится только на серверах в `/etc/admirra/monitoring/telegram-token`, не в репозитории, CLI arguments или environment контейнера. На API-1 права root:65534 0440, на независимом heartbeat root:root 0400. Токен был передан в переписке; рекомендуется последующая ротация через BotFather на обоих узлах.

## Два независимых пути

1. Prometheus → локальный Alertmanager → native Telegram receiver. Alertmanager слушает только 127.0.0.1:9093. Общие сообщения группируются, повторяются через 4 часа; recovery включён. Для синтетического `AdMirraDeliveryTest` ожидание 5 секунд, обновление группы 10 секунд. Disk critical подавляет disk warning того же узла. Telegram HTTP redirects запрещены; plaintext-шаблон исключает ошибки Markdown.
2. Третий сервер, AI gateway → public HTTPS probes → Telegram напрямую, без зависимости от первых двух серверов. Максимум три попытки проверки; уведомление о сбое, восстановлении и напоминание через 4 часа. Первое здоровое состояние молчит. State переживает рестарты, failed send повторяется следующим запуском таймера. Pending incident сохраняется до внешней отправки; даже неопределённый результат отправки не теряет recovery. Доставка at-least-once: timeout/crash после принятия сообщения Telegram может дать дубль.

Конфиг heartbeat `/etc/admirra/monitoring/heartbeat-telegram.json` содержит `token_file` и `chat_id`, опционально `message_thread_id`. Systemd drop-in включает notifier, timeout 80 секунд покрывает probes и Telegram. Файл состояния probes не содержит тела ответов, пользовательские данные или секреты; notification state содержит только флаги и время.

## Приёмка

- 32 изолированных unit cases heartbeat + delivery smoke: pass, сеть контейнера отключена.
- До выкладки обязательны pinned `amtool check-config`, `promtool check config` и systemd verify.
- После выкладки: readiness, all scrape targets, real synthetic Alertmanager firing/resolved и явно помеченные `[ТЕСТ — сайт не отключался]` heartbeat critical/recovery. Нельзя объявлять уведомления прочитанными человеком по одному HTTP 200; владелец подтверждает получение всех четырёх сообщений отдельно.
- Тест heartbeat использует отдельный временный state, production status/notifications не меняет. Сайт не останавливается.

## Ограничения

- Обе доставки зависят от одного Telegram-бота и Telegram API. Блокировка/отзыв токена — общий отказ; независимый email/второй канал не включён.
- Внешний heartbeat проверяет доступность сайта/API, а не каждую внутреннюю очередь и не состояние самого Alertmanager. Отказ отправки Telegram виден в метриках/статусах, но не может гарантированно сообщить о себе через тот же недоступный канал.
- Отдельный ответственный за реакцию и offline-копия recovery key не подтверждены этим подключением.

## Откат и ротация

- Alertmanager можно остановить `docker stop admirra-alertmanager`; его volume и секрет не удалять. Prometheus хранит прежние данные. Новый release конфигурации разворачивается отдельно от приложений.
- Heartbeat notifier отключается удалением только `/etc/systemd/system/admirra-public-heartbeat.service.d/telegram.conf` с `systemctl daemon-reload`; базовый observe-only timer остаётся. Код и unit предыдущего release сохранены перед установкой.
- Ротация: новый токен через stdin в защищённый временный файл, owner/mode как выше, atomic replace; пересоздать только Alertmanager (file bind mount должен увидеть новый inode), heartbeat читает токен при каждой отправке. Прогнать две synthetic пары снова, старый токен отозвать.

Основание: [официальная конфигурация Telegram receiver](https://prometheus.io/docs/alerting/latest/configuration/#telegram_config).

## Production evidence

Заполняется после фактической установки. Эта инструкция сама по себе не означает, что уведомления включены.
