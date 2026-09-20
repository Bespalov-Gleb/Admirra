# API-2 canary — health guard и Docker recovery

Дата включения: 20.09.2026. Статус: lightweight guard включён на обоих production-узлах; доставка уведомления человеку остаётся открытой до выбора владельцем канала и получателя.

## Что включено

- `admirra-api2-monitor@ingress.timer` на сервере 1 запускается раз в минуту.
- `admirra-api2-monitor@api2.timer` на сервере 2 запускается раз в минуту.
- Probe не использует JWT, рекламные токены, платёжные ключи или данные клиентов.
- Результат пишется одной JSON-строкой в journald и в Prometheus textfile:
  - `/var/lib/admirra-api2-monitor/ingress.prom`;
  - `/var/lib/admirra-api2-monitor/api2.prom`.
- Проверяются: свободное место, возраст WireGuard handshake, API-2 readiness и DB check, Nginx service/config, финальные 5xx и fallback canary за десять минут, состояние/restart count контейнера API-2.
- Порог диска: warning ниже 20%, critical ниже 10%. Любой финальный 5xx, unhealthy API-2/Nginx/VPN или critical disk возвращает ненулевой статус.

Systemd unit работает с `ProtectSystem=strict`, `ProtectHome=yes`, `PrivateTmp=yes`, `NoNewPrivileges=yes`; write-доступ ограничен каталогом метрик и техническими путями, нужными `nginx -t`.

## Проверки

- Три изолированных unit-теста прошли стандартным `unittest`.
- Оба штатных production probe завершились `status=ok`, `ExecMainStatus=0`.
- Negative probe с отсутствующим API-2 container вернул `critical`, exit 2.
- Negative probe с недоступным readiness URL вернул `critical`, exit 2.
- Выполнен контролируемый `systemctl restart docker` только на сервере 2. API-2, broker Redis и cache Redis автоматически вернулись в healthy за 11 секунд.
- Во время recovery публичные запросы `/api/auth/me` не получили итоговых 5xx; Nginx зафиксировал retry API-2 → API-1. Это проверка Docker recovery, а не OS reboot/WireGuard recovery.
- На сервере 1 удалён только неиспользуемый Docker build-cache старше суток: освобождено 14,28 ГБ, использование `/` уменьшилось с 79% до 43%. Images, containers, volumes и rollback-релизы не удалялись.

## Эксплуатация

Проверка последних результатов:

```sh
systemctl list-timers --all 'admirra-api2-monitor@*'
journalctl -u admirra-api2-monitor@ingress.service -n 20 --no-pager
journalctl -u admirra-api2-monitor@api2.service -n 20 --no-pager
```

Отключение без удаления evidence:

```sh
# сервер 1
sh /root/admirra-api2-monitor-20260920/uninstall-monitor.sh ingress

# сервер 2
sh /root/admirra-api2-monitor-20260920/uninstall-monitor.sh api2
```

Повторное включение — `install-monitor.sh` с соответствующей ролью. Установка идемпотентна и перед reload выполняет `systemd-analyze verify`.

## Открытые ограничения

1. Textfile-метрики пока не собираются центральным TSDB; это подготовленный Prometheus-совместимый контракт.
2. Канал технических alert и ответственный получатель владельцем не выбраны, поэтому подтверждённой цепочки «alert → человек → recovery» ещё нет.
3. OS reboot и отдельный WireGuard fault/recovery требуют согласованного окна; Docker recovery уже проверен.
4. Наблюдение canary должно пройти минимум полный рабочий цикл до увеличения доли или набора маршрутов.
