# Финальная приёмка двух узлов — 24.09.2026

Статус: новые проверки выполнены, **production cutover ещё не выполнен**.
Production schema `cc3d4e5f6a7b`, legacy automation и admission open сохранены.
Не считать синтетический межсерверный тест live-provider peak acceptance.

## Сборка и восстановление

- Чистый backend из commit `eb9550c`, image
  `sha256:b959c09111a5278493e072452cec334bce7be4dda6e250a72c29be716eda1482`.
  Доставлен на оба узла. Локальные незавершённые frontend/landing изменения
  владельца не попали в artifact. Frontend на проде остаётся AI/legal hotfix.
- Полный immutable-image manifest: **1612 passed, 1 failed, 1 skipped,
  1 deselected, 6 subtests passed**, 890.27 s. Единственное падение — устаревший
  точный digest в `test_example_uses_the_preserved_backend_rollback_image`.
  Manifest уже содержал правильный deployed backend `875ab667…`; исправлен
  ожидаемый digest теста. После исправления все **25 cutover tests passed**
  отдельным запуском; не выдаём его за полный повтор manifest.
- Свежий encrypted backup `20260923T230014Z-6da70651`, sender success в 23:00:23 UTC.
  Restore с миграциями до `f68b92a3b4c5`, preflight, четыре worker-группы,
  API startup и **64/64 HTTP 200** прошли; 71 s, `network=none`.
  72 проекта разрешённого аккаунта в compact list, прежние поля совпали.
  Read-smoke p95 1872.25 ms, max 2183.82 ms при параллельной регрессии.
  Summary batch: 64 проекта × 4 канала, 876.2 ms, 12 сравнений совпали.
  Это не браузерная скорость полной страницы и не production SLO.

## Два физических узла

`ops/multihost_rehearsal.py` запускает отдельный PostgreSQL на server 1,
API на обоих серверах, Redis и test driver на server 2. Private WireGuard,
отдельные bridge-сети, тестовые порты только на private IP. Узкие DOCKER-USER
правила разрешают только peer test ports, запрещают другой egress. Только
синтетические credentials/data. Нет production .env или provider secrets.

Application code — один immutable image, test driver/helper отдельно монтируются
read-only. Бизнес-процессы sync/report используют controlled stubs внешних API;
PostgreSQL, HTTP, JWT, транзакции, durable ledger и межсерверный transport реальные.

- Первый прогон: 600 запросов, 4 параллельных читателя, 12 sync apply,
  12 report receipts, 4 ожидаемых cross-tenant отказа; 22.012 s,
  p95 237.4 ms, max 676.88 ms. Расход/лиды атомарно соответствуют одному snapshot.
- Второй прогон: тот же mixed workload, p95 217.72 ms, max 697.6 ms,
  19.939 s. Затем real prefork Celery child crash/duplicate delivery/recovery,
  cache isolation/outage/cancel, SSE cancellation и billing replay/unknown-state
  guards на той же межсерверной тестовой DB. **44 passed**, 66.84 s.
- Два API во время первого workload: примерно 122 MiB каждый; SQL test container
  около 110 MiB. Это небольшой synthetic dataset, не прогноз общей capacity.
- Observer сохраняет агрегаты Docker stats, не env/response bodies.
- Первый запуск остановился на SSH timeout до workload. Переключён на SSH
  ControlMaster reuse; повторные два прогона прошли. Тестовые контейнеры, сети,
  firewall hooks и handshake удаляются в finally, production сервисы не затронуты.
- Firewall contract unit: **2 passed**. Raw evidence на рабочей машине:
  `/private/tmp/admirra-multihost-20260924/` и
  `/private/tmp/admirra-multihost-recovery-20260924/`.

## Окружение AI workers

Выявлено: действующий backend имеет OpenRouter, legacy automation — нет.
Предыдущий export только из automation оставлял будущие workers без нового AI
provider. Теперь export берёт только AI-ключи из backend и проверяет равенство
общих auth/encryption secrets. Явный `refresh-ai` меняет только AI allowlist,
не трогает DB/SMTP/scheduler и оставляет root-only backup прежнего worker.env.

**8 runtime tests passed**. На server 2 worker.env обновлён закрытым SSH pipe,
recovery-копия на server 1 обновлена до нового backup. Workers не запущены.

## Подтверждения владельца

Получатель и ответственный за Telegram alerts — владелец в существующем чате
с ботом. Получение firing/resolved тестов подтверждено ранее. По явному запросу
ключ восстановления передан владельцу в личный чат; его значение не сохраняется
в исходниках, документах, test artifacts или deployment evidence. Передача
в чат сама по себе не доказывает отдельное офлайн-хранение.

## Gates на момент первого прогона (обновления ниже)

- Scoped live-provider peak (manual/nightly provider IO + report render + AI,
  с жёстким budget и без customer sends/charges). Выполненные 44 теста этого
  не заменяют; `provider_peak_accepted` пока нельзя ставить true.
- Итоговый согласованный API/worker flag manifest и совместимый rollback после
  новых durable jobs; старый legacy image не должен потреблять новую очередь.
- Свежий cutover preflight, admission/drain, миграции, API1 + workers + один
  scheduler, E2E test job, затем canary API2. Ничего из этого не выполнено выше.

