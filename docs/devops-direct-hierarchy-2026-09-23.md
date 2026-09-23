# Direct hierarchy: detached fetch и короткое сохранение

23.09.2026. Candidate, **не production deployment**. Этот пакет закрывает
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

Результаты чистого image и restore фиксируются после финальной сборки.

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
