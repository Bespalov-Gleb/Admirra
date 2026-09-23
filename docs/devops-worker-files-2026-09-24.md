# Окружение воркеров и общие файлы — 24.09.2026

Первые два пункта подготовки выполнены. **Это не запуск новых consumers и не
полное переключение production.** Рабочие API/automation/frontend, схема
`cc3d4e5f6a7b`, admission и доля API-2 не менялись. Новым постоянно работающим
сервисом стал только приватный файловый транспорт; новые очереди не потреблялись.

## 1. Worker runtime

На server 2 установлены закрытые `/etc/admirra/worker.env`, `scheduler.env`,
`worker-secrets/google-service-account.json`, клиентские TLS credentials.
Источник — фактическое окружение работающего automation, не старый git checkout
или полный `.env`. Передача — SSH pipe без сохранения секретов на ноутбуке/в git.

- DB URL заменён на существующую роль `admirra_worker`: не superuser, нет
  CREATEDB/CREATEROLE, connection limit 20. Проверено реальным read-only SQL.
- Redis: существующие отдельные broker/limiter/cache worker ACL, три PING
  прошли. Ключи/ACL не ротировались, Redis не перезапускался.
- Проверены Fernet key и разбор Google service account без запроса к Google.
- Scheduler получил только DB env и Redis env: без AI/платёжных/почтовых ключей,
  без файловых mounts. Он только планирует calendar/outbox.
- Compose `format: raw` сохраняет `$`, `#` и JSON в значениях без интерполяции.
- Все процессы non-root 10001, read-only root, tmpfs, no-new-privileges, cap drop,
  ограниченные CPU/RAM/SQL pools. Полный render с настоящими env проверен без
  вывода env. Лимиты сохранены: manual/nightly 1280 MiB/1.5 CPU, reports и
  maintenance 768 MiB/1 CPU, scheduler 256 MiB/0.5 CPU. Pool 2 без overflow.
- Проверка `work_preflight.check()` с env scheduler корректно отказала из-за
  текущей старой schema, **до** calendar/claim/publish. Схему ради теста не меняли.

Подготовленный Compose — `ops/compose.workers.yml`. Immutable application image
остаётся `a5635d5`, digest
`sha256:5642c39fa1134a840e4b3f3657ffb2c77de232c8ed6e631c21a353189cc2075c`.
Ops scripts тестировались source-overlay; они не выдаются за новый backend image.
Полный прежний regression этого image — 1606 passed, см. preflight 23 сентября.

## 2. Общие файлы без S3

### Новые immutable отчёты

На server 1 работает `admirra-artifacts-storage-1`, только
`https://10.77.0.1:9443`. Каталог `/srv/admirra/artifacts`, владелец 10001.
Обязательные mTLS + отдельный role bearer. API1/API2/worker — writer; удаление
только отдельным maintenance principal. CA private key находится в
`/etc/admirra/artifact-pki`, не смонтирован в сервис/клиентов.

Server и client leaf certificates выданы на год, CA на пять лет. Срок leaf
истекает 23.09.2027 UTC; renew-before записан в root-only `enrolled.json`.
Ротация — отдельная операция, enrollment отказывается перезаписывать PKI.
Для обычного обновления leaf использовать ту же CA, проверить новые cert/key
и права 0640 root:10001, обновить соответствующий client mount и перезапустить
его consumers после drain; storage server certificate требует его restart.
Смену самой CA выполнять с overlap доверия, не заменять все ключи вслепую.

Исправлен обнаруженный runtime gap: Docker 29 не публикует порт сети
`internal:true`. Теперь выделенный bridge `admrfiles0`, bind приватного IP,
IPv4/IPv6 INPUT/DOCKER-USER guards и запрет NEW egress из этого bridge.
Runtime сервис не имеет DB/provider credentials и не инициирует внешние запросы.

### Старые uploads и приватные файловые журналы

Legacy bridge — NFSv4.2 **только внутри WireGuard**. Это не rsync-копии: оба
узла видят одни и те же bytes. Существующий `/root/Admirra/uploads` сохранён,
через bind mount представлен как `/srv/admirra/shared/uploads`. Второй bind —
`/srv/admirra/rejected-leads` → `/srv/admirra/shared/rejected-leads`.

Экспорт разрешён только `10.77.0.2`, `sync`, `all_squash`, uid/gid 10001,
без удалённого root. NFS3/UDP отключены. Server слушает 10.77.0.1:2049.
Порты RPC/NFS/storage закрыты firewall снаружи **на обоих** серверах.
Исходные owner uploads не изменены: добавлен ACL для uid 10001 и default ACL;
предыдущий ACL сохранён в `/etc/admirra/uploads-acl-before-shared.txt`.

Worker mounts используют Docker NFS volumes с `nocopy`, `hard`,
`nosuid,nodev,noexec`: при невозможности mount не возникает запасной пустой
локальной папки. Uploads для workers read-only, rejected-leads read-write.
Для будущего API2 подготовлен `ops/compose.shared-api-files.yml` с RW uploads
и его собственным mTLS principal; **к живому canary override не применён**.
Путь `/app/uploads` сохраняется для совместимости старых URL/brand.

