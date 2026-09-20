# DB-02 / ресурсы — родительские пулы Celery и проверка capacity

Часть T03 / §4.3, DB-01–02. Подготовлено локально; production workers/API не запускались. Это не акт завершения всего DB/двухсерверного этапа.

## Подтверждённый риск и исправление

`automation.work_worker` выполнял SQL preflight до prefork, оставляя idle connection в родительском pool. `worker_process_init` уже правильно создавал дочерний pool через `dispose(close=False)`, но это не освобождало соединение **родителя**. Пять parent-процессов могли дополнительно держать 5 idle connections поверх 14 child + 2 scheduler — выше лимита 20 у `admirra_worker`.

Теперь `prepare_worker_parent()` выполняет preflight, требует отсутствия checked-out SQL connections и закрывает parent pool **до** fork. Если незавершённая SQL session осталась, запуск отклоняется. Child reset сохранён, child не закрывает сокет родителя. Runtime engine остаётся пригодным для новых соединений.

Проверки используют настоящий PostgreSQL: preflight → ноль idle/checked-out connections; запрет fork с активным соединением; настоящий `fork` → разные `pg_backend_pid`, при этом parent connection остаётся работоспособным. Существующие tests SIGKILL/recovery настоящего Celery worker продолжают проходить. Рекомендуемый entrypoint — только `python -m automation.work_worker`, не обходной raw Celery CLI.

