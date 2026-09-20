# Restored read/API + worker boot load evidence

Дата: 20.09.2026. Scope: изолированный server 2, production не изменялся.

## Среда

- Recovery point: `20260920T155915Z-e639b5d3`, полный encrypted DB/runtime/release-manifest set.
- Candidate: `admirra-devops:acf6ed8`, image `sha256:ad9559725e724789281765526f85839b8b9adf604c114ad25850812b0c544d0a`.
- PostgreSQL восстановлен с `cc3d4e5f6a7b`, затем пять migrations до `bc8d9e0f1a2b`.
- API: один process, pool `5/0`, read-only rootfs, UID 10001.
- Одновременно запущены manual 2, nightly/backfill 2, reports 1, maintenance 1 и одноразовый Redis. Все workers прошли preflight/ready/Celery ping.
- Весь набор разделял `network=none`; scheduler, business jobs, SMTP, AI, Wordstat, external providers и клиентские доставки не запускались.
- Для авторизации выбран active+verified владелец с максимальным числом проектов в восстановленной БД; email, UUID, token и тела ответов не логировались.

## Нагрузка и результат

После одного warm-up каждого маршрута выполнено по 8 запросов:

- `/api/auth/me`;
- `/api/clients`;
- `/api/folders`;
- `/api/notifications`;
- `/api/dashboard/summary` за 14 дней, `platform=all`.

Итого: 40 запросов, concurrency 4, **40 × HTTP 200**, duration 2,092 s, 19,12 req/s, p50 129,36 ms, p95 692,12 ms, max 807,58 ms. Полный restore + migrations + worker/API/read-load smoke занял 44 s. После trap cleanup осталось 0 restore containers/volumes/runtime directories.

Предыдущий отдельный API-only запуск после холодного восстановления также дал 40/40 HTTP 200: 8,25 req/s, p50 532,39 ms, p95 1171,51 ms, max 1315,03 ms. Эти два запуска показывают диапазон cold/warm filesystem/DB cache, а не гарантированный production SLO.

## Что это доказывает и чего не доказывает

Подтверждены: candidate schema compatibility, auth, реальные read-маршруты на production-size snapshot, pool `5/0`, одновременный worker boot и отсутствие ошибок при bounded concurrency.

Не подтверждены: полный browser dashboard fan-out, cache revision/invalidation, фактические manual/nightly provider calls, report rendering/delivery, AI/billing side effects, длительный soak и одновременные пики 03:00/05:00. До production cutover нужен отдельный approved test tenant/provider run и наблюдение RSS/PSS, DB locks/pool, Redis/AOF и quota/failure поведения.
