# Provider/worker peak acceptance — безопасный контур запуска

Дата: 20.09.2026. Статус: fail-closed scope и resource observer реализованы и проверены; реальная provider-нагрузка не запускалась, потому что владелец ещё не утвердил точный tenant/project/integration scope и тестового получателя.

**Обновление после ревью:** владелец предоставил тестовый аккаунт и разрешил выбор проектов. Scope validator и observer — только части приёмки, а не законченный launcher. Они не ограничивают фактический workload глобальных handlers. Требуется scoped runner с ownership validation и запретом side effects; текущий `provider_peak_accepted=false`. Подробности: [review](devops-review-2026-09-20.md). Digests и команды ниже относятся к прежнему candidate `acf6ed8` и не являются актуальным разрешением запуска.

## Что подготовлено

`ops/provider_peak_scope.py` принимает только короткоживущий JSON-манифест:

- approval не старше 24 часов, expiry не дальше следующих 24 часов;
- назначены owner и operator, строки `REQUIRED*` не проходят;
- exact candidate image `sha256:ad9559725e724789281765526f85839b8b9adf604c114ad25850812b0c544d0a` и schema `bc8d9e0f1a2b`;
- ровно один tenant, 1–5 проектов и 1–10 интеграций в canonical UUID;
- provider calls разрешены явно;
- concurrency не более 4, длительность 5–30 минут;
- bounded manual/nightly/report/assistant/billing-sandbox inventory;
- production messages, реальные списания и force-sync всех проектов всегда запрещены;
- доставка отчёта либо выключена, либо направлена только заранее настроенному sandbox-получателю.

Шаблон `ops/provider_peak_scope.example.json` намеренно блокируется. Он не содержит реальных UUID/получателей и хранится в Git безопасно. Заполненный scope хранится только в защищённом release-каталоге; SHA-256 его точных bytes попадает в measurement evidence.

`ops/peak_observer.py` не запускает jobs и не обращается к provider. Во время утверждённого запуска он каждые 1–2 секунды собирает только:

- CPU, cgroup memory, memory %, PID count каждого launch-контейнера;
- суммарные RSS/PSS всех процессов контейнера через `smaps_rollup`;
- минимальную доступную RAM хоста и максимальные load1/load5;
- restart delta, OOMKilled и финальный container status.

Observer не читает Docker env, логи, SQL, HTTP-тела, токены или customer identifiers. Evidence записывается atomic replace с mode `0600`. Команды фиксированы (`docker stats`, `docker top`, ограниченный `docker inspect`); произвольный shell из scope не выполняется.

## Проверка реализации

- 36 unit cases scope + observer в immutable candidate image, `network=none`, read-only — pass;
- незаполненный example возвращает `blocked` по восьми обязательным причинам;
- реальный двухсэмпловый observer smoke на server 2 для API-2/broker/cache — pass, restart delta 0, OOM false;
- реальное чтение RSS/PSS API-2 и broker на server 2 — pass;
- output evidence mode `0600` подтверждён.

## Порядок утверждённого прогона

1. Владелец указывает тестовый tenant, проекты/интеграции и при необходимости единственный sandbox-получатель. Не использовать массовый список рабочих кабинетов.
2. Заполнить scope, установить expiry внутри окна и проверить:

```sh
python3 ops/provider_peak_scope.py /secure/provider-peak-scope.json \
  --expected-image sha256:ad9559725e724789281765526f85839b8b9adf604c114ad25850812b0c544d0a \
  --expected-schema bc8d9e0f1a2b
```

3. На восстановленной БД/candidate workers запустить observer на весь launch set. Типовой профиль — 150 samples × 2 s; он покрывает пять минут:

```sh
python3 ops/peak_observer.py \
  --scope-file /secure/provider-peak-scope.json \
  --expected-image sha256:ad9559725e724789281765526f85839b8b9adf604c114ad25850812b0c544d0a \
  --expected-schema bc8d9e0f1a2b \
  --container admirra-workers-sync-manual-1 \
  --container admirra-workers-sync-nightly-1 \
  --container admirra-workers-reports-1 \
  --container admirra-workers-maintenance-1 \
  --container admirra-workers-scheduler-1 \
  --container admirra-api2-api-1 \
  --samples 150 --interval 2 \
  --output /secure/provider-peak-measurement.json
```

4. Только после старта observer поставить bounded jobs из scope: manual + nightly на выбранных интеграциях, render без доставки либо sandbox delivery, два AI-запроса, billing sandbox replay. Никаких production charges/получателей.
5. Параллельно снять существующие Prometheus series: DB connections/long transactions/deadlocks, Redis memory/evictions/AOF, host disk/memory, API-2 health/fallback; сопоставить accepted job IDs с единственными terminal business outcomes.

## Критерии принятия

- restart delta 0, OOM false, все контейнеры `running`;
- доступная RAM server 2 не опускается ниже согласованного OS reserve 1536 MiB, container memory не достигает limit;
- worker DB budget вместе с reserve не превышает 20, API budget — 30; нет долгих транзакций/lock pile-up/deadlocks;
- Redis evictions 0, broker AOF healthy, нет потери accepted PostgreSQL jobs;
- manual acceptance p95 ≤300 ms, старт при свободной quota p95 ≤10 s;
- unexpected 5xx <0,5%; provider 429/Retry-After ограничивает темп, а не обходит limiter;
- 0 потерянных jobs, 0 повторных отправок/списаний/business outcomes, 0 чужих данных;
- report render/AI завершаются в заданных пределах и не вытесняют manual reserve;
- scope digest observer совпадает с утверждённым scope.

Любое превышение — `provider_peak_accepted=false`; пороги не ослабляются постфактум. Автоматического production cutover после теста нет.