Проверенные настройки основаны на [exports(5)](https://www.man7.org/linux/man-pages/man5/exports.5.html)
и [nfs(5)](https://www.man7.org/linux/man-pages/man5/nfs.5.html).
`hard` выбран ради целостности данных; при отказе file host файловая операция
может ждать восстановления. Это ограничение нужно учитывать в load/recovery,
а не менять на `soft` и рисковать повреждением записи. Server 1 остаётся SPOF.

### Карта файлов

| Данные | Хранение / доступ | Что осталось при cutover |
| --- | --- | --- |
| Аватары, логотипы | Один существующий uploads, NFS для API2, старые URL | Применить API2 mount override к новому release |
| Report PDF/PNG, новые file links | Private immutable objects + DB metadata/ref scope | Migrations, flags и scoped copy/verify; старые DB blobs не удалять |
| Старые report file/view tokens | Legacy process cache или существующий DB delivery | Drain/TTL или сохранение legacy route, не случайный round-robin |
| Вложения ассистента | Исходник не сохраняется; извлечённый текст в БД | Общая БД; не нужен перенос оригиналов |
| Экспорт ответа ассистента DOCX/MD | Генерация по запросу/временные bytes | Не делать temp path межрепличным контрактом |
| Rejected-lead журналы | Приватный общий каталог вне public uploads | Подключить API1 путь в candidate, сохранить legacy журнал если появится |

## Проверки и эксплуатация

- Окончательный isolated target: **84 passed, 17 warnings, 7.02 s**, exit 0.
  Включает runtime preparation, PKI, private services, capacity, storage,
  backup receiver/restore safety. Это не полный повтор manifest и не нагрузка.
- Все **33** существующих uploads, **379 363 bytes**, одинаковы с обоих узлов:
  manifest SHA256 `05dc270cf6cdfe9a3fc8cee413978bc1a69e7b39e2555494d8b178ba31df1201`.
- Synthetic NFS write server2 → read server1, затем запись из настоящего
  Compose runtime maintenance под uid 10001 → read server1 прошли; markers удалены.
- Synthetic artifact API1 → worker/API2 read, storage restart → API2 read,
  worker → API1 read, запрет writer delete, maintenance delete → missing прошли.
  Без client certificate TLS отвергается; без bearer — 401. Никаких клиентских
  документов/отправок/платежей эти проверки не создавали.
- Извне TCP 111/2049/20048/9443 недоступны на обоих публичных IP; приватные
  чтения прошли. Host guards сохраняются systemd, SSH/web policy не менялась.
- Health timers на обоих узлах каждую минуту: mTLS health, systemd mounts,
  срок сертификатов. Prometheus получил `admirra_shared_files_up=1` с обоих.
  Добавлены unavailable/stale/cert-expiring правила; promtool принял 26 rules.
- Владелец подтвердил получение **всех четырёх** прежних Telegram тестовых
  уведомлений (Alertmanager и внешний heartbeat, проблема/восстановление).
  Повторная рассылка тестов не требовалась. Offline recovery key не подтверждён.
- Финальный inventory: только прежние API/automation/Redis и новый storage;
  worker/scheduler consumers отсутствуют. Test containers/network удалены.
  Production image digests прежние, restart counters 0, сайт HTTP 200,
  Prometheus active alerts пуст. Лог 84 tests сохранён root-only на server2:
  `/opt/admirra-staging/runtime-prep/verified-tests.log`.

Операционные исходники и Compose для продолжения лежат на обоих узлах в
`/opt/admirra-file-ops/ops/`. Конфиги/секреты — отдельно в `/etc/admirra`.

## Backup и восстановление

Backup теперь включает immutable artifacts, private rejected-leads, ACL и
закрытый PKI/конфиги. Worker env/Sheets/DB/Redis recovery material скопирован
закрытым SSH pipe в `/etc/admirra/worker-host-recovery` на server 1, откуда
попадает в encrypted runtime backup на server 2. Обновлять эту recovery-копию
после ротации worker/Redis credentials; не считать её онлайн-синхронизацией.

Новый backup **`20260923T211209Z-729f038c`**, schema `cc3d4e5f6a7b`, sender success.
Закрытая streaming decrypt-проверка на server2 подтвердила пять обязательных
storage/recovery путей и SHA256 synthetic artifact. Секреты не печатались.
Это приёмка нового содержимого архива, не повторная полная clean-host DB restore;
предыдущая полная restore/migration/API/worker boot приёмка — 65 s, 23 сентября.

При восстановлении: сначала DB/immutable objects/PKI и legacy uploads из
проверенного набора, затем вернуть uid/gid и uploads ACL (`tar --acls` либо
повторно `setfacl`); поднять private link/firewall/bind mounts/NFS/storage;
только после checksum/health подключать API/workers. Не удалять objects,
tombstones, metadata или CA ради rollback. Все новые hosts в этой процедуре
пока те же два сервера, не offsite и не полноценная HA.

## Следующий этап (не выполнен здесь)

1. Общая межсерверная mixed-load/recovery приёмка API + очередей + файлов,
   cache revisions/SSE и совместимого rollback, с ограниченными тестовыми scope.
2. Затем согласованный cutover: fresh backup/preflight → admission/drain →
   остановка **единственного legacy automation + встроенных API schedulers** →
   migrations → candidate API1/minimal consumers → **один** work_control →
   проверенная E2E задача → admission → API2 canary по ступеням.

Не выполнять blanket `docker compose up` текущего server checkout. Legacy и
новый календарь не должны работать одновременно. Итоговый flags manifest
API/workers проверяется совместно при load/cutover, а не включается одним узлом
раньше остальных. S3 и две ночи ожидания по решению владельца отложены.
