# VK hierarchy: detached fetch и атомарное сохранение

23.09.2026. Локальный candidate, **не production deployment**.

## Что изменено

- `backend_api/hierarchy_read.py`: shared подготовка и apply для Direct/VK.
  Контракт доступа/настроек и fingerprint VKStats/VKGroups/VKBanners читаются
  в коротком SQL snapshot; соединение освобождается до первого provider await.
- `backend_api/vk_hierarchy_read.py`: определение контекста токена, каталоги
  групп/баннеров и дневная статистика собираются в plain values до записи.
  Unknown token kind — отказ, а не догадка о личном кабинете. Agency/manager
  требует account_id; client_id идёт только в каталоги, не в Statistics.
- `automation/vk_hierarchy_contract.py`: отдельный strict transport вместо
  старых методов, которые перехватывали ошибки и возвращали частичные списки.
  Explicit items/rows, проверка родителя, дат, метрик, повторов, pagination,
  count (если присутствует), лимиты страниц/размера. Неуспех любой страницы
  или chunk завершает весь сбор; 429/5xx не превращаются в успешные нули.
- Один короткий apply после успешного сбора: Client → Integration → Campaign
  locks, перечитывание actor access/config и fingerprint. Поздний результат
  после sync/смены настроек отклоняется (409), потеря доступа — 403.
  Перезапись свежих метрик и частичное сохранение групп при сбое баннеров
  запрещены. Каталожная строка не затирает существующие метрики.
- SQL всегда ограничен client_id + campaign_id + периодом. Natural key не
  включает изменяемые названия; уже существующие duplicate keys не склеиваются
  догадкой. Незавершённые ORM-правки вызывающего кода не отбрасываются.
- HTTP children route передаёт actor ID, иначе response schema и lead/CPL
  семантика не менялись. Direct использует те же shared guards и отдельно
  проходит регрессию. Старые VK API-методы остальных consumers не изменены.

## Приёмка

`tests/test_vk_hierarchy_read.py`: настоящий isolated PostgreSQL, pool_size=1,
max_overflow=0; на каждом provider этапе второй читатель получает единственный
слот и выполняет SELECT 1. Synthetic VK + httpx.MockTransport, без живых
кабинетов, платежей, LLM и сообщений клиентам.

Проверяются личный/агентский/manager контексты, unknown, все стадии ошибок,
смена настроек/владельца/активности пользователя, удаление/переименование,
параллельный sync и два одновременно собранных результата, cancellation,
legacy foreign-client rows, duplicate keys, pending edits, настоящий route
для групп/баннеров (34 conversions / 3400 cost), чанки дат/ID, pagination,
неполные/повторные/чужие/невалидные ответы API.

Предварительный прогон: 56 passed, 1 failed (проверка числа date chunks в
тесте: выбранный диапазон поместился в один интервал существующего helper-а).
Тестовый диапазон увеличен на день, чтобы фактически пересечь границу.
После этого добавлены foreign-client и malformed normalized payload cases.
Окончательные image regression/restore результаты фиксируются ниже после
завершения, не считаются выполненными заранее.

## Границы

- Сохранена текущая lazy-cache политика: наличие хотя бы одной строки
  groups/banners в slice позволяет пропустить повторную загрузку этого уровня.
  Это **не** гарантия полного исторического покрытия или актуальности.
  Coverage/watermark и исправление уже сохранённых legacy partial/zero rows —
  отдельная задача; этот пакет не переписывает исторические данные в проде.
- Catalog/statistics не являются единым атомарным snapshot на стороне VK.
  Проверки обнаруживают некорректные/явно неполные ответы, но не доказывают
  отсутствие незаявленного пропуска самим провайдером. Существующие записи,
  отсутствующие в отчёте, не удаляются.
- Primary filters `_ad_plan_id__in`/`_ad_group_id__in` взяты из уже используемого
  рабочего контракта VK-клиента. Silent fallback к списку всего кабинета здесь
  намеренно отсутствует. Официальные страницы AdGroup/Banner/Statistics
  недоступны для browser fetch при проверке; новая live-provider совместимость
  не заявляется. Перед широким включением нужен read-only provider smoke.
- Locks согласованы с durable ads sync; legacy writers без такого протокола
  не получили глобальную сериализацию. Schema/env/credentials не изменяются,
  OAuth refresh этим интерактивным путем не выполняется.
- Не закрыты Avito hierarchy attribution, audience/top-ads и остальные
  legacy SQL-over-IO, multi-host/cache/SSE/queue recovery и SLO/load gates.
  Не выполнено production cutover. S3 и две ночи наблюдения отложены владельцем.
