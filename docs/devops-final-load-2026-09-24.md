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

## Ещё не принятые gates

- Scoped live-provider peak (manual/nightly provider IO + report render + AI,
  с жёстким budget и без customer sends/charges). Выполненные 44 теста этого
  не заменяют; `provider_peak_accepted` пока нельзя ставить true.
- Итоговый согласованный API/worker flag manifest и совместимый rollback после
  новых durable jobs; старый legacy image не должен потреблять новую очередь.
- Свежий cutover preflight, admission/drain, миграции, API1 + workers + один
  scheduler, E2E test job, затем canary API2. Ничего из этого не выполнено выше.

S3 и ожидание двух ночей остаются отложенными владельцем. Не ослаблять
fail-closed preflight ради формального завершения выкладки.
