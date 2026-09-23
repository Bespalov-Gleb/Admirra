# Ассистент: короткие SQL-фазы и закрытие потоков

23.09.2026. Candidate `b8bda45`, **не production deployment**.
Production env, ingress, БД и scheduler этим пакетом не менялись.

## Найденная проблема

После `commit()` SQLAlchemy истекает ORM-объекты. Чтение `message.id`,
настроек integration, вложений или conversation после commit заново начинает
SQL-транзакцию. В интерактивном ассистенте она могла жить во время ответа LLM,
запроса рекламного API или ожидания SSE-клиента. Это занимает слот общего пула,
даже когда полезная SQL-работа уже закончилась.

Кроме того, закрытие внешнего async generator само по себе не гарантировало
немедленного закрытия вложенного provider generator на всех уровнях.

## Изменения

- `/api/assistant/chat` освобождает auth/conversation read до передачи
  StreamingResponse. Сначала в короткой SQL-фазе собираются история и тексты
  вложений, затем используются обычные значения, не lazy ORM-поля.
- `_persist` берёт UUID сообщения после flush **до commit** и возвращает UUID,
  а не истёкший ORM-объект. Вывод финального `message_id` больше не открывает SQL.
- ToolContext хранит только identities пользователя/диалога и scalar snapshot
  integration. Перед новым инструментом настройки и доступ перечитываются;
  активность пользователя, владение диалогом и доступ к выбранному проекту
  проверяются также между LLM-итерациями и перед сохранением результата.
- Yandex/VK/Avito и Wordstat выполняют HTTP без занятого request DB-соединения.
  OAuth refresh отделён от короткой записи результата: проверяются actor,
  project scope, наличие integration и неизменность credentials/account/settings.
  Поздний ответ не перезаписывает ручное переподключение, новое значение токена,
  перенос проекта или удалённую интеграцию. Ошибка сохранения не маскируется
  успешным обновлением in-memory токена.
- `aclosing` на уровнях agent → LLM → selected wire закрывает вложенные
  потоки на нормальном завершении, исключении и отмене. Гарантируется закрытие
  нашего транспорта, **не** отмена вычисления/стоимости у внешнего провайдера.
- Ошибка подготовки истории тоже завершает SQL-фазу. Read-release helper
  отказывается молча потерять pending writes. Общие ошибки инструментов не
  передают модели текст внутреннего SQL/credential exception.

Схема, цены, квоты и набор моделей не менялись. Новый feature flag не добавлен:
поведение применяется к ассистенту при выкладке этого кода. Существующий ledger
продолжает резервировать одну продуктовую единицу и не повторяет платный вызов
при replay. Неизвестный результат/отмена после обращения к провайдеру не
объявляется бесплатным успешным запросом.

## Проверки

`tests/test_assistant_db_lifecycle.py` использует настоящую isolated PostgreSQL,
ORM с обычным expire-on-commit, **pool_size=1 / max_overflow=0 / timeout=0,3 s**.
В каждой проверяемой точке IO соединений у запроса ноль, и отдельный читатель
может занять единственный слот и выполнить `SELECT 1`. Внешние провайдеры
заменены заглушками; реальные отправки/AI-затраты отсутствуют.

Покрыты:

- история, вложения, обычный ответ, tool-loop и последний ход без tools;
- SSE start/text/tool/done и отсутствие скрытого SELECT на выдаче message_id;
- Yandex/VK/Avito/Wordstat wrappers, успешный refresh, отмена refresh;
- настоящие Yandex Direct/Metrika/Reports client methods с fake HTTP
  `401 → refresh → 200`, без SQL во время каждого HTTP;
- поздний refresh после смены токена, кабинета, владельца, блокировки актёра
  или удаления integration: обновление отклонено;
- сохранение выбранного проекта и перечитывание нового кабинета между tools;
- полный chat route + реальный run ledger: replay без второго LLM-вызова,
  одна списанная единица; при отмене после первого токена — interrupted,
  без ложного возврата неизвестной provider cost;
- ошибки подготовки/провайдера и закрытие всех четырёх LLM wire-протоколов.

До упаковки: первый набор 66 passed; расширенный 117 passed; после защиты
подготовки 74 passed; отдельно Yandex wire 3 passed; финальные stream/lifecycle/
provider-limits — 31 passed. Это перекрывающиеся наборы, их нельзя складывать.
Результат проверки чистого образа фиксируется отдельно ниже.

### Сам чистый образ

`admirra-devops:b8bda45`:
`sha256:9a096e97ce4c81dbdcea15f669aa8a71be3d59413914c9639613cb7599cd88ad`.
Image-only (без source mount), non-root/read-only, изолированная сеть,
PostgreSQL/Redis только тестового compose project:
**134 passed, 117 warnings, 6 subtests passed, 113,15 s**, exit 0.
Включает новый lifecycle, runs/streaming/files/VK/provider limits, team access,
ads sync, API boot, packaging и provider transport. Это целевой набор,
не полный повтор общего manifest.

Restore этого image: backup `20260922T221413Z-b1eea7ec`, migration head
`f68b92a3b4c5`, **66 s**, network=none. Worker preflight, boot/ping четырёх
Celery-групп, API health/auth и **64/64 HTTP reads** прошли. Компактный контракт
проверен сравнением с полным. Batch: 64 проекта × 4 канала, 12 индивидуальных
сравнений совпали, access guards passed, 795,64 ms. Внешние провайдеры недоступны;
воркеры проверены на запуск, не на реальную business нагрузку. Это не LLM live
acceptance, не двухузловая проверка и не новый production capacity benchmark.

Evidence: `/opt/admirra-staging/b8bda45/assistant-tests.log` и `restore.log`,
mode 600. Build image из commit, tests без source bind; рабочие secrets и
незакоммиченные пользовательские изменения в него не включались.
Временный compose project `admirra-assistant-io-review` удалён после приёмки;
restore containers/volumes и runtime tmpfs также очищены. Рабочие сервисы
и сохранённые images/evidence не удалялись.

## Ограничения и следующий шаг

Это исправление интерактивного `/assistant/chat`, не автоматическое закрытие
всех `SQL-over-IO` в проекте. Отдельно остаются live attribution/campaigns/
dynamics в `backend_api/stats.py`, другие legacy AI/report/billing paths,
общая двухузловая cache/files/SSE/drain/recovery и bounded provider acceptance.

Защита записи refresh — проверка неизменности состояния под коротким row lock,
не единый глобальный lease на OAuth grant для **всех** старых sync/interactive
consumers. Параллельные внешние refresh одной rotating grant могут потребовать
восстановления подключения; exactly-once refresh этим пакетом не обещается.
Повторная проверка доступа выполняется между этапами, а не прерывает мгновенно
уже отправленный провайдеру HTTP при отзыве прав в середине запроса.

Чистый backend artifact упакован из Git allowlist (599 файлов), без пользовательских
незакоммиченных frontend/landing, `.env` и uploads. Миграций в пакете нет;
общий candidate по-прежнему требует `f68b92a3b4c5`. Полный прошлый результат
1481 tests относится к `5e788f9`, не автоматически к этому новому image.
