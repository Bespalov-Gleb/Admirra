# Этап 5: приватный PostgreSQL, Redis и ограниченные сервисные учётные записи

## Границы изменений

На двух серверах включена инфраструктура безопасного обмена. Это ещё **не**
переключение приложения на Celery/новый runtime и **не** балансировка двух API.
Production-приложение остаётся на `cdf0a4d`; его env, nginx, бизнес-данные,
расписания, отправки отчётов и платежи не изменялись. Контейнер PostgreSQL не
пересоздавался. В самой production-БД добавлены роли и права, а HBA перечитан
без разрыва существующих соединений. Это реальные инфраструктурные изменения,
не только подготовленные файлы.

Независимый backup пользователь организует отдельно. Копия HBA ниже — резерв
одного конфигурационного файла, **не резервная копия БД**.

## Работающие сервисы

| Узел | Компонент | Доступ |
| --- | --- | --- |
| Сервер 1, 91.221.68.90 | PostgreSQL, прежний контейнер | Внутри прежней Docker-сети |
| Сервер 1 | Новый HAProxy TCP-вход в PostgreSQL | Только `10.77.0.1:5432` |
| Сервер 2, 91.221.68.94 | Redis broker + лимитер внешних API | Только `10.77.0.2:6379` |
| Сервер 2 | Redis read-cache | Только `10.77.0.2:6380` |

WireGuard `admirra0` соединяет эти приватные адреса. Default route/DNS не менялись.
HAProxy не заменяет веб-nginx и не балансирует HTTP: сейчас он только добавляет
TCP-вход к работающей БД, чтобы не перезапускать её ради публикации порта.
Backend разрешается по Docker DNS (`db`, обновление адреса), а адрес самого proxy
зафиксирован `172.18.0.250` в существующей сети `admirra_default` / `172.18.0.0/16`.
Адрес проверен на отсутствие конфликта до запуска; он важен для HBA.

Образы закреплены digest:

- Redis 7.4 Alpine: `sha256:ff02b58f971e7d7d156a1267e283fcbbeee91773b6aa36c49dac28ecfe28eadf`;
- HAProxy 3.2 Alpine: `sha256:6343ce34a132a5dceaa24767d739df2bd519f8f7c1079ae39e4821334e8eb42e`.

Broker: AOF `everysec`, `noeviction`, Redis memory cap 256 MB / container 512 MB,
именованный том `admirra-workers_broker-data`. Cache: без persistence,
`allkeys-lfu`, 128 MB / container 256 MB. Это одиночные экземпляры, не HA-кластер.
При отказе broker задания восстанавливаются из PG ledger после включения новой
схемы; провайдерный limiter fail-closed. Работающее legacy-приложение их ещё не использует.

## Firewall

`ops/private_firewall.py` добавляет только собственные цепочки `ADMR-PRIV-IN`
и `ADMR-PRIV-FWD` и hooks для TCP 5432/6379/6380. Учитываются IPv4 и IPv6,
host INPUT и Docker DOCKER-USER. Публичный интерфейс блокируется для этих портов;
на WireGuard допускается только адрес второго участника. Loopback и внутренний
Docker-трафик не блокируются. Ответный трафик не затрагивается (`ctdir ORIGINAL`).

Default policies, SSH 22, веб-порты 80/443 и существующие публикации 8001/8080
не менялись. Это **точечная защита приватных сервисов**, не полный hardening хоста.
Существующие прямые публикации backend/frontend предстоит отдельно ограничить
при настройке окончательного nginx ingress и проверке всех потребителей.

Правила повторяемы; сервисы `admirra-private-firewall@1` и `@2` включены в systemd.
Они запускаются после Docker/WireGuard и связаны с перезапуском Docker.
Перезагрузку всей production-машины на этом этапе не выполняли: boot/failure drill
остаётся обязательным перед окончательным cutover. Привязка портов к VPN-адресу
и аутентификация действуют независимо от дополнительного firewall.

## PostgreSQL

Созданы `admirra_api` (лимит 30 соединений), `admirra_worker` (20) и общая
NOLOGIN-группа `admirra_runtime`. Нет SUPERUSER/CREATEDB/CREATEROLE/REPLICATION/
BYPASSRLS и владения таблицами. Доступ: CONNECT, USAGE schema, SELECT/DML таблиц
приложения, USAGE/SELECT sequences. `alembic_version` доступен только на чтение;
миграции выполняются отдельно. Default privileges охватывают будущие таблицы,
созданные владельцем `postgres`. Это общие runtime-права приложения, не изоляция
клиентов на уровне PG-ролей: tenant-доступ продолжает проверяться приложением.

