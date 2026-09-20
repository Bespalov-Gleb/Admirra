# Backend release candidate acf6ed8

> Исторический candidate. После ревью подготовлен `45ef70f`; актуальные fixes, tests/restore и незакрытые rollout gates: [devops-review-2026-09-20.md](devops-review-2026-09-20.md). Наличие нового проверенного image не означает разрешённый production cutover.

Дата проверки: 20.09.2026. Статус: проверенный immutable candidate, **не включён** в production runtime.

## Источник и артефакт

- Ветка: `metrics-fallback-fix`.
- Commit: `acf6ed8`.
- Исходный архив создан `python3 -m ops.package_backend ... --revision acf6ed8`: 431 tracked runtime/test files, 881 762 bytes.
- Архив не содержит `.env`, `.git`, secrets, uploads, frontend/landing, debug scripts, probes, dumps или private keys.
- Image: `admirra-devops:acf6ed8`.
- Image ID: `sha256:ad9559725e724789281765526f85839b8b9adf604c114ad25850812b0c544d0a`, size 203 349 851 bytes.
- OCI `org.opencontainers.image.revision=acf6ed8`; `pip check` успешен.
- Сборка и закрытые логи находятся на сервере 2 в `/opt/admirra-staging/acf6ed8/`.

Сборка не использовала dirty working tree. Пользовательские незакоммиченные frontend/landing-файлы и отдельный untracked regression-файл сохранены без изменений и не попали в image.

## Изолированная проверка

Запускался сам image без source bind, как non-root/read-only container, с synthetic PostgreSQL 15.18 и Redis 7.4.11 во внутренней Docker-сети. Production credentials, production DB и outbound provider calls недоступны.

Результат: **603 passed, 1 skipped, 1 deselected, 47 warnings, 6 subtests passed**, 134,66 s.

В актуальный manifest входят tracked-тесты API-2 monitor и bounded Nginx failover, backup/retention, durable workers/outbox, AI attachments/exports, VK assistant reporting, billing slot purchase, mobile plan progress, team router и OAuth/link flows. Test containers/network после прогона остановлены и удалены; production API-2/Redis/exporters не затрагивались. Предыдущий прогон `d7a6fa3` выявил один зависящий от текущего времени backup freshness fixture; clock сделан явным, точечные 5 tests и повторный полный suite прошли.

## Schema gate

- Production Alembic revision: `cc3d4e5f6a7b`.
- Candidate Alembic head: `bc8d9e0f1a2b`.
- Ожидающие additive migrations: durable jobs/outbox, report route guards, history backfill state, durable public report links и artifact lifecycle.

Зашифрованная recovery point `20260920T151415Z-e003a617` реально восстановлена в isolated PostgreSQL; все пять миграций candidate до `bc8d9e0f1a2b` применились за один транзакционный rehearsal, девять новых таблиц подтверждены. Полный набор `20260920T153240Z-574e4117` дополнительно прошёл запуск candidate API с восстановленными `.env`, secrets и uploads, без внешней сети и side effects; readiness и auth guard подтверждены, весь rehearsal занял 24 s. Следующий набор `20260920T155915Z-e639b5d3` содержит проверяемый production release/image/config manifest. Финальный candidate `acf6ed8` на этом наборе прошёл restore, все migrations, version/schema/delivery/legacy-job worker preflight и application smoke за 25 s; текущий production inventory не содержит legacy jobs в `QUEUED/RUNNING`. В расширенном rehearsal одновременно подняты manual/nightly/reports/maintenance workers и isolated Redis, все четыре worker hostname ответили на Celery ping; вместе с API smoke — 41 s, без внешней сети и business jobs. Production DB не изменялась. Candidate всё ещё нельзя подставлять вместо текущего API/automation или запускать как worker до согласованного cutover: внешний offsite/PITR и независимый escrow ключа остаются открыты. Старый production runtime остаётся без изменений; API-2 canary продолжает использовать production-compatible image.

## Следующий безопасный шаг

Подключить внешний immutable repository/PITR и независимый escrow ключа. После полного G3 — отдельное окно production migration и single-API durable-worker rollout; уже пройденный end-to-end restore повторить с будущей внешней recovery point.
