# Alertmanager — подготовленный production receiver

> Обновление: выбран Telegram, webhook-шаблон заменён native receiver. Production включение, private gateway и реальные проверки описаны в [devops-telegram-alerts-2026-09-20.md](devops-telegram-alerts-2026-09-20.md). Ниже — историческое состояние до подключения; команды/пути webhook не использовать для новой конфигурации.

Дата: 20.09.2026. Статус: конфигурация, deploy/rollback и synthetic firing/resolved smoke подготовлены и проверены изолированно; production Alertmanager не включён, уведомления человеку не подключены до получения адреса канала. Независимый public heartbeat на третьем сервере уже [включён отдельно](devops-external-heartbeat-2026-09-20.md).

## Реализация

- Alertmanager `0.34.1`, официальный multi-arch image закреплён digest `sha256:e9733bafb1bdef9b00e25a21f8f99dc26a22224bf16641ad754d1649f4c3357a`.
- Слушает только `127.0.0.1:9093`; публичный порт не создаётся, single-node cluster port выключен.
- Контейнер работает UID/GID `65534`, без capabilities, с `no-new-privileges`, read-only rootfs, лимитами 256 MiB / 0,25 CPU / 128 PID.
- Данные silences/notification log хранятся в отдельном named volume. Compose project `admirra-alerting` отделён от Prometheus, поэтому rollback Alertmanager не удаляет monitoring project.
- Receiver — generic webhook; URL не хранится в Git или YAML, а читается из root-owned файла, доступного только группе процесса.
- `send_resolved=true`; alerts группируются по имени/severity/node, повторяются не чаще одного раза в четыре часа.
- В Prometheus добавлен локальный Alertmanager target и два правила: Alertmanager не обнаружен и ошибка доставки.

Alertmanager поддерживает группировку, дедупликацию, silences и маршрутизацию уведомлений; generic webhook принимает firing/resolved payload. Использованные настройки соответствуют [официальной конфигурации Alertmanager](https://prometheus.io/docs/alerting/latest/configuration/) и [официальной документации уведомлений](https://prometheus.io/docs/alerting/latest/notifications/).

## Подключение выбранного канала

Владелец передаёт один защищённый webhook URL технического канала. Это может быть отдельный Telegram/почтовый relay или иной сервис, который принимает стандартный Alertmanager payload. URL не присылается в Git и не вставляется в командную строку с shell history.

На server 1 оператор создаёт:

- `/etc/admirra/monitoring/alertmanager.yml` из `alertmanager.yml.example`;
- `/etc/admirra/monitoring/alertmanager-receiver-url` с одной строкой URL;
- оба файла `root:65534`, mode `0440`.

После защищённой доставки файлов:

```sh
sh deploy-alertmanager.sh
sh deploy-prometheus.sh
python3 alertmanager_delivery_smoke.py
```

Последняя команда отправляет одну синтетическую пару `firing → resolved`, не содержит данных клиентов и ждёт 45 секунд между состояниями. Пункт принимается только после фактического подтверждения человеком обоих сообщений; успешный HTTP submit сам по себе недостаточен.

## Проверка и откат

Изолированно пройдены:

- `amtool check-config` — 1 route/receiver, success;
- `promtool check config` — Prometheus config и 22 rules, success;
- Compose render без секретов — success;
- 6 unit tests synthetic delivery — pass в immutable candidate image, `network=none`, read-only rootfs.

После production включения проверить `http://127.0.0.1:9093/-/ready`, Prometheus targets/alerts, затем firing/resolved доставку. Откат Alertmanager:

```sh
sh remove-alertmanager.sh
```

После отката вернуть предыдущий Prometheus config либо ожидать `AdMirraAlertmanagerUnavailable`. Named volume сохраняется; secrets удаляются отдельно только по утверждённой ротации.
