# Внешний public heartbeat AdMirra

Дата включения: 20.09.2026. Статус: независимый heartbeat развёрнут на AI gateway `194.87.134.173`, вне обоих application-серверов. Проверка работает каждые две минуты. Доставка тревоги человеку остаётся отдельным незакрытым шагом до выбора webhook/ответственного.

## Что проверяется

- `GET https://admirra.ru/` обязан вернуть `200` и непустое тело;
- `GET https://admirra.ru/api/auth/me` без сессии обязан вернуть `401`, что одновременно проверяет ingress, backend и auth guard;
- одна попытка ограничена восемью секундами и 256 KiB тела;
- при ошибке выполняются максимум три попытки с паузой две секунды.

Heartbeat не содержит cookies, токенов, tenant/project IDs или клиентских данных. Тела ответов и тексты сетевых ошибок не сохраняются: state содержит только статусы HTTP, длительность, тип ошибки и итог `ok|critical`.

## Развёртывание

- код: commit `b632772`;
- release: `/opt/admirra-public-heartbeat-release-b632772`;
- исполняемый файл: `/opt/admirra-public-heartbeat/external_heartbeat.py`;
- systemd units: `admirra-public-heartbeat.service` и `admirra-public-heartbeat.timer`;
- state: `/var/lib/admirra-public-heartbeat/status.json`, atomic replace, mode `0644`;
- расписание: `OnBootSec=60s`, затем каждые две минуты с небольшим jitter;
- сервис oneshot, с `NoNewPrivileges`, read-only системой, закрытыми home/devices/kernel/control-groups и лимитом памяти 64 MiB.

Таймер `enabled` и `active`. Первый production-запуск завершился `Result=success`, `ExecMainStatus=0`: root `200`, auth `401`, итог `ok`. Внешний ручной smoke с того же узла до установки дал тот же результат.

## Проверки до включения

- 11 unit cases в immutable candidate image, `network=none`, read-only bind — pass;
- `systemd-analyze verify` service/timer на server 2 — pass;
- SHA-256 всех четырёх release-файлов до и после передачи на AI gateway совпали;
- реальный HTTPS smoke с AI gateway — pass;
- systemd timer, итоговый state и journal после установки — pass.

## Ограничение и следующий шаг

Heartbeat намеренно observe-only: при полном падении `admirra.ru` он зафиксирует `critical` локально на независимом узле, но пока не отправит сообщение человеку. После выбора технического webhook нужно связать critical/recovery с тем же получателем, включить подготовленный Alertmanager на server 1 и подтвердить человеку synthetic `firing → resolved`. До этой проверки пункт `alert → человек` остаётся P0.

Повторная установка:

```sh
cd /opt/admirra-public-heartbeat-release-b632772
sh install-external-heartbeat.sh
```

Остановка без удаления state:

```sh
systemctl disable --now admirra-public-heartbeat.timer
```
