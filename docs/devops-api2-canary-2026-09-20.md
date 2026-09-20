# API-2 — production read canary на втором сервере

Дата включения: 20.09.2026. Статус: приватная API-реплика включена; ограниченный read-canary получает 10% запросов четырёх маршрутов на `admirra.ru`. Это не полный двухсерверный cutover и не запуск Celery-workers.

## Фактическая схема

- API-1 остаётся в рабочем контейнере сервера 1 с образом `sha256:047c8019bbbeec83c0c8cd11b39c03b31af2931d8e2f0b415196199f8768afe0`.
- API-2 работает на сервере 2 в контейнере `admirra-api2-api-1`, image `sha256:8190db69fe00584ed4d7d84b749ec1933b25938f41cce7b834f45fd786a69ff5`.
- API-2 собран строго поверх активного production image. Скрипт сборки проверяет SHA-256 трёх исходных файлов и прекращает сборку при любом drift.
- API-2 слушает только `10.77.0.2:8001` через WireGuard. `91.221.68.94:8001` недоступен извне.
- PostgreSQL доступен через приватный gateway `10.77.0.1:5432`, роль `admirra_api`. Проверено: DDL/Alembic запрещены, нужные DML-права есть, privileged gateway login отклоняется.
- Пул API-2 ограничен `pool_size=5`, `max_overflow=0`, `pool_timeout=5`. Наблюдалось пять idle-соединений роли `admirra_api` после нагрузки.
- Контейнер: 1 процесс Uvicorn, лимит 1 GiB RAM / 1,5 CPU, restart `unless-stopped`, health `/api/health/live` и `/api/health/ready`.
- В API-2 отключены schema bootstrap, embedded sync worker, scheduler отчётов/телефонии и другие startup jobs. В логах нет их запуска.

## Что получает трафик

Только домен `admirra.ru`, только `GET/HEAD`, только точные маршруты:

- `/api/auth/me`;
- `/api/clients`;
- `/api/folders`;
- `/api/notifications`.

Nginx использует `least_conn`, вес API-1:API-2 = 9:1. Для connection errors/timeouts/502/503/504 разрешён максимум один повтор на второй upstream, что безопасно только для этих read-запросов. Любой другой HTTP-метод внутренне уходит прямо в API-1. `admirra.online`, AI/SSE, файлы, отчёты, OAuth, интеграции, синхронизации, платежи/webhooks и остальные маршруты остаются на API-1.

Канареечный лог: `/var/log/nginx/admirra-api2-canary.log`. Он содержит request ID, method, `$uri` без query string, итоговый status, upstream и timings; Authorization/body в лог не попадают.

## Проверки

- WireGuard и оба Redis работают; API-2 healthy, restart count 0.
- OpenAPI: API-1 — 292 маршрута, API-2 — 294; единственная разница — `live/ready`.
- Под тестовым аккаунтом ответы API-1/API-2 совпали по status и каноническому JSON для auth/me, clients, folders, billing/overview и notifications. Токен/данные в evidence не сохранялись.
- Healthy-canary: 60 публичных авторизованных запросов, все 200 и с одним response hash; распределение 54/6, то есть 10% дошло до API-2.
- Failover: API-2 штатно остановлен, ещё 60 запросов — все 200; четыре попытки API-2 получили upstream 502 и автоматически завершились 200 через API-1. API-2 возвращён в healthy.
- Direct load после ограничения пула: 120 запросов, concurrency 20, 0 ошибок, 173,9 req/s, p50 83,9 ms, p95 251,9 ms, max 306,6 ms. Это короткий synthetic smoke одного небольшого endpoint, не capacity acceptance всего продукта.
- После проверки API-2 использовал около 117 MiB из 1 GiB; на сервере 2 доступно около 7,1 GiB RAM, swap не использовался. Диск после удаления временного transfer archive: 74%, около 4,5 GiB свободно.
- Nginx config валиден, сервис active. Финальных 5xx в 120 контрольных canary-запросах нет.
- Миграции/изменения данных/реальные платежи/рассылки/AI-вызовы не выполнялись.

## Файлы и откат

Репозиторий: `ops/api2_canary/` — проверяемый overlay build, Compose, активный Nginx site, upstream/snippet и скрипты deploy/rollback.

Сервер 2:

- `/opt/admirra-api2/release-20260920/compose.api2.yml`;
- `/etc/admirra/api2.env` и `/etc/admirra/db-api.env`, mode 0600;
- `/etc/admirra/api2-secrets`, mode 0700;
- `/srv/admirra/api2/uploads` — локальный compatibility mount, публичные file routes на API-2 не направляются.

Сервер 1:

- `/root/admirra-api2-canary-20260920/backup/admirra.ru`;
- `/root/admirra-api2-canary-20260920/rollback-canary.sh`;
- `/etc/nginx/conf.d/admirra-api2-upstream.conf`;
- `/etc/nginx/snippets/admirra-api2-read-proxy.conf`.

Откат выполняется в таком порядке:

```sh
sh /root/admirra-api2-canary-20260920/rollback-canary.sh
ssh root@91.221.68.94 'cd /opt/admirra-api2/release-20260920 && docker compose -f compose.api2.yml stop -t 30 api'
```

Откат Nginx проверяет конфигурацию перед reload. БД откатывать не требуется: миграций не было. Сначала убрать реплику из маршрутизации, затем останавливать контейнер.

Временный архив образа и split-части удалены с обоих серверов и локальной машины после проверки digest/load. Одноразовый SSH-ключ server1→server2 удалён с обеих сторон; постоянный операторский ключ установлен на сервере 2.

## Что ещё обязательно до расширения

1. Наблюдать canary error/timing и ресурсы минимум рабочий цикл; подключить central alert на unhealthy/fallback/disk.
2. Отдельно проверить reboot/Docker/WireGuard recovery в согласованное окно.
3. Не добавлять dashboard stats, manual sync и другие маршруты без route-by-route проверки внешних вызовов, process-local state и cross-replica fixtures.
4. До общего round-robin закрыть shared files/tokens, AI run/SSE drain, durable jobs, cache revision и billing/side-effect guards по основному DevOps-ТЗ.
5. Celery workers пока не запускать: прежний полный workers manifest вместе с API-2 не проходил резерв памяти ОС.
