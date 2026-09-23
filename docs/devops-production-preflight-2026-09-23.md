# Production preflight: факты перед переключением

23.09.2026, начало проверки 20:26 UTC. Владелец попросил переходить к production.
**Статус: cutover ещё не выполнен. Admission остаётся open, рабочие API/
automation/frontend не пересоздавались, production migrations не применялись.**
Этот документ заменяет впечатление «остался только docker up» конкретными
обязательными работами. Оставшиеся улучшения UI/SQL сами по себе релиз не блокируют.

## Зафиксированный production baseline

| Сервис | Реальный image digest |
| --- | --- |
| Backend | `sha256:d497fa5d99258cf7cb36858984bdd1f18d0371a2e368807972cecfedfb613a93` |
| Automation | `sha256:e6f8ebec4a2de0e780bb7d867a783448377409a44f0758af59a17f15bccdf1bc` |
| Frontend | `sha256:09aaa07dec7a855b98bdc52007b3e1838b925ba2c3167192242f81395663e929` |
| Admin frontend | `sha256:3023714f37d9bc7f675db78085068a4a200a78690f588751cd768555196aaa5e` |

Backend/automation config — `/etc/admirra/releases/signup-enabled-20260922T123659Z/`;
frontend — `/etc/admirra/releases/signup-ui-20260922T130959Z/`.
Git checkout сервера 1 — `cdf0a4d3c9dee66722219d7e7e2924d5475c0044`, clean tracked tree,
но runtime собран overlay-релизами и **не равен этому checkout**.
Нельзя делать blanket pull/build/up. Schema — `cc3d4e5f6a7b` плюс уже применённые
additive поля; общий candidate migration head — `f68b92a3b4c5`.

Старый `ops/rollback_images.json` от 20 сентября не учитывал signup-discount.
Manifest и пример preflight обновлены по фактическому Docker inspect;
все четыре образа сохранены дополнительными тегами `pre-cutover-20260923`.
Сохранение образа **не означает**, что старый consumer умеет новые durable jobs:
откат после новых claims требует отдельной reconciliation/совместимого runtime.

## Read-only эксплуатационная проверка

- Сайт HTTP 200; API-2 private readiness — ready/database ok.
- Текущие backend/automation/frontend: restart counters 0.
- Оба настоящих monitor timers (`@ingress`, `@api2`) active/success;
  первые запросы по неверным сокращённым именам дали inactive, это не отказ мониторинга.
- Prometheus active alerts — пусто. Внешний heartbeat timer active, последний run success.
- На момент SQL-read: queued/running sync 0, sending reports 0,
  AI messages за последние 10 минут 0. Это snapshot, не drain: перед cutover
  после закрытия admission перечитать, не переносить эти числа как актуальные.
- Server 1 ~18 GiB свободно, server 2 ~18 GiB свободно до нового image transfer.

## Подготовлено этим этапом

1. Создан новый encrypted backup `20260923T202713Z-ebc64797`, schema
   `cc3d4e5f6a7b`; sender systemd job success. Restore нового backup записывается
   ниже после завершения (успех создания не подменяет восстановление).
2. Полный isolated backend manifest запущен на immutable `a5635d5`, без bind
   исходников и без внешней сети. Результат записывается после завершения.
3. Исправлен stale `EXPECTED_SCHEMA_REVISION` в `ops/compose.workers.yml`:
   вместо старого `de0f1a2b3c4d` теперь обязательный release input
   `ADMIRRA_SCHEMA_REVISION`. Без выбранного проверенного head Compose не разрешает запуск.
4. Targeted проверки новых ops изменений: **55 passed**, 0,18 s. Первоначальный
   тест использовал отсутствующий PyYAML; заменён на source contract assertion
   без добавления runtime-зависимости. Реальный Docker Compose capacity parser
   также пройден: cap 6144 MiB с API-2, OS headroom 1796 MiB, worker SQL max 14
   при role limit 20. `load_accepted=false`: арифметика не заменяет mixed-load.
5. Повторные тестовые пары Alertmanager и внешнего heartbeat отправлены для
   свежей проверки доставки: Alertmanager notifications 14 → 16, все failure
   counters Telegram 0; внешний heartbeat вернул sent для critical и ok.
   Human receipt не считается подтверждённым по HTTP.
6. Immutable `admirra-devops:a5635d5` доставлен на server 1; digest на обоих
   узлах `sha256:5642c39fa1134a840e4b3f3657ffb2c77de232c8ed6e631c21a353189cc2075c`.
   Образ не запущен с production credentials/traffic. Старые runtime не тронуты.

## Что реально мешает полному переключению

1. **Runtime deployment не завершён:** на server 2 нет `/etc/admirra/worker.env`
   и `/srv/admirra/worker-data`; production consumers/scheduler ещё legacy.
   Нужны versioned, проверенные env/mounts/permissions/roles, явная карта
   остановки старого scheduler и запуска единственного нового. Не генерировать
   значения секретов, не включать календарь «для проверки» на живой БД.
2. **Общие файлы не развёрнуты:** приватный artifact service пока только в коде.
   На server 1 нет `/etc/admirra/artifact-server` и `/srv/admirra/artifacts`,
   runtime контейнера нет. Подготовить private CA/principals/storage, проверить
   cross-host upload/read и сохранение текущих ссылок/files. Это не покупка S3;
   S3 отложен. Без этого нельзя расширять API-2 на весь трафик или переносить
   файловые consumers и утверждать, что файлы доступны с обоих узлов.
3. **Интеграционная приёмка:** финальный mixed-load/recovery с реальными
   service roles, двумя узлами, cache revisions/SSE/files/drain и безопасными
   provider/report/AI/billing сценариями. Проверенные unit/PG/image restore
   не являются этим тестом. Нужен совместимый rollback после новых durable jobs.
4. **Подтверждения владельца:** получение обеих тестовых пар в AdMirra Alerts,
   ответственный за реакцию, отдельная копия recovery key вне обоих серверов.
   Запрошено в текущем диалоге; без ответа не ставить true в evidence.

После закрытия этих пунктов: свежий bounded preflight → admission/drain →
миграции → single-API + минимальные workers → проверенный тестовый job →
открытие admission → API-2 canary по ступеням. Не заменять эту процедуру
перезапуском всего Compose. S3 и две ночи наблюдения остаются отложенными.
