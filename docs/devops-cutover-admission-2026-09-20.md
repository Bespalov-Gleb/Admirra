# Cutover admission gate

Дата: 20.09.2026. Статус: Nginx gate и atomic manager подготовлены и изолированно проверены; до отдельной установки production Nginx не изменён.

## Зачем нужен отдельный gate

Проверка «очередь сейчас пуста» недостаточна: между проверкой и остановкой legacy consumer пользователь может запустить новую синхронизацию, отчёт или AI-запрос. Gate закрывает только вход для долгих/платных/external-side-effect операций, после чего уже принятые операции можно безопасно drain. Он находится на ingress и поэтому одинаково действует на текущий `cdf0a4d` и candidate API.

При `closed` блокируются с HTTP 503:

- mutations `/api/assistant/*`;
- AI chat/generate-report/comment;
- mutations `/api/reports/*`;
- оба ручных sync endpoint;
- запуск dynamics backfill.

Продолжают работать обычные dashboard reads, авторизация, настройки вне перечисленных контуров, CloudPayments callbacks и лидовые webhooks. Ответ содержит `Retry-After: 60`, `Cache-Control: private, no-store`, `X-AdMirra-Admission: closed` и стабильный код `cutover_drain`.

## Устройство

- `admirra-cutover-map.open.conf` — default allow, используется при обычной работе;
- `admirra-cutover-map.closed.conf` — точный список закрываемых method/path;
- `admirra-cutover-admission.conf` — server-level guard и JSON 503;
- `manage.py install|open|closed|status` — atomic replace → `nginx -t` → reload; при любой ошибке восстанавливает прежние файлы и конфигурацию.

`install` патчит только два известных HTTPS site-файла по единственному `client_max_body_size 20m` anchor. Неизвестная/дублированная структура блокирует установку. До изменения создаётся root-only backup реальных symlink targets и прежних gate-файлов в `/root/admirra-cutover-admission-backups/<UTC>`.

## Проверка

- 7 unit tests: exact/idempotent patch, ambiguous-layout refusal, open/closed route inventory, resolved-site backup — pass;
- реальный `nginx -t` на временном prefix — pass;
- временный Nginx на loopback проверен восемью HTTP-кейсами:
  - GET ассистента не блокируется;
  - POST assistant/AI/report/manual-sync/backfill → 503 с нужными headers/body;
  - CloudPayments и lead webhook POST → не блокируются.

Тестовый Nginx остановлен и временные файлы удалены; production-конфигурация при тесте не менялась.

## Эксплуатация

После установки gate остаётся в `open`. В согласованном окне:

```sh
python3 manage.py closed
python3 manage.py status
```

После drain/migration/API-worker smoke и решения оператора:

```sh
python3 manage.py open
```

`closed` не останавливает уже начатые операции и не заменяет проверку БД/воркеров. При проблеме команда `open` — первый безопасный откат ingress; текущие running/uncertain side effects отдельно reconciled, а не повторяются автоматически.