S3 и ожидание двух ночей остаются отложенными владельцем. Не ослаблять
fail-closed preflight ради формального завершения выкладки.

## Реальные API: найденные и исправленные несовместимости

Ограниченный read-only probe `ops/provider_read_peak.py` запускался на server 2
в сети будущих workers, с их provider/Redis конфигурацией и серверным PostgreSQL
`default_transaction_read_only=on`. Только два маленьких подключения разрешённого
тестового владельца, один день, максимум 40 внешних read-запросов. `collect` и
validation выполняются реально; production `apply`, рассылки и банковские вызовы
запрещены. Это не массовый пик всех кабинетов.

- Первый запуск с host network остановился на недоступных Docker DNS broker/cache;
  последующие используют `admirra-workers_work`, как реальные будущие workers.
- Первое VK-подключение вернуло `401 expired_token`; credentials не изменялись.
  Другое подключение того же владельца прошло: 4 кампании, 4 строки статистики.
- Выявлены реальные дефекты нового strict Direct parser: quoted report title,
  скрытые ID/названия групп Campaign Wizard и повторяющиеся названия Criteria,
  которые провайдер неявно группирует по CriteriaId. До исправления новый sync
  отклонял корректные ответы HTTP 200. Эти кандидаты нельзя выпускать.
- Исправление сохраняет суммы всех исходных строк, проверяет исходный footer count
  ДО агрегации, не придумывает group IDs. Неизвестная группа хранится SQL NULL,
  а не строкой `None`; прочие invalid IDs и duplicate snapshot keys отклоняются.
  Основание: https://yandex.ru/dev/direct/doc/ru/report-format.
- После исправлений parallel VK + Direct/Metrica read прошёл за 7.747 s:
  12 read-запросов; Direct 1 campaign / 1 opaque group / 12 keyword rows,
  186 goal rows. Production DB writes = 0, customer sends = 0, bank calls = 0.
- OpenRouter со второго сервера: два маленьких успешных запроса
  `anthropic/claude-sonnet-5`, суммарно $0.00038. Повторные ads-проверки запускались
  с `--ads-only`, без повторных платных запросов. PDF in-memory 13 272 bytes успешен.
- Новые регрессии покрывают parser, суммы, NULL group ID и idempotent apply/replay
  на изолированном PostgreSQL. Targeted ads/Direct набор прошёл; финальный новый
  immutable artifact ещё требует сборки и полной проверки.

Финальный image из `24f58b7` собран и доставлен на оба узла:
`sha256:57ac503afcdf6136a90d4bbb9903975ed98cefd9c1ca927a465f4d085930a8dd`.
В этом immutable image parallel VK/Direct/Metrica/OpenRouter/PDF probe прошёл
за 7.897 s (13 запросов, один AI за $0.00019). Итого AI-проверки этого этапа
$0.00057. Полный manifest запущен повторно; результат пока ожидается.
Production images/schema/workers не переключались.

Подготовлен [единый launch profile и границы rollback](devops-cutover-launch-profile-2026-09-24.md).
Profile/provider-budget проверки: **8 passed**, network=none. Этот source-overlay
тест не выдаётся за часть полного immutable manifest или включённый production env.

## Launch flags, восстановление и совместимый API-only rollback

- `restore_logical_backup.sh` получил opt-in `ADMIRRA_LAUNCH_PROFILE=1` и
  `ADMIRRA_ROLLBACK_LEDGER_SMOKE=1`. Проверки работают только на isolated restore
  DB, сохраняют network=none; launch profile запрещён для старой схемы. Копия
  mTLS credentials берётся из расшифрованного backup в временном каталоге;
  live PKI и live env не меняются. Credentials удаляются штатной cleanup.
- Candidate мигрировал копию до `f68b92a3b4c5`, создал synthetic queued/uncertain
  admissions. Совместимый резервный API `eb9550c` с полным launch profile прошёл
  startup и **40/40 HTTP 200**, p95 215.07 ms. Ledger не потерял очередь,
  dedupe остался действующим, unknown не replay; повторный candidate check прошёл.
  Весь restore/rollback smoke — **42 s**. Consumers в этом rollback выключены.
- Этот резервный API не является прежним legacy backend `875ab667…`; это
  durable-compatible API. Из-за известных Direct parser багов старта workers
  из `eb9550c` при rollback не допускаем. Режим — обслуживать чтения и сохранять
  backlog до forward fix, без возобновления внешних side effects.
- Повторный restore с новым `24f58b7`, полным launch profile на API/четырёх
  worker-группах и ledger markers: **passed, 71 s**, **64/64 HTTP 200**,
  p95 1641.8 ms, max 1781.39 ms. Summary 64 × 4: 848.45 ms, 12 сравнений совпали.
  Параллельно выполнялась полная регрессия. Это изолированная приёмка, не скорость
  страницы в публичном production. Расписания/рассылки не запускались.
- Дополнительные safety tests restore/rollback script: **16 passed**, 1.37 s.

Остаётся фактическое контролируемое переключение с актуальным preflight,
подтверждением отдельного хранения recovery key и наблюдением canary.
В 03:00/05:00 МСК переключение запрещено; approval владельца «выкатываем»
не является доказательством сохранённой им офлайн-копии ключа.
