# Production observability — этап 1

Дата включения: 20.09.2026. Статус: центральный Prometheus собирает host- и API-2-canary-метрики с обоих production-узлов; правила алертов вычисляются. Alertmanager/доставка человеку не включены до выбора владельцем канала и получателя.

## Развёрнутая схема

- Prometheus `3.5.5 LTS`, image `sha256:332c2f43e7e389d74d3893b55bb02fbbd684208e681eeb604641d5d769c0fe2a`, работает на сервере 1.
- node-exporter `1.12.1`, image `sha256:1b4e4438faca4dd7e001dd445d161a4a2091b0fededa84093b3a8dfeae1f1be0`, работает на обоих узлах.
- Prometheus слушает только `127.0.0.1:9090`.
- Exporters слушают только WireGuard-адреса `10.77.0.1:9100` и `10.77.0.2:9100`.
- Проверка извне: `9090/9100` на обоих публичных IP недоступны.
- Все images закреплены digest, контейнеры работают без Linux capabilities и с `no-new-privileges`; exporter mounts read-only.
- Prometheus ограничен 768 MiB / 0,75 CPU, retention 7 дней и максимум 1 ГБ TSDB. Exporter на каждом узле ограничен 128 MiB / 0,25 CPU.

Официальные версии выбраны по стабильным релизам проектов: Prometheus 3.5 — LTS-линейка, node-exporter 1.12.1 — актуальный стабильный релиз на дату установки.

## Собираемые данные

- CPU, load, RAM/swap, filesystem/inodes, network, pressure и базовые kernel metrics обоих узлов.
- Локальные API-2 health-guard metrics через node-exporter textfile collector:
  - состояние API-2/Nginx/WireGuard;
  - финальные 5xx и fallback canary за окно;
  - disk free;
  - API-2 container restart count;
  - timestamp последней проверки.

Не используются user/project/request IDs, содержимое HTTP-запросов, токены и клиентские данные.

## Правила

`rules.yml` содержит десять правил:

- exporter down;
- health guard failed/stale;
- disk warning/critical;
- low available memory;
- final canary 5xx;
- canary fallback;
- stale WireGuard handshake;
- API-2 container restart.

Тестовый Docker recovery создал fallback, и Prometheus перевёл соответствующее правило в pending/firing; то есть цепочка `probe → exporter → Prometheus → rule` проверена. Доставка человеку ещё не проверена и не считается закрытой.

## Приёмка и доступ

Prometheus targets:

- `http://10.77.0.1:9100/metrics` — up;
- `http://10.77.0.2:9100/metrics` — up;
- `http://127.0.0.1:9090/metrics` — up.

Интерфейс доступен оператору через SSH tunnel, не через публичный firewall:

```sh
ssh -L 9090:127.0.0.1:9090 root@91.221.68.90
```

После подключения открыть локально `http://127.0.0.1:9090`.

Проверка конфигурации перед каждым deploy выполняется `promtool check config`; на production подтверждено 10 валидных rules.

## Деплой и откат

Release-каталог обоих узлов: `/opt/admirra-monitoring/release-20260920`.

Повторный deploy:

```sh
# server 1
sh deploy-node-exporter.sh 10.77.0.1:9100
sh deploy-prometheus.sh

# server 2
sh deploy-node-exporter.sh 10.77.0.2:9100
```

Откат сначала Prometheus, затем exporters. TSDB volume намеренно сохраняется:

```sh
sh remove-prometheus.sh
sh remove-node-exporter.sh
```

## Что ещё требуется для OBS

1. Выбрать отдельный технический канал и ответственного; подключить Alertmanager/receiver и подтвердить тестом alert → человек → resolved.
2. Добавить application metrics API/DB pool/SSE, durable jobs/sync/reports/AI/billing после включения соответствующих runtime-компонентов.
3. Добавить PostgreSQL/Redis exporters с отдельными минимальными credentials; текущий этап не выдаёт мониторингу доступ к БД/Redis.
4. Подключить внешний uptime heartbeat вне обоих серверов: локальный Prometheus не сообщит о полном падении server 1/ingress.
5. Уточнить retention после замера фактического TSDB growth; текущие 7 дней/1 ГБ — ограниченная стартовая политика.
