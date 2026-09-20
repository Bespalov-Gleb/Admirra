# Backend release candidate 14c99d0

Дата проверки: 20.09.2026. Статус: проверенный immutable candidate, **не включён** в production runtime.

## Источник и артефакт

- Ветка: `metrics-fallback-fix`.
- Commit: `14c99d0`.
- Исходный архив создан `python3 -m ops.package_backend ... --revision 14c99d0`: 415 tracked runtime/test files, 852 KiB.
- Архив не содержит `.env`, `.git`, secrets, uploads, frontend/landing, debug scripts, probes, dumps или private keys.
- Image: `admirra-devops:14c99d0`.
- Image ID: `sha256:6aaaf82130131601b12fdbff626480588738256b962732a7b66faf8e1c947ad2`.
- OCI `org.opencontainers.image.revision=14c99d0`; `pip check` успешен.
- Сборка и закрытые логи находятся на сервере 2 в `/opt/admirra-staging/14c99d0/`.

Сборка не использовала dirty working tree. Пользовательские незакоммиченные frontend/landing-файлы и отдельный untracked regression-файл сохранены без изменений и не попали в image.

## Изолированная проверка

Запускался сам image без source bind, как non-root/read-only container, с synthetic PostgreSQL 15.18 и Redis 7.4.11 во внутренней Docker-сети. Production credentials, production DB и outbound provider calls недоступны.

Результат: **587 passed, 1 skipped, 1 deselected, 47 warnings, 6 subtests passed**, 136,95 s.

В актуальный manifest добавлены существующие tracked-тесты API-2 monitor, AI attachments/exports, VK assistant reporting, billing slot purchase, mobile plan progress, team router и OAuth/link flows. Test containers/network после прогона остановлены и удалены; production API-2/Redis/exporters не затрагивались.

## Schema gate

- Production Alembic revision: `cc3d4e5f6a7b`.
- Candidate Alembic head: `bc8d9e0f1a2b`.
- Ожидающие additive migrations: durable jobs/outbox, report route guards, history backfill state, durable public report links и artifact lifecycle.

Зашифрованная recovery point `20260920T151415Z-e003a617` реально восстановлена в isolated PostgreSQL; все пять миграций candidate до `bc8d9e0f1a2b` применились за один транзакционный rehearsal, девять новых таблиц подтверждены. Production DB не изменялась. Candidate всё ещё нельзя подставлять вместо текущего API/automation или запускать как worker до полного G3/cutover: внешний offsite/PITR, secrets/files recovery и end-to-end restore остаются открыты. Старый production runtime остаётся без изменений; API-2 canary продолжает использовать production-compatible image.

## Следующий безопасный шаг

Подключить внешний immutable repository/PITR и включить backup shared files/secrets, затем выполнить end-to-end application restore. После полного G3 — отдельное окно production migration и single-API durable-worker rollout.
