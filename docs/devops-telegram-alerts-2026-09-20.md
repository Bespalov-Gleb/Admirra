# Telegram alerts: подключение

Получатель выбран владельцем: техническая группа AdMirra Alerts. Токен хранится только на серверах в `/etc/admirra/monitoring/telegram-token`, не в репозитории, CLI arguments или environment контейнера. На API-1 права root:65534 0440, на независимом heartbeat root:root 0400. Токен был передан в переписке; рекомендуется последующая ротация через BotFather на обоих узлах.

## Два независимых пути

1. Prometheus → локальный Alertmanager → WireGuard `10.78.0.3:8080/telegram` → HTTPS Telegram. Прямой IPv4 Telegram с API-1 не отвечает; native Telegram receiver использует закрытый фиксированный gateway. Alertmanager слушает только 127.0.0.1:9093. Общие сообщения группируются, повторяются через 4 часа; recovery включён. Для синтетического `AdMirraDeliveryTest` ожидание 5 секунд, обновление группы 10 секунд. Disk critical подавляет disk warning того же узла. Telegram HTTP redirects запрещены; plaintext-шаблон исключает ошибки Markdown.
2. Третий сервер, AI gateway → public HTTPS probes → Telegram напрямую, без зависимости от первых двух серверов. Максимум три попытки проверки; уведомление о сбое, восстановлении и напоминание через 4 часа. Первое здоровое состояние молчит. State переживает рестарты, failed send повторяется следующим запуском таймера. Pending incident сохраняется до внешней отправки; даже неопределённый результат отправки не теряет recovery. Доставка at-least-once: timeout/crash после принятия сообщения Telegram может дать дубль.

Конфиг heartbeat `/etc/admirra/monitoring/heartbeat-telegram.json` содержит `token_file` и `chat_id`, опционально `message_thread_id`. Systemd drop-in включает notifier, timeout 80 секунд покрывает probes и Telegram. Файл состояния probes не содержит тела ответов, пользовательские данные или секреты; notification state содержит только флаги и время.

Gateway location разрешает только POST `/telegram/bot<token>/sendMessage` с API-1 (10.78.0.1), query string запрещён, body до 16 KiB, rate 1/s с burst 10. Upstream фиксирован на api.telegram.org, TLS/CA проверяются, повторы upstream запрещены. Token-bearing URI не пишется в access log; error log этой location выключен, поскольку Nginx может включать URI в текст ошибки. Основные OpenRouter endpoints/ACL/firewall не меняются. Новый include — `/etc/nginx/snippets/admirra-telegram-location.conf`.

## Приёмка

- 32 изолированных unit cases heartbeat + delivery smoke: pass, сеть контейнера отключена.
- До выкладки обязательны pinned `amtool check-config`, `promtool check config` и systemd verify.
- После выкладки: readiness, all scrape targets, real synthetic Alertmanager firing/resolved и явно помеченные `[ТЕСТ — сайт не отключался]` heartbeat critical/recovery. Нельзя объявлять уведомления прочитанными человеком по одному HTTP 200; владелец подтверждает получение всех четырёх сообщений отдельно.
- Тест heartbeat использует отдельный временный state, production status/notifications не меняет. Сайт не останавливается.

## Ограничения

- Обе доставки зависят от AI gateway, одного Telegram-бота и Telegram API. Блокировка/отзыв токена или падение третьего сервера — общий отказ; независимый email/второй канал не включён. Внешний heartbeat независим от двух app servers, но два Telegram-пути не являются независимыми друг от друга каналами.
- Внешний heartbeat проверяет доступность сайта/API, а не каждую внутреннюю очередь и не состояние самого Alertmanager. Отказ отправки Telegram виден в метриках/статусах, но не может гарантированно сообщить о себе через тот же недоступный канал.
- Отдельный ответственный за реакцию и offline-копия recovery key не подтверждены этим подключением.

## Откат и ротация

