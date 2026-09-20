# Production cutover preflight

Дата: 20.09.2026. Статус: fail-closed gate реализован и проверен; production cutover не запускался.

## Назначение

`ops/cutover_preflight.py` проверяет единый evidence bundle непосредственно перед переключением. Он не выполняет миграции, не останавливает процессы, не обращается к providers и не читает production credentials. Его задача — запретить начало cutover, если хотя бы одно обязательное доказательство отсутствует, устарело или относится не к утверждённому artifact.

Проверяются:

- окно не длиннее четырёх часов, назначенные основной и rollback-операторы, запрет 03:00/05:00 МСК;
- точные production/candidate commits, candidate/rollback image digests и schema head;
- clean tracked tree, regression/config/restore evidence;
- свежая внешняя recovery point, release manifest, PITR chain и escrow ключа; для первого запуска допустимо только отдельное owner-accepted исключение не более 30 дней при свежем проверенном server-2 backup и офлайн-копии ключа;
- свежий firing/resolved test доставки алерта человеку и внешний heartbeat не старше пяти минут;
- отсутствие параллельного deploy, активных legacy sync/report/AI операций, uncertain jobs, expired leases и firing alerts;
- readiness обоих API, capacity, worker boot, read-load и отдельно принятый provider/report/AI/billing peak;
- явное подтверждение владельца и разрешённый test scope.

`ops/cutover_evidence.example.json` — намеренно незаполненный шаблон. Он обязан возвращать `blocked`; `REQUIRED`/`false` нельзя заменять предположением. Evidence собирается заново перед каждым окном, а не переносится из предыдущего запуска.

## Запуск

```sh
python3 ops/cutover_preflight.py /secure/path/cutover-evidence.json \
  --expected-production-commit cdf0a4d3c9dee66722219d7e7e2924d5475c0044 \
  --expected-candidate-commit acf6ed8d76ea13436152e8ccc9659346169c7040 \
  --expected-candidate-image sha256:ad9559725e724789281765526f85839b8b9adf604c114ad25850812b0c544d0a \
  --expected-rollback-image sha256:047c8019bbbeec83c0c8cd11b39c03b31af2931d8e2f0b415196199f8768afe0 \
  --expected-schema bc8d9e0f1a2b
```

Код возврата `0` разрешает перейти к ручному шагу admission/drain из основного runbook; код `2` блокирует переключение. Даже успешный preflight не выполняет следующий шаг автоматически. Bundle может содержать внутренний test-scope, поэтому его хранят в защищённом release-каталоге и не коммитят.

## Проверка

- `py_compile` — pass;
- 25 сценариев: полный pass, ограниченное backup-исключение, stale evidence/heartbeat, неверный candidate/rollback artifact, соответствие сохранённому rollback manifest, запрещённое время, active/uncertain jobs, placeholder/ложные/неверно типизированные подтверждения — pass;
- совместно с worker-capacity, backup receiver/retention и API-2 monitor: **62 passed**, один ожидаемый pytest cache warning из-за read-only rootfs;
- тесты выполнены в immutable candidate image, `network=none`, `read_only`, без production mutations;
- незаполненный example возвращает `blocked` по 17 причинам.

Preflight принимает rollback digest только при точном совпадении с сохранённым production backend из `ops/rollback_images.json`; произвольный валидный SHA больше не проходит. Строки-заглушки `REQUIRED*` не считаются оператором, test scope или подтверждением, а heartbeat обязан иметь свежий timestamp. Gate автоматизирует решение «можно начинать или нельзя», но не создаёт отсутствующие внешние доказательства. На текущий момент остаются channel/receiver, approved provider test scope и назначенное владельцем окно. Решение временно отложить S3/PITR представлено отдельным ограниченным исключением: оно не может жить более 30 дней, требует свежий проверенный backup на server 2 и офлайн-копию ключа и не отмечает внешний backup выполненным.
