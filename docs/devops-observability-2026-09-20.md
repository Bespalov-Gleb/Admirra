# Production observability — host, PostgreSQL и Redis

Дата включения: 20.09.2026. Статус: центральный Prometheus собирает host-, API-2-canary-, PostgreSQL- и Redis-метрики с обоих production-узлов; правила алертов вычисляются. Alertmanager/доставка человеку не включены до выбора владельцем канала и получателя.

## Развёрнутая схема

- Prometheus `3.5.5 LTS`, image `sha256:332c2f43e7e389d74d3893b55bb02fbbd684208e681eeb604641d5d769c0fe2a`, работает на сервере 1.
- node-exporter `1.12.1`, image `sha256:1b4e4438faca4dd7e001dd445d161a4a2091b0fededa84093b3a8dfeae1f1be0`, работает на обоих узлах.
- postgres-exporter `0.20.1`, image `sha256:ac5ec343104fae0e2d84a27bb8d69b38430a11910c5382cad85d478d2bab713e`, работает на сервере 1.
- redis_exporter `1.89.0`, image `sha256:fed773ffd2bb2eac706e0ed9cc2fff41651193ee4977e2a4f6919658ad2313f4`, по одному экземпляру для broker и cache работает на сервере 2.
- Prometheus слушает только `127.0.0.1:9090`.
- Exporters слушают только WireGuard-адреса `10.77.0.1:9100` и `10.77.0.2:9100`.
- PostgreSQL exporter слушает только `127.0.0.1:9187`; Redis exporters — только `10.77.0.2:9121/9122`.
- Проверка извне: `9090`, `9100`, `9187`, `9121` и `9122` на соответствующих публичных IP недоступны.
- Все images закреплены digest, контейнеры работают без Linux capabilities и с `no-new-privileges`; exporter mounts read-only.
- Prometheus ограничен 768 MiB / 0,75 CPU, retention 7 дней и максимум 1 ГБ TSDB. Каждый exporter ограничен 128 MiB / 0,25 CPU.

Официальные версии выбраны по стабильным релизам проектов: Prometheus 3.5 — LTS-линейка, node-exporter 1.12.1 — актуальный стабильный релиз на дату установки.

## Собираемые данные

- CPU, load, RAM/swap, filesystem/inodes, network, pressure и базовые kernel metrics обоих узлов.
- Локальные API-2 health-guard metrics через node-exporter textfile collector:
  - состояние API-2/Nginx/WireGuard;
  - финальные 5xx и fallback canary за окно;
  - disk free;
  - API-2 container restart count;
  - timestamp последней проверки.
- PostgreSQL: доступность, число подключений и предел, состояния сессий, длительные транзакции, deadlocks и стандартные показатели `pg_stat_*`.
- Redis broker/cache: доступность, память/maxmemory, evictions, AOF broker и стандартные INFO-метрики.

Не используются user/project/request IDs, содержимое HTTP-запросов, токены и клиентские данные.

PostgreSQL exporter использует отдельную роль `admirra_monitor`: членство только в `pg_monitor`, `default_transaction_read_only=on`, `statement_timeout=5s`, connection limit 2. Redis exporters используют отдельного ACL-пользователя `monitor`: разрешены только служебные read-only команды для INFO/CONFIG GET/SLOWLOG/LATENCY; keyspace и write-команды недоступны. Рабочие API/worker credentials при добавлении мониторинга не менялись. Secrets находятся только в `/etc/admirra/monitoring`, mode `0400`, под UID контейнеров.

## Правила

`rules.yml` содержит 19 правил:

- exporter down;
- health guard failed/stale;
- disk warning/critical;
- low available memory;
- final canary 5xx;
- canary fallback;
- stale WireGuard handshake;
- API-2 container restart;
- PostgreSQL exporter/connection saturation/idle and long transactions/deadlocks;
- Redis exporter/evictions/high memory/AOF failure.

Тестовый Docker recovery создал fallback, и Prometheus перевёл соответствующее правило в pending/firing; то есть цепочка `probe → exporter → Prometheus → rule` проверена. Доставка человеку ещё не проверена и не считается закрытой.

## Приёмка и доступ

Prometheus targets:

- `http://10.77.0.1:9100/metrics` — up;
- `http://10.77.0.2:9100/metrics` — up;
- `http://127.0.0.1:9090/metrics` — up.
- `http://127.0.0.1:9187/metrics` — `pg_up=1`;
- `http://10.77.0.2:9121/metrics` — broker `redis_up=1`;
- `http://10.77.0.2:9122/metrics` — cache `redis_up=1`.

После включения все шесть Prometheus targets имеют `up=1`, `ALERTS{alertstate=~"pending|firing"}` пуст. Проверены входные series для всех новых правил: max connections 200, текущие подключения собираются, long transactions 0, Redis maxmemory ненулевой, broker AOF status 1. На момент приёмки Prometheus потреблял около 36 MiB, PostgreSQL exporter около 8 MiB, Redis exporters около 8 MiB каждый.

Интерфейс доступен оператору через SSH tunnel, не через публичный firewall:

```sh
ssh -L 9090:127.0.0.1:9090 root@91.221.68.90
```

После подключения открыть локально `http://127.0.0.1:9090`.

Проверка конфигурации перед каждым deploy выполняется `promtool check config`; на production подтверждено 19 валидных rules.

## Деплой и откат

Release-каталог обоих узлов: `/opt/admirra-monitoring/release-20260920`.

Повторный deploy:

```sh
# server 1
sh deploy-node-exporter.sh 10.77.0.1:9100
sh provision-postgres-monitor.sh
sh deploy-postgres-exporter.sh
sh deploy-prometheus.sh

# server 2
sh deploy-node-exporter.sh 10.77.0.2:9100
python3 provision-redis-exporter.py
sh deploy-redis-exporters.sh
```

Откат сначала Prometheus, затем exporters. TSDB volume намеренно сохраняется:

```sh
sh remove-prometheus.sh
sh remove-node-exporter.sh
sh remove-postgres-exporter.sh
sh remove-redis-exporters.sh
```

## Что ещё требуется для OBS

1. Выбрать отдельный технический канал и ответственного; подключить Alertmanager/receiver и подтвердить тестом alert → человек → resolved.
2. Добавить application metrics API/DB pool/SSE, durable jobs/sync/reports/AI/billing после включения соответствующих runtime-компонентов.
3. Подключить внешний uptime heartbeat вне обоих серверов: локальный Prometheus не сообщит о полном падении server 1/ingress.
4. Уточнить retention после замера фактического TSDB growth; текущие 7 дней/1 ГБ — ограниченная стартовая политика.
