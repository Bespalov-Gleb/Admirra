# AdMirra — отдельный AI-шлюз и переключение ассистента

Дата: 15.09.2026. Статус: **шлюз включён, production-ассистент переключён**.
Это отдельный этап, не завершение общего DevOps-ТЗ и не деплой накопленных application-коммитов.

## Фактическая схема

`backend на 91.221.68.90 → WireGuard admirraai → 10.78.0.3:8080 на 194.87.134.173 → HTTPS OpenRouter`

- Новый VPS: 1 vCPU AMD EPYC, 1895 MiB RAM, диск 28 GiB / свободно около 26 GiB, Ubuntu 26.04.1 LTS, KVM.
- IP-info: сеть Timeweb, Amsterdam/NL; OpenRouter/Cloudflare также определил IPv4 и IPv6 как NL.
- Это сетевые наблюдения, не независимое подтверждение физического размещения или юридической доступности моделей.
- На сервере приложения WireGuard `10.78.0.1/32`, на шлюзе `10.78.0.3/32`, UDP 51821, MTU 1380, keepalive 25.
- AllowedIPs только адрес противоположного узла `/32`. Default route, DNS, существующий `admirra0` для серверов 1/2, PostgreSQL/Redis не менялись.
- Сервер 2 пока **не подключён** к AI-туннелю. Адрес `10.78.0.2` и публичный IP зарезервированы в правилах; ключ/peer не добавлены. Не путать с прежним `10.77.0.2`.

## Что включено на шлюзе

- SSH-ключ владельца добавлен; независимый вход по ключу проверен до изменения политики SSH.
- `PasswordAuthentication no`, `KbdInteractiveAuthentication no`, root допускается только по ключу. Пароль не сохранён в репозитории. Пароль консольного входа не менялся.
- nftables: входящие по умолчанию запрещены. Доступны SSH, ICMP; WireGuard только от серверов 1/2; HTTP 8080 только внутри AI-туннеля от разрешённых адресов.
- Zabbix 10050 сохранён только для трёх адресов мониторинга, найденных в конфигурации провайдера. Публичный 10050 закрыт.
- Nginx 1.28.3: единственный HTTP listener `10.78.0.3:8080`. Нет публичного сайта/прокси и произвольного CONNECT/upstream.
- Разрешены только `GET /healthz`, `GET /api/v1/models`, `GET /api/v1/key`, `POST /api/v1/chat/completions`. Остальные пути 404; запрещённые методы 403.
- Upstream жёстко задан `openrouter.ai`, TLS с проверкой CA/SNI. DNS обновляется раз в 60 секунд, исходящий HTTPS прокси использует IPv4.
- WireGuard шифрует внутренний HTTP; дальше TLS до OpenRouter. Сам nginx терминирует этот внутренний HTTP и видит запрос в памяти — это не end-to-end TLS от контейнера до провайдера.
- Streaming без response/request buffering, cache и повторов upstream. Разрыв клиентского соединения не игнорируется. Connect timeout 10 с, read/send idle timeout 180 с.
- Общий предел 100 одновременных HTTP-запросов, превышение 429. Это защитная настройка, не обещание квоты OpenRouter.
- Body limit 8 MiB, buffer 128 KiB. MemoryHigh/MemoryMax nginx 384/512 MiB, TasksMax 64, LimitNOFILE 8192.
- Access logs: время, HTTP/upstream status, длительность и число байт. Без промптов, Authorization, query string, текста ответов. Ключ OpenRouter хранится только в существующей конфигурации backend, не на диске шлюза.
- Штатный logrotate nginx: daily, 14 архивов, compression. Автостарт WireGuard/firewall/nginx и timer проверки состояния.
- Проверка каждые ~5 минут: systemd units, свежесть WireGuard handshake, private TCP listener, TLS/формат публичного каталога моделей. Нет платной генерации, ключей или автоматических перезапусков backend.
- Результаты проверок пока только в systemd journal. **Внешнее оповещение дежурному не подключено**; полноценный мониторинг остаётся в общем ТЗ.

## Production-переключение

Перед переключением проверено: текущий Compose environment совпадал с запущенным backend; постороннего env drift не было.

