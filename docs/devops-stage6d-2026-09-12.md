# 6D — HTTP файлов отчётов и copy/verify без потери старых ссылок

Часть T02 / FILE-03–04. **Подготовлено, не включено на production.** Production app проверен 12.09: `cdf0a4d`, legacy контейнеры работают, HTTPS `/` = 200. Nginx, рабочие процессы и production-схема в этом пакете не менялись.

## Реализация

- `backend_api/artifact_response.py`: проверенный download, максимум 2 одновременных загрузки на процесс; лишняя получает 503 + Retry-After. Подготовка удалённого файла в ограниченный tempfile завершается с проверкой SHA-256/size **до** отправки HTTP headers. Затем выдача чанками 256 KiB, без загрузки всего файла в RAM.
- Request SQL connection отпускается до файлового IO и передачи медленному клиенту. Файловые handles, tempfile, HTTP client и semaphore освобождаются при завершении, ошибке отправки и отмене. Ответ, который не начал выполняться, не открывает файлов. Shield завершает ограниченную подготовку/cleanup при cancel, не оставляя фонового читателя с потерянными handles.
- `/api/reports/file/{f1_token}` читает hashed capability из БД, повторно проверяет действующие права создателя. Неизвестная/истёкшая/отозванная — 404; storage failure при существующей ссылке — 503. `GET /api/reports/file-links` даёт только owner-scoped management IDs/dates, cursor pagination ≤100; `DELETE /api/reports/file-links/{id}` отзывает ссылку. Токены и scope в listing не раскрываются.
- `save_report_for_link` сохраняет прежний контракт token-return, но в opt-in режиме требует factory, creator и точный project scope. Публикация токена только после storage verification + DB commit. Текущих внешних вызовов этого helper в репозитории нет; он не подменяет ещё не разбитый render/send pipeline.
- PDF builder записывает `_scope_client_ids` из того же списка, по которому агрегировал цифры. Старый aggregate snapshot без такого поля не получает придуманную принадлежность из сегодняшнего состава папки.
- `reports/artifacts.py`: чтение frozen PDF/PNG → reserve/upload/finalize вне длинной SQL-транзакции → повторный row lock/revision check → references. При смене bytes/scope во время копирования привязка не создаётся. Повтор сохраняет те же immutable objects.
- Старые public delivery URL и authenticated `snapshot.pdf/png` остаются прежними. Только совпавшая проверенная привязка переключает чтение на adapter. Изменённый draft без новой привязки читает новые DB bytes, а не старый artifact. При сбое уже привязанного storage нет скрытого fallback на другую копию.
- Заголовки приватных downloads: no-store/private, no-referrer, noindex, nosniff; новые `f1_` capability скрываются в логах наравне с `r1_`.

## Флаги и откат

По умолчанию `DURABLE_REPORT_FILES=false`, `SHARED_REPORT_ARTIFACTS=false`; прежние пути работают. Первый флаг переключает создание file links, второй — чтение подтверждённых report references. При включении проверяются additive schema `bc8d9e0f1a2b` и корректность локальных TLS/credential настроек, без файловой записи.

Отключение создания не ломает уже выданные f1-ссылки: их read/list/revoke продолжают работать. Поэтому metadata/service/certificates сохранять до истечения/отзыва всех активных ссылок. `SHARED_REPORT_ARTIFACTS=false` возвращает прежнее чтение delivery из БД: исходные blobs намеренно сохранены. Это application rollback на совместимый release, не удаление таблиц/downgrade. Старые in-memory tokens всё ещё требуют отдельного drain/TTL/reissue плана перед вторым API.

## Операторская миграция

`python -m ops.migrate_report_artifacts` — агрегатная read-only инвентаризация, с 15 s statement timeout; не выводит пользователей, содержимое файлов или public tokens. `scope_candidates` — предварительная оценка, не гарантия доступа/валидности.

```sh
python -m ops.migrate_report_artifacts --apply --delivery-id VERIFIED_DELIVERY_UUID
```

Только явно перечисленные 1–20 UUID, без неявного массового прохода. Применять в release environment с отдельными DB/storage правами после backup/capacity inventory. Copy + checksum/size verification + revision recheck; исходные blobs, public tokens, даты, snapshot JSON и AI-текст не переписываются. Нет генерации PDF/AI, рассылок, списаний или удаления. Ошибка даёт nonzero exit и тип ошибки без SQL parameters/содержимого. Повтор безопасен. Старые aggregate snapshots без доказанного scope пропускаются с ошибкой, не угадываются.

## Приёмка и оставшееся

`tests/test_report_artifacts.py`: настоящий изолированный PostgreSQL, synthetic файлы, два независимых FastAPI test apps, без production secrets/external sends. Проверяются точные bytes старых URL, cache reset, rollout flags, owner revoke/current access, stale revision race, missing storage = 503, отсутствие SQL connection при IO, disconnect/cancel cleanup, backpressure и read-only inventory.

Source-bind полный regression до последнего management listing/scope-теста: **374 passed, 1 skipped, 1 deselected**, 47 warnings, 75,89 s. После последнего изменения targeted HTTP + ledger: **29 passed**, 17 warnings, 22,23 s (18 HTTP/migration/scope + 11 ledger). Проверка окончательного committed image фиксируется следующим evidence. Реальный межхостовой API-1/API-2 transport ещё не принят: локальный mTLS service проходил отдельные тесты 6B, production endpoints не запускались.

Финальная image-only приёмка `17fd0af`: **375 passed, 1 skipped, 1 deselected**, 47 warnings, 75,63 s. Image ID `sha256:24ce28ab7d5720e9904c924f263fb941a6b9707376767caaf313fd39015d67ac`, OCI revision `17fd0af`; image собран из `--revision`, source bind отсутствует. `pip check` успешен; .env/.git/uploads/landing/frontend в `/app` отсутствуют. Всё только на изолированном стенде сервера 2.

T02 не закрыт целиком: публичные avatars/brand/SEO uploads и rejected-leads, legacy temp tokens, physical tombstone retention/PITR, сертификаты/rotation/firewall активации и межхостовая приёмка остаются. Текущий bridge ещё читает DB blob для source hash; он не заявляется устранением blob overhead. Direct render → shared artifact и освобождение DB blobs относятся к дальнейшему T09 pipeline после проверяемого rollback.
