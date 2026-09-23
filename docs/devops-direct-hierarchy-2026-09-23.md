# Direct hierarchy: detached fetch и короткое сохранение

23.09.2026. Candidate `9e54bb8`, **не production deployment**. Этот пакет закрывает
проверенные Yandex Direct paths раскрытия кампаний, не все рекламные платформы.

## Изменения

- `backend_api/hierarchy_read.py`: подготовка scalar attribution contract и
  fingerprint существующих строк YandexStats/Groups/Ads за запрошенный scope
  в коротком SQL snapshot, затем rollback до обращения к API.
- Все campaign/group/ad reports и каталоги собираются в памяти **до записей**.
  Во время ожидания отчёта, catalogue pagination и Метрики request Session
  не удерживает SQL connection. Direct drill attribution получает plain values,
  а не истёкшие ORM-объекты после commit.
- Apply берёт Client → Integration → Campaign locks; первые два совпадают с
  порядком durable ads sync. Настройки, actor/project access и fingerprint
  перечитываются до записи. Отозванный доступ — 403, изменившиеся настройки
  или данные — 409. Запоздавшая загрузка не затирает intervening sync.
- Natural keys — date/campaign/entity ID, **без изменяемых названий**.
  Существующие строки читаются пакетно, не SELECT на каждую запись.
  Каталожная нулевая строка может только создать отсутствующую сущность,
  но никогда не обнулить существующую статистику.
- Повторные запросы сериализуются на коротком apply; второй результат со
  старым fingerprint отклоняется. Если в старой БД уже есть неоднозначные
  duplicate natural keys, apply ничего не меняет и возвращает конфликт,
  а не произвольно выбирает строку или удаляет данные.
- Строгий Direct TSV parser расширен на ad level. Каталоги AdGroups/Ads
  получают только необходимые поля, проходят pagination, проверку campaign ID,
  дублей, advancing offset и ограничений размера. Ошибка/неполный ответ не
  превращается в успешный пустой каталог. Сохранён v501 → v5 fallback при
  API-level несовместимости/пустом v501; transport errors fail closed.
- Ошибка сбора возвращает безопасный 502 без частичных записей. В лог попадает
  только campaign UUID и класс ошибки, не provider body/token. Cancellation
  проходит наружу без записи; pending ORM writes не отбрасываются helper-ом.

Схема, миграции, креды/env, ingress и worker routing не менялись.
Контракт каталогов (CampaignIds/FieldNames/Page/LimitedBy) сверен с официальными
страницами [AdGroups.get](https://yandex.ru/dev/direct/doc/ru/adgroups/get) и
[Ads.get](https://yandex.ru/dev/direct/doc/ru/ads/get); это не заменяет live smoke.

## Проверки

`tests/test_hierarchy_read.py`: настоящая isolated PostgreSQL, pool_size=1 /
max_overflow=0. На каждом provider этапе другой читатель может выполнить
SELECT 1 через единственный слот. Provider metrics — синтетические; каталог
также проверяется через httpx.MockTransport (pagination/HTTP/malformed/scope).

Покрываются: metrics + zero catalogs, повторный запрос без дубликатов,
отказы на промежуточных этапах, изменение sync/settings/owner/campaign,
два одновременно собранных результата, cancellation, pending writes,
старые duplicate natural keys, настоящий children route для групп/объявлений
с точной Метрикой (34 лида, расход 3400), строгий ad TSV.

Чистый image `admirra-devops:9e54bb8`:
`sha256:6a8149888956ed9889666e4bb458e09a67520c1b843e454cf97f0cf9475a704e`.
Собран из 603 allowlisted Git-файлов, без secrets, uploads и dirty frontend.
Предварительная source-overlay регрессия: 224 passed, 1 skipped, 163 warnings,
144,60 s. После неё дополнительно усилен client_id scope SQL-чтения/записи
и добавлена проверка неконсистентной legacy-строки другого клиента; окончательные
результаты artifact-only прогона/restore фиксируются отдельно ниже.

Artifact-only `9e54bb8`, без host source bind: **225 passed, 1 skipped,
164 warnings**, 145,89 s, exit 0. Новый файл hierarchy — 21 test cases.
Проверены hierarchy + attribution, ads sync contract/work, Direct API,
provider transport, summary/Avito, assistant VK reporting и API-role boot.
Skip — опциональное сравнение с previous-release implementation; весь isolated
manifest не повторялся. Внешние кабинеты/платные API не вызывались.

Restore этого же image: backup `20260922T221413Z-b1eea7ec`, migration head
`f68b92a3b4c5`, **66 s**, network=none. Worker preflight/boot, application
smoke и **64/64 HTTP 200** прошли. Compact/full metadata contract совпадает;
summary batch — 64 проекта × 4 канала, 12 индивидуальных сравнений,
access guards passed (758,22 ms). Это не реальная нагрузка очередей: workers
проходят startup/ping, реальные отправки отключены. Read smoke: 12,782 s,
aggregate p95 1847,5 ms, concurrency 4, по 8 запросов на маршрут — не SLO.

Root-only логи сервера 2:
`/opt/admirra-staging/9e54bb8/hierarchy-tests.log`,
`/opt/admirra-staging/9e54bb8/restore.log`.
Isolated compose-проект `admirra-hierarchy-io-review`, restore containers/
volumes и runtime tmpfs удалены; image и логи сохранены. Production не менялся.

## Границы и следующий участок

- VK lazy hierarchy пока сохраняет старую реализацию SQL-over-IO.
  Avito hierarchy attribution, audience/top-ads и прочие legacy paths тоже
  не объявлены завершёнными этим пакетом.
- Это incremental hydration, **не полная замена витрины**: отсутствующие в
  отчёте старые строки не удаляются. Существующее правило пропуска повторной
  загрузки ad slice при наличии строк сохранено; оно не доказывает полноту
  исторического покрытия. Нужны отдельные coverage/watermark правила.
- Блокировки координируют этот apply с durable sync, использующим тот же
  lock protocol. Legacy writers без такого протокола не получили глобальной
  гарантии сериализации. HTTP чтение Метрики и локальный SQL не превращены
  в одну распределённую транзакцию.
- Нет live-provider проверки на клиентском кабинете, общего performance/SLO
  заключения и production cutover. Далее: VK/оставшиеся IO paths, multi-host
  mixed-load/recovery, финальные preflight/backup и переключение.
- S3 и две ночи наблюдения остаются отложенными владельцем.