Изменены только:

```dotenv
AI_ASSISTANT_PROVIDER=openrouter
OPENROUTER_BASE_URL=http://10.78.0.3:8080/api/v1
```

Существующий `OPENROUTER_API_KEY` принят `/api/v1/key`. Он не копировался в новый публичный сервис и не выводился.

Backend пересоздан **без build, pull и перезапуска зависимостей**, с закреплением уже запущенного образа:

`sha256:778c896e65f79be3fb33748c1c819d22dc7fd3ffb677505bf2fe987b43bbb2c8`

Git рабочего приложения остался `cdf0a4d`. Миграции не запускались. Фронтенд, automation, БД, расписания и сервер 2 не переключались. Локальные DevOps-изменения до `279af12` этой операцией не выкатаны.

**AI-комментарии дашборда и detector-LLM остаются на byesu / Claude Sonnet 5 через прежний `OPENAI_*`-конфиг.** Этот этап переключает `/ai`-ассистента, а не все LLM-клиенты на иной протокол. Активная модель UI: `google/gemini-3.7-flash`.

## Проверки и результаты

1. Публичный OpenRouter catalog: IPv4/IPv6 HTTP 200. Начальный IPv4 запрос 64 мс — это каталог, не время генерации.
2. Private health из хоста приложения и **из реального backend-контейнера**: HTTP 200.
3. `/api/v1/key`: 200, key valid, не free-tier; нужный model slug есть в каталоге.
4. Первоначальный synthetic запрос с `reasoning.effort=none` отвергнут HTTP 400: для этой модели reasoning обязателен. Probe исправлен на low; app с medium прошёл тесты без изменения бизнес-кода.
5. Бounded synthetic test: forced tool-call → синтетический результат 42 → финальный текст. Два SSE-потока завершились `[DONE]`, причины `tool_calls`/`stop`, usage/cost переданы.
6. Два дополнительных прогона через **фактический production `ai.assistant.llm.stream_completion`** с medium: до переключения с process-local override и после переключения с `--use-current` без override. Оба: инструмент → результат → финальный ответ; без цикла повторных инструментов в этом сценарии.
7. Все платные тесты ограничены max_tokens=1024 на запрос. Шесть успешных коротких генераций, суммарный возвращённый `usage.cost` **$0.000915**. Это не оценка стоимости реальных аналитических диалогов и не включает комиссию покупки кредитов. Клиентские проекты/личные данные не отправлялись.
8. Изолированный nginx + loopback mock, без внешних запросов: 25/50/100 параллельных SSE; правильные chunks/DONE и получение первого chunk до завершения ответа. Финальный прогон max first chunk 8/10/23 мс. Нет повторного запроса при upstream 503, исходный код ошибки сохранён. Проверены path/method guards.
9. Это короткие синтетические потоки на одном VPS, **не долговременный distributed load test и не 100 реальных LLM-сессий**. Нет подтверждения будущей ёмкости/квот/суточного SLA.
10. Шлюз перезагружен до переключения продакшена: WireGuard, firewall, nginx и timer восстановились; вход по ключу работает, парольный SSH выключен.
11. ICMP после handshake: 5/5 ответов, 0% потерь, ~112,5 мс между шлюзом и узлом приложения. В первом коротком запуске один пакет потерян при установлении туннеля; не скрываем этот замер.
12. Снаружи TCP 8080/10050/80 не соединяется. Из неразрешённого локального адреса gateway `/healthz` вернул 403. С app узла запрещённый метод 403, неизвестный путь 404.
13. После переключения: фактический provider/base проверен в новом контейнере, `SELECT 1` успешно, сайт/openapi HTTP 200, `/api/assistant/models` без авторизации 401 (защита не обойдена). Образ совпал с исходным digest.
14. Память nginx после проверок около 5,2 MiB; доступно ~1530 MiB RAM. Это спокойный snapshot, не peak под рабочей нагрузкой.

## Файлы и диагностика

Версионируемые шаблоны/скрипты: `ops/ai-gateway/`.

На шлюзе:

