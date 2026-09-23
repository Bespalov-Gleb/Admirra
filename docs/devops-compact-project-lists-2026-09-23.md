# Компактные списки и два HTTP API: приёмка candidate

23.09.2026. **Не production deployment.** Изменения API, ingress, env,
схемы и scheduler в production этим пакетом не выполнялись.

## Контракт и совместимость

`d254266` добавляет opt-in `include_campaigns=false` к `/api/clients/`,
`/api/clients/stats` и `/api/folders/tree`. По умолчанию возвращается прежний
полный ответ. Компактный вариант не читает ORM relationship кампаний и
**не включает ключ `campaigns`**, а не подменяет реальные кампании пустым списком.
Все остальные поля проектов, интеграций, статистики и папок сохраняются.
Секреты не добавляются в ответ; правила доступа остаются прежними.

Для 20 проектов с одной интеграцией: загрузка отношений и сериализация —
2 SELECT вместо 3 у полного пакетного ответа (41 у старого lazy-пути).
Это не число всех запросов endpoint: access checks и агрегаты считаются отдельно.

Проверены consumers общего `useProjects`, Header, `useDashboardStats` и старого
`views/Project/Projects.vue`: им нужны project/integration metadata, а не
вложенные кампании. Эти четыре места теперь запрашивают компактный ответ.
Кампании для выбора/таблицы загружаются отдельными `/campaigns/` и
`/dashboard/campaigns`; детали интеграций также имеют отдельные запросы.
Неаудированные legacy consumers оставлены на полном ответе.

Старый frontend продолжит получать полный контракт. Новый frontend совместим
со старым backend, который проигнорирует неизвестный query parameter, но
экономия payload появится только после обновления backend. Миграций в этом
пакете нет; candidate в целом по-прежнему требует schema `f68b92a3b4c5`.

## Автоматические проверки до упаковки

- PostgreSQL/API: 79 passed, 1 skipped, 17 warnings, 34,29 s. Проверяются
  неизменность default/full ответа, полное совпадение compact с full за вычетом
  кампаний, отсутствие lazy SQL/ORM mutations, access guards и недопустимый flag.
- Безопасность restore benchmark: 12 passed, 16 warnings, 0,85 s. Сравнение
  нормализованного JSON обнаруживает изменение лидов, но игнорирует только
  вложенные кампании. Тела ответов/контакты/токены не печатаются.
- Frontend: 14 целевых unit tests и полный tracked Node-набор 49 tests passed;
  production build прошёл (949 modules,
  2,97 s). Это сборка рабочей копии, включая существующие пользовательские
  изменения вне пакета, не чистый frontend deploy artifact. Вёрстка этим
  пакетом не менялась; browser/visual acceptance не заявляется.

Дополнительно чистые frontend sources из `git archive 5e788f9` собраны отдельно:
949 modules, 2,72 s. Использованы уже установленные локальные `node_modules`
через symlink; это проверка чистых исходников, не повторный `npm ci`/CI image.
Все 49 Node tests повторно прошли и в этой чистой копии исходников.

## Два API-процесса

`5e788f9` добавляет отдельный `tests/test_two_api_read_workload.py`.
Два настоящих uvicorn-процесса используют одну изолированную PostgreSQL,
настоящие JWT и по 2 SQL-соединения без overflow. Четыре читателя выполняют
120 запросов summary/batch-карточек; параллельно работают 12 real sync apply
и 12 report receipt workflows с повторным обращением к каждому отчёту.

До упаковки: 1 passed, 57 warnings, 13,16 s; load-фаза 4,709 s,
p95 269,64 ms, max 558,06 ms, 120 успешных чтений и 4 ожидаемых отказа доступа.
28 чтений пересеклись с report IO, 91 — с sync IO. Cost/leads согласованы,
прошлый период неизменен, повторная генерация отчёта не произошла.
После запросов у обоих API нет idle-in-transaction соединений.

Это процессы **в одном контейнере**, не два production-хоста. Внешние
VK/LLM/render заменены контролируемыми заглушками; сеть изолирована.
Sync/report выполняются через реальные функции/ledger, но не через Celery
consumer. Проверка не охватывает ingress, cache invalidation, SSE, uploads,
общую файловую систему, реального провайдера или финансовые side effects.
Пики SQL pools измеряются только у родительского test driver, не у child API;
для API подтверждается конфигурация pool и отсутствие зависшей транзакции,
а не измеренный peak. Это не production capacity/SLO.

Запуск: `ops/compose.isolated.yml` + `ops/compose.artifact-tests.yml` +
`ops/compose.mixed-http.yml`; последний даёт 2 GiB на pytest + два API.
Обычный manifest остаётся отдельным 1 GiB тестом.