- Alertmanager можно остановить `docker stop admirra-alertmanager`; его volume и секрет не удалять. Prometheus хранит прежние данные. Новый release конфигурации разворачивается отдельно от приложений.
- Heartbeat notifier отключается удалением только `/etc/systemd/system/admirra-public-heartbeat.service.d/telegram.conf` с `systemctl daemon-reload`; базовый observe-only timer остаётся. Код и unit предыдущего release сохранены перед установкой.
- Ротация: новый токен через stdin в защищённый временный файл, owner/mode как выше, atomic replace; пересоздать только Alertmanager (file bind mount должен увидеть новый inode), heartbeat читает токен при каждой отправке. Прогнать две synthetic пары снова, старый токен отозвать.

Основание: [официальная конфигурация Telegram receiver](https://prometheus.io/docs/alerting/latest/configuration/#telegram_config).

## Production evidence

Включено 20.09.2026 около 20:13–20:23 UTC. Commits `d32cf78`, `b67a33f`, `3848411`, `7aa9bf7`.

- API-1: release `/opt/admirra-monitoring/telegram-d32cf78/ops/monitoring`, overlay исправлений до `7aa9bf7`; pinned Alertmanager image `sha256:e9733bafb1bdef9b00e25a21f8f99dc26a22224bf16641ad754d1649f4c3357a`. Prometheus использует конфиги из того же release, прежний TSDB volume сохранён.
- AI gateway heartbeat release `/opt/admirra-public-heartbeat-telegram-d32cf78`; executable `/opt/admirra-public-heartbeat/external_heartbeat.py`, Telegram drop-in активен. Gateway source release `/opt/admirra-telegram-gateway-3848411` с исправлением `7aa9bf7`; Nginx graceful reload, прежний конфиг в `/etc/admirra/monitoring/rollback-d32cf78/`.
- `amtool check-config`: pass; `promtool`: pass, 23 rules; systemd verify: pass (посторонние deprecated CPUAccounting warnings provider xfs units). После установки heartbeat timer enabled/active, Result=success, public 200/auth401, notification not_due в обычном здоровом запуске.
- Реальный heartbeat smoke отправил две явно помеченные test нотификации, Telegram API подтвердил обе.
- Прямая отправка из API-1 сначала завершилась timeout; это реальный найденный сетевой дефект, не успешная приёмка. После переключения на WireGuard gateway новая synthetic пара Alertmanager дала **2 notification requests / 2 notifications / 0 failures**. Текущее отсутствие токена в Alertmanager log проверено без его вывода.
- В первоначальном старом Compose был неподдерживаемый `--web.enable-lifecycle`; удалён в `b67a33f`. До исправления перезапускался только новый Alertmanager, приложение не затрагивалось. Изолированный Nginx test также поймал `set` после `rewrite ... break`; порядок исправлен до live reload.
- Gateway: 8 unit tests; изолированный real-Nginx test точных путей/методов/query, отсутствие dummy token в access/error logs и 25/50/100 synthetic SSE — pass. Платных model calls не было.
- Итог: 7/7 Prometheus targets up, active alerts пуст, сайт HTTP 200, ingress monitor active. Backend/frontend/automation images и restart counters не изменились. Общие migrations/workers не включались.
- Владелец получил запрос подтвердить видимость **четырёх** тестовых сообщений. Ответ пока не получен: human acceptance не отмечена выполненной в cutover gate.

## Дополнительно: место на API-2

Проверка обнаружила реальный disk warning: 40 GiB физический диск, root LV 18,47 GiB, ещё 18,47 GiB свободны в VG. Сначала сохранена metadata `/etc/lvm/backup/ubuntu-vg.before-telegram-20260920`, выполнен `lvextend --test`, проверены ext4/отсутствие snapshot/pool. Затем absolute target `lvextend --resizefs -l 8825 /dev/ubuntu-vg/ubuntu-lv`: LV вырос до 34,47 GiB, ext4 расширена online. `df`: 34G total / 14G used / 19G available, 43%; VG reserve 2,47 GiB. API-2/Redis/exporters и monitor timer остались healthy/active, без рестарта. Данные и rollback images не удалялись. Обратное уменьшение root не предлагается как безопасный rollback.

Обоснование способа расширения: [lvextend](https://man7.org/linux/man-pages/man8/lvextend.8.html), [online ext4 resize](https://man7.org/linux/man-pages/man8/resize2fs.8.html).
