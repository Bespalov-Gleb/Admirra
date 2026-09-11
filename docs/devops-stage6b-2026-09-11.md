# 6B — приватный файловый сервис и storage adapter

T02 / FILE-01, FILE-02, часть FILE-04. **Подготовлено**, не включено на production. Это файловый транспорт; PostgreSQL metadata/tenant scope и подключение существующих producers — следующий пакет. T02 целиком не закрыт.

## Реализация

- `core/artifact_storage.py`: объекты с UUID-ключом, SHA-256 и размером. Никаких произвольных путей/URL/имён от пользователя.
- `backend_api/artifact_store.py`: отдельное приложение без импорта production DB/settings, schedulers, рекламных API и AI.
- `ops/artifact_server.py`: обязательная взаимная TLS-аутентификация (`CERT_REQUIRED`, TLS ≥1.2). Обычный `uvicorn backend_api.artifact_store:…` без этого entrypoint не является разрешённым deployment.
- `core/artifact_client.py`: проверка CA и server hostname, клиентский сертификат + отдельный role credential в Authorization; trust_env=false, redirects=false. Role credential не помещается в URL. Тексты upstream ошибок/секреты наружу не передаются.
- `ops/compose.storage.yml`: подготовленный отдельный service с bind только `10.77.0.1:9443`, non-root, read-only root, отдельным каталогом artifacts, ресурсными лимитами. На узлах **не запускался**, firewall/CA/credentials ещё не устанавливались.

## Права и граница доверия

Дополнительно к mTLS приложение проверяет случайный bearer по SHA-256 из закрытого server-side JSON. Роли: `read` — чтение; `writer` — чтение/создание; `maintenance` — чтение/логическое удаление. Writer не может удалять, maintenance не может создавать. JSON содержит идентификатор principal, role и hash; исходные credentials находятся только в закрытых клиентских файлах.

Это **сервисная** авторизация. Прежде чем вызывать adapter, основной API/worker обязан проверить tenant/scope в PostgreSQL; владение UUID само по себе не даёт пользователю прав. Файловый API не монтируется в публичный backend router. Service certificate и role credential — два независимых требования; роль определяется credential, не CN сертификата.

Корневой каталог и его родители — операторский mount, недоступный другим runtime-приложениям напрямую. Все операции открывают ключи относительно directory FD с `O_NOFOLLOW`, проверкой regular file и отсутствия чужих hardlinks. Временные файлы — в отдельном `.uploads`, чтобы очистка не сканировала все опубликованные объекты.

## Публикация, повторы, удаление

1. До вызова транспорта caller готовит неизменяемые expected size/hash/key (следующий пакет связывает их с DB state).
2. Запись в эксклюзивный временный файл 0600, циклический `os.write` с обработкой short writes, подсчёт фактических size/hash.
3. Несовпадение или превышение declared size не публикует объект. `fsync` файла → stripe flock → проверка immutable UUID → atomic rename → `fsync` обоих каталогов.
4. 256 фиксированных stripe lock-файлов ограничивают их число и сериализуют конкурирующие mutations между процессами. Тот же UUID с теми же bytes — идемпотентно; с другими — 409. Читатель не видит частичный файл.
5. Delete сохраняет `.deleted` tombstone вместе с прежними bytes. Отложенная загрузка не может оживить удалённый UUID. Если объекта ещё не было, ставится пустой tombstone. Физическое удаление готовых/tombstoned bytes **не реализовано и не запускается** до reference/backup/PITR retention из следующих пакетов.
6. `cleanup_parts` удаляет ограниченное число старых временных файлов; flock открытого upload защищает живую загрузку. Cleanup не удаляет опубликованные объекты/tombstones. Автоматического расписания пока нет.

## Ограничения ресурсов и ошибки

Максимум 50 MiB на объект, четыре одновременных upload, 60 s на загрузку, server concurrency 12. На хосте по умолчанию сохраняется минимум 512 MiB свободного места сверх ожидаемого файла; фактический ENOSPC также обрабатывается. Это защита ресурсов, а не новая продуктовая квота тарифов. Перед включением проверить реальные PNG sizes и capacity.

Download проверяется adapter **до передачи bytes вызывающему коду**: spool во временный файл, size/hash из доверенной metadata, запрет неожиданного encoding. Ошибочная длина/hash — ObjectCorrupt; missing — ObjectMissing; недоступность/TLS/credential/неожиданный HTTP — StorageUnavailable. Ответы stat/put ограничены 4 KiB. HTTP timeouts/pool limits заданы отдельно, у download есть общий deadline.

GET/read-only операции не публикуют новые файлы. Прерывание upload оставляет максимум закрытый временный файл для recovery, не successful reference. Авария машины/питания не равнозначна SIGKILL процесса: fsync-протокол реализован, power-loss/restore acceptance ещё предстоит.

## Проверено

`tests/test_artifact_storage.py`: **26 passed**, 1 warning, 4,68 s на сервере 2 в изолированном backend test container. Только synthetic temp files, отдельные test certificates, loopback TLS-сервис без внешних портов/production secrets.

Проверены UUID/path/symlink/hardlink, size/hash/short write/ENOSPC/disk reserve, idempotence, 8 конкурентных publishers, tombstone против inflight upload, SIGKILL частично записавшего процесса и cleanup, отдельные клиенты и перезапуск реального TLS-сервиса, отсутствующий/чужой/истёкший сертификат, неверный bearer, запрет writer delete, отказ от redirect/неверного encoding/повреждённого download.

Эти проверки не объявляются проверкой двух production API или всех producers. Пока приложение не использует adapter и storage service на production не включён.

## Следующие действия без повторного согласования пакета

1. Metadata/state/references в PostgreSQL, короткие транзакции reserve → upload → finalize, crash reconciliation и tenant checks.
2. Подключение существующих report artifacts, устойчивых file links и публичных uploads с сохранением старых URL/политик доступа.
3. Контролируемое certificate enrollment/rotation и установка в изолированный межхостовый стенд. CA private key не отдавать API/worker/storage.
4. Проверка полного image, миграций, backup consistency, fault/load/resource evidence; только затем activation по общим gates.

Rollback подготовительного пакета: действующие сервисы его не используют; не трогать текущие production DB/файлы. После будущей activation выключать producers и сохранять metadata/объекты, а не удалять каталог ради отката.

Технические основания: [Python os: dir_fd, rename, fsync](https://docs.python.org/3/library/os.html), [HTTPX: SSL/client certificates](https://www.python-httpx.org/advanced/ssl/), [HTTPX streaming API](https://www.python-httpx.org/api/).
