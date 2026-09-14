# DB-03 / T05 — устранение N+1 списка интеграций

Дата: 13.09.2026. Статус: подготовлено локально, не production rollout. Не закрывает T03/T05 целиком.

## Причина и изменение

`backend_api/integrations.py:get_integrations` выполнял JOIN с `Client` для фильтра, но не заполнял ORM-связь `Integration.client`. При сериализации `IntegrationResponse` свойства `client_name`/`client_display_id` и список `campaigns` вызывали дополнительные lazy SELECT для каждой интеграции. Реальный код сериализатора используется и в регрессионном тесте, а не подменяется упрощённым DTO.

Теперь `contains_eager(Integration.client)` использует уже существующий JOIN, а `selectinload(Integration.campaigns)` читает кампании пакетно. Стратегии соответствуют закреплённому SQLAlchemy 2.0.52: [загрузка связей](https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html). Два запроса — бюджет проверенных размеров, не обещание для произвольного количества: select-in разбивает большие наборы идентификаторов на пакеты (до 500).

Сохраняются прежняя авторизация, фильтры проекта/папки, состав полей JSON, список кампаний и исключение access_token из ответа. SQL-агрегаты, атрибуция, CPL, тарифы, cache, schema и frontend не менялись. Нет миграции или нового индекса. Порядок без ORDER BY раньше не гарантировался и сейчас не является контрактом.

## Измеренный бюджет запросов

Изолированный PostgreSQL, отдельная схема каждого теста, два синтетических владельца; у каждой интеграции отдельный проект и две кампании. Счётчик SQLAlchemy считает все SELECT, включая сериализацию.

| Доступных интеграций | Старый data path | Новый data path |
| --- | ---: | ---: |
| 1 | 3 | 2 |
| 13 | 27 | 2 |
| 20 | 41 | 2 |

Это **без авторизации**, одинаковой в обоих вариантах. Дополнительный тест с настоящим resolver владельца: 20 интеграций, **6 SELECT целиком** (4 прежних запроса доступа + 2 чтения данных). После возврата handler сериализация не выполняет SQL, JSON полностью доступен и после закрытия Session. Ответы до/после совпадают после нормализации порядка по ID.

Дополнительно проверены: чужой владелец/кампании недоступны; client_id не расширяет доступ; результат folder resolver пересекается с ACL; отсутствие прав не читает интеграции; секрет не попадает в ответ.

Targeted suite `tests/test_integration_list_queries.py`: **8 passed**, 16 warnings, 9,60 s. Полный source-bind regression: **484 passed, 1 skipped, 1 deselected**, 47 warnings, 104,13 s.

Чистый образ коммита **`d965d77`**, image-only: **484 passed, 1 skipped, 1 deselected**, 47 warnings, 108,10 s. Docker image ID: `sha256:3cb807f8bb0fe95c709e3d44abe8e2cdd5c0cdfd8f7fc6e2f85fd8ceabf80554`; release label `d965d77`. Source volumes отключены через `ops/compose.artifact-tests.yml`. `pip check` успешен; `.env`, `.git`, uploads, landing и frontend отсутствуют в образе. Логи на тестовом узле: `/opt/admirra-staging/d965d77-build.log`, `/opt/admirra-staging/d965d77-image-tests.log`.

Рабочее приложение повторно проверено отдельно 13.09.2026: commit `cdf0a4d`, публичная главная HTTPS 200 в 16:19 UTC. Push, application deploy, production migrations и перезапуск production PostgreSQL не выполнялись. Изолированный стенд использовал синтетические данные и internal Docker network без host ports/исходящего трафика.

## Границы результата и следующий шаг

Похожие client/campaign queries обнаружены в [спокойном production sample](devops-db03-sampling-2026-09-13.md). Это основание исследовать путь, но не доказательство происхождения всех запросов sample: для этого нужен HTTP trace. Снижение query count воспроизведено тестом; latency/RPS/CPU под реальной нагрузкой пока не измерены.

Endpoint по-прежнему возвращает все доступные интеграции и их кампании. Pagination, lazy details и batch API карточек остаются частью T05; эта небольшая оптимизация не заменяет их. Откат — предыдущий совместимый backend artifact; DB rollback не нужен. Применять вместе с согласованным release plan, не поверх неизвестной версии production.
