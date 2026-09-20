# Production rollback artifacts

> После отдельного AI hotfix рабочие backend/frontend изменились. Для будущего cutover актуальны `admirra-rollback/backend:quota-0e5f031` (`sha256:6321c5fb910e9f8e4ff942deffd6bbe63d6285efd05b35b670a192ce780d365d`) и `admirra-rollback/frontend:quota-0e5f031` (`sha256:680b8893a1dcfa00460d0c2f591b5e7cb415d047cd9780d566535e6419a04af1`). `ops/rollback_images.json` обновлён. Таблица ниже сохраняет **до-hotfix** baseline для отката самого hotfix; automation/admin не менялись. Все старые теги сохранены. См. [release](assistant-quota-release-2026-09-20.md).

Дата фиксации: 20.09.2026. Статус: точные images backend, automation и внутренней админки закреплены отдельными Docker-тегами на server 1; запущенные контейнеры не перезапускались. На ревью добавлен ранее пропущенный **пользовательский frontend**; результат закрепления указан в review evidence.

## Зафиксированные артефакты

| Контур | Image ID | Защитный тег |
|---|---|---|
| backend | `sha256:047c8019bbbeec83c0c8cd11b39c03b31af2931d8e2f0b415196199f8768afe0` | `admirra-rollback/backend:pre-cutover-20260920` |
| automation | `sha256:33b4ca03408c55cd11093fa3c4f9b86ecf1f323f50636222a43ea71bb4217ab8` | `admirra-rollback/automation:pre-cutover-20260920` |
| customer frontend | `sha256:1b36b676b9cadca75befb5d03c66ac4c1177b0a7099e652af46360163eba4767` | `admirra-rollback/frontend:pre-cutover-20260920` |
| admin frontend | `sha256:3023714f37d9bc7f675db78085068a4a200a78690f588751cd768555196aaa5e` | `admirra-rollback/admin-frontend:pre-cutover-20260920` |

ID получены непосредственно из `.Image` работающих контейнеров и после тегирования повторно сверены через `docker image inspect`. Теги добавляют ссылки на уже существующие layers, не создают копий, не меняют контейнеры и защищают images от обычного prune как dangling.

Машиночитаемый manifest находится в `ops/rollback_images.json`. `cutover_preflight.py` требует передать exact backend image через `--expected-rollback-image` и сверяет evidence с ним. Один лишь синтаксически корректный digest больше не принимается.

## Ограничения

- это быстрый rollback на том же server 1, не offsite registry;
- откат приложения не выполняет downgrade additive schema: старый image должен оставаться совместимым с уже применёнными additive migrations;
- scheduler/worker ownership и admission gate восстанавливаются по cutover runbook, а не простым одновременным restart всех контейнеров;
- удалять защитные теги и выполнять aggressive image prune до завершения окна и периода наблюдения запрещено.

Перед окном повторно проверить, что каждый тег разрешается в записанный Image ID. После успешного периода наблюдения артефакты можно удалить только отдельным решением владельца.
