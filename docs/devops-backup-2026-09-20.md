# Encrypted cross-host backup и restore drill

Дата включения: 20.09.2026. Статус: ежедневная зашифрованная логическая копия PostgreSQL на сервер 2 включена и реально восстановлена. Это отдельная recovery point от диска server 1, но **не внешний offsite и не PITR**.

## Схема и защита

- Server 1 запускает `pg_dump --format=custom --compress=6` и `pg_dumpall --globals-only` из действующего PostgreSQL 15.
- Поток шифруется на server 1 посредством `age 1.1.1`; незашифрованный dump на диск не записывается.
- Private age identity существует только на server 2: `/etc/admirra/backup/age.key`, root, mode `0600`. Server 1 имеет только публичный recipient.
- Передача идёт по SSH через WireGuard на `10.77.0.2` с закреплённым Ed25519 host key.
- Unix-пользователь `admirra-backup` имеет forced command и OpenSSH `restrict`: ключ sender не открывает shell/forwarding, не читает и не удаляет repository; он может только создать новый объект с валидным уникальным ID.
- Receiver запрещает path/shell injection, overwrite, symlinks, пустые и oversized objects; пишет через private partial file + fsync + atomic hard-link.
- Repository: `/var/lib/admirra-backup/postgres`, owner `admirra-backup`, mode `0700`.

Рабочие DB credentials в backup transport не передаются и в логах не появляются. Global roles находятся только внутри зашифрованного объекта.

## Первая recovery point

Backup ID: `20260920T151415Z-e003a617`.

- исходный размер production DB: 842 407 271 bytes (803 MiB);
- encrypted database object: 47 088 184 bytes;
- encrypted globals object: 2 915 bytes;
- encrypted manifest: 498 bytes;
- schema cutoff: `cc3d4e5f6a7b`;
- сервис завершился успешно, заметного DB resource spike после завершения нет.

В manifest зашифрованы object receipts с размером и SHA-256. Restore до расшифровки сверяет оба encrypted objects; `age` дополнительно аутентифицирует ciphertext.

## Расписание, retention и мониторинг

- `admirra-logical-backup.timer` на server 1 включён: ежедневно 22:00 UTC + случайная задержка до 15 минут; service ограничен `CPUQuota=50%`, low IO priority и `Nice=10`.
- `admirra-backup-prune.timer` на server 2 включён: ежедневно 23:30 UTC + случайная задержка до 15 минут.
- Retention сохраняет последние 7 дневных, 4 недельных и 3 месячных bucket; самый новый complete set сохраняется всегда. Неполные наборы удаляются только старше 24 часов. За один запуск нельзя удалить больше 100 объектов.
- API-2 health guard публикует `logical_backup_complete_sets` и `logical_backup_age_seconds`.
- Prometheus имеет 20 валидных rules; `AdMirraLogicalBackupStale` срабатывает при отсутствии complete set или возрасте более 30 часов. После включения complete sets = 1, alert set пуст.

Фактический заявляемый RPO этого этапа — примерно сутки, не 15 минут. Timer `Persistent=true`: пропущенный запуск выполняется после восстановления узла; duplicate object ID запрещён.

## Restore и migration rehearsal

`restore_logical_backup.sh` проверяет manifest/checksums, расшифровывает поток прямо в отдельный PostgreSQL 15.18 container без host ports и с `network=none`. Temporary container и Docker volume удаляются и при успехе, и при ошибке.

Подтверждены два запуска:

1. Restore `20260920T151415Z-e003a617` до исходного `cc3d4e5f6a7b`, базовая schema/data consistency — pass, 21 s.
2. Новый restore той же recovery point и миграционный job из чистого candidate image `admirra-devops:14c99d0`: пять миграций `cc3d4e5f6a7b → bc8d9e0f1a2b`, все девять ожидаемых таблиц существуют — pass, 21 s суммарно.

Production DB и работающие API/automation при этом не изменялись. Это доказывает совместимость миграций с текущим снимком, но не является production migration approval.

## Эксплуатация

Ручной backup:

```sh
systemctl start admirra-logical-backup.service
journalctl -u admirra-logical-backup.service --since today
```

Restore rehearsal на server 2:

```sh
/opt/admirra-backup/release-20260920/restore_logical_backup.sh BACKUP_ID
```

Migration rehearsal:

```sh
/opt/admirra-backup/release-20260920/restore_logical_backup.sh \
  BACKUP_ID admirra-devops:14c99d0 bc8d9e0f1a2b
```

Остановка расписаний не удаляет recovery points:

```sh
systemctl disable --now admirra-logical-backup.timer
systemctl disable --now admirra-backup-prune.timer
```

## Что ещё не закрыто по BACKUP/G3

1. Repository остаётся на втором рабочем сервере того же контура. Нужны внешний S3/object storage в другом fault/administrative domain, versioning/immutability и отдельные writer/restore/delete credentials.
2. Логический daily dump не даёт PITR/RPO 15 min. После выбора external storage нужны pgBackRest/WAL-G либо проверенная base backup + continuous WAL схема и alert на archive backlog.
3. Не резервируются shared artifacts/uploads, runtime secrets/encryption keys, release manifests и необходимый Redis AOF. Ключ восстановления age сам нуждается в независимом защищённом escrow: сейчас потеря server 2 делает эти dumps нечитаемыми.
4. Проверено восстановление DB и миграций, но не полный clean application restore с outbound payments/messages/AI disabled и сверкой файлов/токенов.
5. RTO 21 s относится только к DB restore/migration в уже готовом локальном окружении; end-to-end RTO ≤60 min пока не доказан.

До закрытия этих пунктов G3 считается частично выполненным, а не полным production disaster recovery.