- `/etc/wireguard/admirraai.conf`, `.key`: 0600, не печатать содержимое.
- `/etc/admirra-ai-gateway/gateway.nft`.
- `/etc/nginx/conf.d/admirra-openrouter.conf`, `/etc/nginx/snippets/admirra-openrouter-proxy.conf`.
- `/etc/systemd/system/nginx.service.d/admirra.conf`.
- `/etc/ssh/sshd_config.d/00-admirra-key-only.conf`.
- `/opt/admirra-ai-gateway/check_health.py`; units `admirra-ai-firewall`, `admirra-ai-health.service/.timer`.
- `/root/admirra-gateway-setup/`: копии исходных шаблонов для обслуживания. Актуальные probes брать из git.

```sh
systemctl status nginx wg-quick@admirraai admirra-ai-firewall
systemctl start admirra-ai-health
journalctl -u admirra-ai-health -n 30 --no-pager
wg show admirraai
nginx -t
```

`wg show` скрывает private key. Не использовать `wg showconf`, `wg ... dump`, `cat .env`, `docker compose config` без фильтрации — могут раскрыть секреты.

Локальные неплатные регрессии:

```sh
python3 -m unittest discover -s ops/ai-gateway -p test_config.py
```

Изолированный runtime test на шлюзе: положить рядом `test_gateway.py`, `openrouter.conf`, `proxy.conf`, затем `python3 test_gateway.py`. Порты 18080/18081 только loopback; live nginx не перезагружается.

Read-only проверка с production-хоста (внутри контейнера, исходник передаётся stdin):

```sh
docker exec -i admirra-backend-1 python - --base http://10.78.0.3:8080/api/v1 < probe.py
```

`probe.py --paid-smoke` и `probe_adapter.py` выполняют платные синтетические запросы. Не запускать их циклически/по cron. Health timer их не использует.

## Откат

На сервере приложения сохранено:

`/root/admirra-ai-switch-backups/20260915T084354Z/`

Каталог 0700, файлы 0600: исходный `.env`, metadata с хешами, Compose override с **исходным image digest**. Скрипт: `/root/admirra-ai-switch.py` (исходник `ops/ai-gateway/switch_assistant.py`).

```sh
python3 /root/admirra-ai-switch.py --rollback /root/admirra-ai-switch-backups/20260915T084354Z
```

Восстанавливает прежний env и пересоздаёт только backend на том же image, возвращая ProxyAPI. При изменении `.env` после переключения скрипт откажется затирать его: сначала сверить новые изменения и сделать точечный откат двух переменных. Если после этого этапа уже выкатан новый application image, **не откатывать вслепую весь старый образ**, пересмотреть план.

Откат переключения протестирован unit-тестом с временными файлами; реальный обратный restart production после успешного переключения не выполнялся.

Нельзя отключать `wg-quick@admirraai`/nginx на шлюзе, пока backend использует новый base URL. Сначала вернуть провайдера. Существующий `admirra0` не трогать.

## Что не закрыто этим этапом

- Отказоустойчивость: AI gateway один. Автоматический failover на ProxyAPI отсутствует; автоматический повтор неоднозначно завершившегося платного запроса намеренно не добавлен.
- Подключение будущего API/worker узла 2: отдельный peer/ключ, маршрут, проверка Docker egress и доступа. Не переносить gateway firewall на серверы приложения!
- Central alerts, долговременная нагрузка, cost limits/ledger/uncertain outcomes и остальные требования общего DevOps-ТЗ.
- Полное UI/многопроектное ревью ассистента, длинные цепочки инструментов и все модели каталога этим небольшим synthetic сценарием не подтверждены. Нужен пользовательский приёмочный диалог в `/ai`.
- Право доступа организации/пользователей к каждой модели должно соответствовать [условиям OpenRouter §5.7](https://openrouter.ai/terms). Иностранный сервер сам по себе такого права не даёт; письменного подтверждения OpenRouter в рамках этого этапа не получено.

Технические первоисточники: [Nginx proxy module](https://nginx.org/en/docs/http/ngx_http_proxy_module.html), [WireGuard quick start](https://www.wireguard.com/quickstart/).