## Финальный артефакт

Чистый backend artifact из Git `5e788f9`, 597 разрешённых файлов,
без dirty frontend/landing, `.env`, uploads и Git:
`sha256:d1332c01595e6f9e85de6618475154e5dcf5902dec5650fa91655c23749a849c`.
Тесты image запускаются без source mounts, non-root/read-only.

Полный backend manifest **этого image**: **1481 passed, 1 skipped,
1 deselected, 259 warnings, 6 subtests passed, 823,13 s**. Exit 0,
OOM=false. `python -m pip check`: No broken requirements found.
Это не внешняя provider/sandbox приёмка и не security vulnerability scan.

Отдельный двухпроцессный тест **этого image**: 1 passed, 57 warnings,
15,30 s. Load-фаза 5,173 s, p95 301,96 ms, max 681,72 ms;
120 чтений, 4 ожидаемых 403, 12 sync/12 report receipts. Пересечение чтений
с report/sync IO: 23/95. Шёл параллельно regression на общей тестовой БД;
эти latency нельзя сравнивать с предыдущим отдельным прогоном как ускорение.

## Restore и последовательное сравнение

Оба прогона: backup `20260922T221413Z-b1eea7ec`, image `5e788f9`,
миграции до `f68b92a3b4c5`, network=none. Полная регрессия уже завершилась,
другой нагрузочный тест параллельно не запускался. PostgreSQL 2 CPU/2 GiB,
API 1 CPU/1 GiB, pool 5/0. Сначала полный ответ, затем новый restore и compact.
72 проекта, 72 интеграции; в полном ответе 2250 вложенных кампаний.

| JSON response | Полный, bytes | Компактный, bytes |
|---|---:|---:|
| clients | 1 007 596 | 107 784 |
| clients/stats | 1 046 153 | 146 341 |
| folders/tree | 1 050 356 | 150 544 |

Список уменьшился на **89,3%** (примерно в 9,35 раза). Это размер
несжатого JSON, не обещание такого же ускорения страницы. Оставшиеся поля
всех трёх ответов полностью совпали с full-вариантом (`full_contract_equivalent`).
Кампании не удалены из БД: их просто нет в compact payload. Нули в диагностике
`campaigns` означают отсутствие вложенных объектов, не отсутствие рекламы.
Хеши остальных пяти маршрутов между restore-прогонами совпали.

| Маршрут, p95 ms | Полный | Компактные lists |
|---|---:|---:|
| auth | 548,58 | 200,73 |
| clients | 1062,93 | 638,03 |
| folders | 717,28 | 458,34 |
| notifications | 500,02 | 806,09 |
| clients/stats | 2134,29 | 1869,44 |
| folders/tree | 2449,37 | 2035,40 |
| summary | 454,71 | 666,78 |
| top-projects | 2294,65 | 1803,06 |

На вариант: **64/64 HTTP 200**, concurrency 4, только 8 измерений каждого
маршрута. Общее время read-фазы 17,482 → 12,314 s; aggregate p95
2297,29 → 1803,06 ms. Есть ухудшения notifications/summary в этой короткой
выборке. Это не статистически устойчивый SLO/capacity и не browser benchmark;
компактный прогон также делает три дополнительных full-запроса до timed-фазы
ради проверки контракта, а последовательность может влиять на файловый кеш.

Каждый restore прошёл worker preflight, boot/ping четырёх Celery-групп,
API health/auth и batch-сверку **64 проекта × 4 канала**, 12 индивидуальных
сравнений, access guards passed. Batch: 769,62 / 783,48 ms.
Restore durations: **69 / 65 s** (до cleanup). Воркеры проверены на запуск,
не на реальную business нагрузку; provider/SMTP/платежи из сети недоступны.
Успешная миграция вперёд не разрешает откат к старой несовместимой схеме.

Логи без тел ответов/контактов: `/opt/admirra-staging/5e788f9/`
`regression.log`, `two-api.log`, `restore-full.log`, `restore-compact.log`,
mode 600. Runtime secrets при restore находятся в закрытом временном tmpfs
и удаляются cleanup; в Git и build artifact их нет.
После приёмки удалён только isolated compose project `admirra-compact-review`.
Проверки inventories: его контейнеров/сети, restore containers/volumes и
`/dev/shm/admirra-runtime-restore.*` не осталось. Образы и evidence сохранены.

## Граница готовности

Следом остаются реальные двухузловые cache/files/SSE/drain и combined recovery,
оставшийся live/interactive SQL-over-IO, ограниченная provider/sandbox и
операторская приёмка, затем свежий backup/preflight и контролируемый cutover.
S3 и две ночи наблюдения отложены владельцем, не объявлены выполненными.