Основание: [SQLAlchemy pooling и multiprocessing](https://docs.sqlalchemy.org/en/20/core/pooling.html#using-connection-pools-with-multiprocessing-or-os-fork).

## Manifest и арифметический gate

`ops/worker_capacity.json` фиксирует наблюдённую память сервера 2 и budgets. `ops/check_worker_capacity.py` читает **реальный prepared Compose**, считает replicas × prefork children × pool cap; parent учтён как процесс, но больше не держит SQL pool. Heartbeat использует второй слот child pool, не отдельный безлимитный engine. Пулы меньше 2 для worker отклоняются.

```sh
python3 -m ops.check_worker_capacity
python3 -m ops.check_worker_capacity --with-api2
```

Только чтение структуры: Compose `config --no-env-resolution --no-interpolate --format json`, env interpolation file `/dev/null`. Пароли/полные env/разрешённая конфигурация не печатаются; выводится только арифметический отчёт. Неизвестные service, отсутствие caps, autoscale/другой pool, неподтверждённые units приводят к отказу. [Docker Compose config](https://docs.docker.com/reference/cli/docker/compose/config/).

Первоначальный фактический результат на сервере 2:

| Вариант | Container memory caps | Остаток ОС | SQL worker | Результат |
| --- | ---: | ---: | ---: | --- |
| Исходный prepared workers, новый pool lifecycle | 6400 MiB | 1540 MiB | 16 + 4 reserve = 20 | Арифметика проходит, нагрузка **не принята** |
| Те же workers + кандидат API-2 1024 MiB / 1 process | 7424 MiB | 516 MiB | 16; API-2 отдельно 10 | Отказ: нарушен минимум 1536 MiB для ОС |

Даже первый вариант почти не имеет запаса сверх минимального резерва. CPU caps суммарно 7,5 на 4 CPU (с API-2 — 9); они могут конкурировать, это не зарезервированные ядра. tmpfs входит в container memory, пики рендера/RSS/PSS и AOF rewrite требуют нагрузки. `capacity_pass=true` **никогда** не означает `load_accepted=true` или разрешение production cutover.

Не урезали память jobs вслепую и не повысили DB role limits, чтобы «прошёл тест». Для двух API нужно измерить пики и пересобрать бюджет/расположение ролей, либо увеличить ресурс; проявить нужные лимиты в проверенном Compose. Manifest кандидата API-2 — план ресурсов, не готовый ingress/deploy config и не проверка всего сервера 1.

## Стартовый профиль 20.09.2026

Для первого single-API durable-worker rollout подготовлен ограниченный профиль, который помещается рядом с действующим read-canary API-2 без снижения DB/OS reserve:

| Вариант | Container memory caps | Остаток ОС | SQL worker | API-2 SQL | Результат |
| --- | ---: | ---: | ---: | ---: | --- |
| Launch workers без API-2 | 5120 MiB | 2820 MiB | 14 + 4 reserve = 18/20 | — | Арифметика проходит |
| Launch workers + API-2 | 6144 MiB | 1796 MiB | 14 + 4 reserve = 18/20 | 5 + API-1 10 + reserve 5 = 20/30 | Арифметика проходит, нагрузка ещё не принята |

Manual/nightly сохраняют concurrency 2 и получают по 1280 MiB; reports и maintenance остаются отдельными по 768 MiB; scheduler — 256 MiB. Новый `ai.prewarm` на стартовом 8 GiB host не запускается и не планируется: `AI_PREWARM_ENABLED=false`, отдельного consumer нет. Это соответствует исходной политике не расширять prewarm без решения владельца и не мешает AI-комментариям/ассистенту по запросу.

Capacity gate теперь сверяет не только названия сервисов, RAM/CPU/SQL, но и эксклюзивное покрытие всех Celery queues. `ai.prewarm` указан как намеренно disabled; пропущенная, неизвестная, задублированная либо одновременно disabled+consumed очередь отклоняет manifest. Сумма CPU caps с API-2 — 8,0 на 4 CPU; это верхние пределы, а не резерв ядер, поэтому load acceptance всё ещё обязательна.

На server 2 реальный Compose разобран через `config --no-env-resolution --no-interpolate`: `capacity_pass=true`, `load_accepted=false`, headroom 1796 MiB, worker pool max 14, API-2 pool max 5. Фокусные capacity/durable tests: **36 passed**, 1 warning, 2,06 s. Чистый immutable candidate `acf6ed8` затем прошёл полный image-only suite: **603 passed, 1 skipped, 1 deselected**, 47 warnings, 6 subtests, 134,66 s.

Дополнительно весь launch consumer set одновременно поднят на восстановленной production-БД после migrations: manual 2, nightly/backfill 2, reports 1, maintenance 1; каждый worker прошёл preflight/ready и ответил на Celery inspect ping через одноразовый Redis. Среда была `network=none`, scheduler/jobs не запускались, полный restore + workers + API smoke занял 41 s и полностью очистился. Это **boot acceptance**, не mixed/peak load acceptance. Production workers не включались.

При том же одновременно работающем consumer set кандидат API с pool `5/0` выдержал bounded authenticated read-load по реальному snapshot: 40/40 HTTP 200, concurrency 4, p50 129,36 ms, p95 692,12 ms, max 807,58 ms. [Отдельный протокол](devops-read-load-2026-09-20.md). Открытым остаётся mixed/peak именно с выполняющимися provider/report/AI/billing jobs и длительный soak.

## Read-only снимок инфраструктуры 12.09

Оба узла: 4 CPU, `MemTotal` около 7940 MiB. На сервере 1 PostgreSQL: max_connections=200, shared_buffers=1GB, work_mem=8MB, max_parallel_workers=8; во время проверки 11 idle и 1 active connection, 5 внутренних backend states. Это мгновенный снимок, не peak/RPS.

Сервер 1: disk `/` около **80%**, доступно 7401 MiB; сервер 2 около 64%, доступно 6296 MiB. Нужны отдельные disk/backup/retention gates, автоматическое удаление образов/backup не запускалось. Legacy service memory не ограничена индивидуально (показывается общий host limit); перед cutover нужно заменить это на проверенный manifest сервера 1.

## Evidence и продолжение

Первый targeted pool/capacity/Celery recovery: **13 passed**, 1 warning, 15,62 s. Затем добавлены 11 unit cases для реальных строковых memory units Compose; полный regression фиксируется после прогона. Actual Compose gate успешно прочитал units и выдал указанные totals; вариант API-2 завершился exit 1 по правильной причине.

Финальный source-bind regression: **406 passed, 1 skipped, 1 deselected**, 47 warnings, 77,52 s. Чистый committed image `admirra-devops:9bfa49a` без source-bind: **406 passed, 1 skipped, 1 deselected**, 47 warnings, 78,26 s. Image ID `sha256:1c1cb690297f16e451c9b3e33551ac6c271f699b9cea7e3336f0083769c05779`, release label `9bfa49a`. Это regression выбранного backend-набора, не load acceptance.

Следующие части T03: измеримый idle/mixed/peak worker load на восстановленной БД, RSS/PSS/AOF/DB pool наблюдение и stop-критерии; затем manifest сервера 1 и полный resource/load acceptance. Общий production cutover и offsite restore по-прежнему gated.
