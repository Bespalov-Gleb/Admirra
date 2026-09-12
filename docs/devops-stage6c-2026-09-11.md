# 6C — DB lifecycle, привязки отчётов и file capabilities

T02 / FILE-02–04, опорный контракт T09. **Подготовлено**; migration на production не запускалась, API/worker на новую схему не переключались.

## Новый контракт

`backend_api/artifact_ledger.py`, `artifact_workflow.py`, migration `bc8d9e0f1a2b` (parent `ab7c8d9e0f1a`). Prepared worker-compose ожидает новый head; старые работающие контейнеры это не меняет.

- `stored_artifacts`: UUID/key, creator/account, точный project scope, вид report PDF/PNG/DOCX, size/hash, идемпотентный request hash, state/generation/lease и времена.
- `report_artifact_refs`: delivery+format → конкретный artifact и source revision hash. FK не позволяет потерять referenced metadata; удаление delivery убирает только reference, не filesystem bytes напрямую.
- `artifact_public_links`: `f1_` capability, hash токена, создатель, artifact, TTL ≤24 h, отзыв. Создание только для собственного ready artifact после проверки текущих project/account прав; возврат должен происходить после commit вызывающего слоя. Это внутренний контракт; HTTP wiring идёт следующим пакетом.

Workflow: вычислить size/hash в ограниченном входном файле → отдельная короткая reserve-транзакция → storage.put **без SQL connection** → отдельная finalize-транзакция с повторной авторизацией и fencing generation. Неизвестный результат storage.put оставляет uploading, повтор с тем же request key восстанавливает тот же immutable UUID. Другие bytes/scope/kind под тем же ключом отклоняются.

Upload lease 15 min. Продление истёкшей lease увеличивает generation; старый finalizer не публикует ready. После GC claim state=deleting поздние upload finalizer/reference/link не могут воскресить объект. Недоступный/пропавший storage при повторе ready не выдаётся за успешную идемпотентность.

Ресурсная защита: account quota checks сериализованы PG advisory lock, максимум 8 pending uploads, по умолчанию 2 GiB referenced/uncollected metadata bytes на account; размер настраивается `ARTIFACT_ACCOUNT_MAX_BYTES`. Это пока выключенная эксплуатационная граница нового режима, не изменение тарифов; перед включением инвентаризировать фактический объём и задать capacity. Failed/unknown uploads не освобождают квоту до согласованной cleanup.

## Cleanup и ссылки

Unbound ready objects живут минимум 2 суток; report references и активные public links защищают объект от GC. Metadata cleanup ограничен 50 строками (max 100), использует SKIP LOCKED и повторную проверку references в **новом READ COMMITTED statement после row lock**. Это защищает от присоединения отчёта между выборкой кандидата и удалением.

Claim → commit → storage logical delete/tombstone → отдельный metadata commit. При гибели между transport delete и commit повтор после lease делает то же идемпотентное удаление. Старый generation не завершает чужую cleanup. Physical bytes/tombstone purge и расписание не включены: сначала общий retention/PITR/reference drill.

При удалении пользователя metadata остаётся с NULL creator/account для последующей cleanup, не исчезает вместе с единственной записью о файле. Доступ к orphaned metadata запрещён; старые чужие account grants не переиспользуются.

## Проверки и границы

`tests/test_artifact_ledger.py` использует настоящий изолированный PostgreSQL и файловый adapter. Первый прогон: 9 passed, 1 warning, 11,86 s. Добавлены ещё две проверки: отзыв текущих прав для file capability и запрет late attachment после GC claim; итоговый результат записывается при общей приёмке.

Итоговый source-bind regression: **357 passed, 1 skipped, 1 deselected**, 47 warnings, 76,93 s. Включает все 11 новых ledger-тестов и 26 storage-тестов пакета 6B. Skipped — прежнее optional differential сравнение; deselected — прежняя проверка Vue-файла вне backend package.

Проверка committed image `admirra-devops:d9229ac` без source bind: **357 passed, 1 skipped, 1 deselected**, 47 warnings, 73,61 s. OCI revision `d9229ac`, image ID `sha256:7c9998df7a9a38c9970c63861ff465d202555b79f3d0cf908deca0828829fc87` (повторно проверен 12.09). Production app остаётся на `cdf0a4d`.

Проверяются: отсутствие checked-out SQL connections во время IO, неизвестный результат upload → безопасный retry, idempotency mismatch, concurrent reservation/quota, lease renewal/fencing, crash cleanup, pinning ссылками/отчётами, checksum descriptor, отзыв прав между upload и finalize, guard downgrade.

На этом этапе существующие PDF/PNG bytes в ReportDelivery не удалены и не перегенерированы. Их старый DB read path сохранён; старые public tokens не переизданы. Следующее: безопасное HTTP wiring, явная фиксация scope новых snapshots, copy+verify existing report artifacts, затем uploads/legacy migration. Полностью T02 пока не закрыт.
