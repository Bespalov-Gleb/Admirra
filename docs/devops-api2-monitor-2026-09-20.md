# API-2 canary — health guard и Docker recovery

Дата включения: 20.09.2026. Статус: lightweight guard включён на обоих production-узлах и собирается центральным Prometheus; доставка уведомления человеку остаётся открытой до выбора владельцем канала и получателя.

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
- Выполнена контролируемая полная OS reboot сервера 2. Boot ID сменился; `wg-quick@admirra0`, Docker, API-2 monitor и backup-prune timer восстановились автоматически. WireGuard стал active в `16:06:29 UTC`, Docker — в `16:06:31 UTC`; API-2, broker/cache Redis и exporters вернулись в healthy, приватный readiness — 200.
- Непрерывный публичный probe охватил reboot/recovery: 243 запроса к `/api/auth/me`, все вернули ожидаемый 401, `5xx/000 = 0`, max response time 2,154 s. Два обращения сначала получили upstream 504 от API-2 и в том же запросе завершились 401 через API-1 — failover реально сработал.
- Во время согласованной аварийной проверки Prometheus ожидаемо поднял `AdMirraCanaryMonitorFailed` и `AdMirraCanaryFallback`; final 5xx остались 0. После reboot все шесть scrape targets `up`, health guard server 2 — `ok`, backup repository сохранил complete sets. Публичные порты API-2/node/Redis exporters `8001/9100/9121/9122` остались закрыты.
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

1. Канал технических alert и ответственный получатель владельцем не выбраны, поэтому подтверждённой цепочки «alert → человек → recovery» ещё нет.
2. Отдельный принудительный WireGuard fault/recovery без reboot ещё не выполнялся; автоматическое восстановление WireGuard после полной OS reboot подтверждено.
3. Наблюдение canary должно пройти минимум полный рабочий цикл до увеличения доли или набора маршрутов.