Timeouts роли: statement 60 s, lock 10 s, idle-in-transaction 300 s. Финальные
лимиты пулов и влияние таймаутов нужно проверить на настоящей смешанной нагрузке.
Прав PUBLIC/старого postgres и legacy-процессов не лишали.

HBA-блок добавлен **перед** прежними правилами только для proxy IP:

```text
host saas_project admirra_api,admirra_worker 172.18.0.250/32 scram-sha-256
host all all 172.18.0.250/32 reject
```

Через новый вход нельзя войти под postgres, даже при знании его пароля.
Старые контейнеры подключаются напрямую, с прежних IP; их правила сохранены.
Оригинал HBA: `/etc/admirra/pg_hba.before-private.conf` на сервере 1, root-only.
Проверка синтаксиса HBA дала 0 ошибок; `pg_reload_conf()` успешен.

## Redis ACL и секреты

Разные пользователи/пароли для API и workers: `broker_api/worker`,
`limiter_api/worker`, `cache_api/worker`; отдельный `health`.

- Очередь: ключи `admirra:task:*`; ограниченный список команд Kombu и служебных каналов.
- Лимитер: `admirra:rate:v1:*`, нужные GET/PSETEX/TIME/Lua; живёт в noeviction broker.
- Кэш: `admirra:read:v1:*`, GET/SET/DEL/Lua, без доступа к очередям и лимитеру.
- Default user выключен; CONFIG/ACL/FLUSHALL/KEYS и доступ к чужому namespace запрещены.
- Для PSUBSCRIBE прописаны точные шаблоны pidbox/worker events, не `&*`.
  Необходимость проверена настоящим Celery с gossip/mingle; это особенность
  [Redis ACL](https://redis.io/docs/latest/operate/oss_and_stack/management/security/acl/).

Секреты сгенерированы на серверах, не лежат в git/чат-выводе/локальном архиве.
`/etc/admirra` — root 0700, JSON state и `.env` — 0600. ACL-файлы содержат только
SHA-256 hashes и доступны Redis через read-only bind mount; каталог хоста закрыт.
SQL получает SCRAM verifier, не plaintext-пароль. Команды пересылки передают
только выбранный service-env по SSH через память локального процесса, без
локальных файлов и печати содержимого.

Сервер 1: `db-credentials.json`, `db-api.env`, `db-worker.env`, `redis-api.env`.
Сервер 2: `redis-credentials.json`, `redis-api.env`, `redis-worker.env`,
`redis-health.env`, `db-worker.env`, два ACL/config-файла. API-env хранится на
сервере 2 для воспроизводимой генерации, на сервер 1 передана только его копия.
Полный `/etc/admirra/worker.env` **не создан**: реальные воркеры не запускать.
Сервисные файлы сами по себе не переключают старое приложение.

Повторная генерация не меняет пароли и отказывается перезаписывать отличающиеся
файлы. Для обновления только ACL — явный `--refresh-acl`: сохраняется предыдущий
файл, меняются только ACL; затем контейнеры пересоздаются, чтобы bind mount
использовал новый файл. Это не процедура ротации паролей. Потеря credential-state
требует восстановления/согласованной ротации, а не удаления файлов и генерации заново.

## Приёмка

- Реальный доступ из Docker-сети сервера 2 к БД через VPN — успешен.
  Запросы выполнялись с `default_transaction_read_only=on`, без чтения бизнес-строк.
  Проверены роль, права на schema/таблицы, запрет UPDATE alembic_version.
- Вход postgres через gateway отклонён именно HBA, а не только неверным паролем.
- Доступ API-сети сервера 1 к Redis сервера 2 и workers-сети к своим Redis успешен.
- Проверены обязательный пароль, запрет административных команд/чужих ключей.
  Для теста создавались только новые случайные ключи с TTL 1 s.
- С внешнего компьютера все шесть комбинаций public IP × 5432/6379/6380 недоступны.
  Это проверка из конкретной точки, дополненная аудитом bind/firewall; не пентест.
- 10 целевых тестов прошли (8 permissions/config tests + 2 real prefork recovery).
  Во втором аварийном тесте настоящий Celery использует ограниченного broker user,
  штатные gossip/mingle/events; SIGKILL дочернего процесса → rollback и одна запись
  результата после повторных доставок. Тесты используют только изолированные PG/Redis.
- Полный source-bind прогон: **291 passed, 1 skipped, 1 deselected**, 46 warnings,
  25,69 s. Skipped — optional сравнение сводки с baseline, проверенное на этапе 4;
  deselected — тест Vue-файла вне backend image.
- Публичный сайт ответил HTTP 200; пять прежних production-сервисов running,
  HEAD приложения `cdf0a4d`.

### Проверка финального артефакта

Код этапа: `37d8904`. На сервере 2 собран `admirra-devops:37d8904`, image ID
`sha256:57a9c49fe3c11724f560aa6fbc37e0db0c791e9ae28185e8abfe73bc14bf09bc`;
OCI revision — `37d8904`. Полный прогон **из самого образа, без подмены исходников**:
**291 passed, 1 skipped, 1 deselected**, 46 warnings, 24,83 s.
`pip check` — без конфликтов зависимостей; `/app/.env`, `/app/.git` и
`/app/uploads` в образе отсутствуют.

Из финального образа повторно проверены read-only подключение к production-БД
ограниченным worker user и ACL всех трёх Redis-подключений. Из прежней API-сети
сервера 1 повторно проверены Redis-подключения с API credentials. Проверки прошли;
HBA — 0 ошибок. Приватные firewall/WireGuard units на обоих узлах active.
Ops-файлы версии `37d8904` установлены в `/opt/admirra-ops/ops/` на обоих узлах.

Изолированные тестовые PG/Redis остановлены и удалены командой `down` только
тестового Compose-проекта. На сервере 2 остались два healthy Redis-контейнера;
боевые workers/расписания там не запущены. Том broker AOF сохранён.
Повторная внешняя проверка: все 6 приватных портов недоступны из точки проверки;
`https://admirra.ru/` — HTTP 200, 11.09.2026 14:12:36 UTC (17:12:36 МСК).

## Эксплуатация и откат до переключения приложения

Проверенные ops-файлы размещаются отдельно от работающего репозитория:
`/opt/admirra-ops/ops/` на обоих хостах. Конфиги/секреты остаются в `/etc/admirra`.

Повторные проверки: `ops/private_services_check.py` в одноразовом контейнере с
соответствующим `--env-file`; вывод не содержит DSN/паролей.
Внешняя проверка: `python3 -m ops.check_private_port_exposure`.

Пока ни API, ни workers не переключены на новые подключения:

1. На сервере 1 `docker compose -f ops/compose.db-gateway.yml down` из
   `/opt/admirra-ops` закрывает только новый DB-вход, не останавливая PostgreSQL.
2. На сервере 2 `docker compose -f ops/compose.redis.yml down` из того же каталога
   останавливает только новые broker/cache. **Не добавлять `-v`** — сохранять том AOF.
3. Новые роли/точечные HBA/firewall можно оставить закрытыми без влияния на старое
   приложение. Если нужно убрать HBA-блок, удалить только маркированные четыре
   строки, сохранив остальные актуальные правила; проверить `pg_hba_file_rules`
   и выполнить reload. Не подменять целиком файл старым backup при чужих новых правках.
4. Не менять root SSH/пароли, не делать глобальный flush iptables и не удалять
   credentials/state в рамках такого отката. После cutover сначала переключать
   потребителей обратно, а уже затем останавливать инфраструктуру.

## Что ещё не закрыто

Отдельный SSH/deploy-user и финальный hardening; общий доступ к файлам/экспортам;
stateless API-2 и nginx/SSE/drain; миграции и атомарное переключение расписаний;
оставшиеся проблемы sync/SQL/AI/report reconciliation; метрики/уведомления;
смешанная нагрузка, ночной прогон, boot/failure/restore drills и независимый backup.
Redis и PostgreSQL пока остаются единичными узлами: считать эту схему полностью
отказоустойчивой нельзя. Известный CPL-баг Авито из этапа 4 отдельно ещё не исправлен.

Сетевые правила сверены с [Docker/iptables](https://docs.docker.com/engine/network/firewall-iptables/),
права — с [PostgreSQL roles](https://www.postgresql.org/docs/15/role-attributes.html)
и [GRANT](https://www.postgresql.org/docs/15/sql-grant.html), DNS proxy — с
[HAProxy](https://www.haproxy.com/documentation/haproxy-configuration-tutorials/proxying-essentials/dns-resolution/).
