# Онбординг и первая скидка — 25.09.2026

Источник ТЗ: `admirra_onboarding_dev_task.html`. Старые локальные тестовые
изменения MainLayout, SignIn и `landing/` не включать в сборку/коммит.

## Изменения

- Вместо модального окна и полосы: TrialCard в прокручиваемой части SidebarV2,
  между тарифами и поддержкой. Скрывается в свёрнутом меню, доступен в мобильном.
- Состояния: создать проект, подключить кабинет, скидка получена, триал завершён;
  оплаченные аккаунты и участники чужого биллингового аккаунта не получают карточку.
- Нулевой список проектов ведёт на существующий встроенный экран `/create`.
  После создания сохраняется переход в мастер с `client_id`.
- Строка предложения в мастере только до первого рекламного подключения.
  Пустой дашборд предлагает подключение именно текущего проекта, вместо плана.
  Не считать наличие семи placeholder-каналов признаком подключённых кабинетов.
  Ошибка/незавершённая загрузка не считается достоверным пустым проектом.
- Toast 5 секунд после серверного claim; старые гранты/сроки/claim не сбрасываются.
- API статуса расширен лёгкими агрегатами владельца; никаких запросов к рекламным
  провайдерам. Frontend делит один запрос между блоками, TTL 15 секунд,
  обновляет после создания/подключения/оплаты, при возврате к проектам и во вкладку.
  Таймер пересчитывает дни и срок без частого polling. При ошибке предложение скрыто.
- Standalone Метрика не выдаёт скидку: сохраняется существующая политика
  Direct/VK/Avito. Второй пустой проект не обещает повторную скидку.
- Milestone JSON claims сериализованы блокировкой одной строки пользователя.
  Новые цели signup_offer_click/support_chat_click; integration_connected получает
  channel/from_offer. Маркер привязан к аккаунту и вкладке, TTL 24 часа.
- payment_success и новый browser trial_to_paid получают discount=signup20/year/none
  и фактически списанную сумму из защищённого confirmation endpoint.
  Новые вкладки объявляют capability onboarding_analytics; старые заказы/вкладки
  сохраняют прежний offline trial_to_paid. Новые manual trial intents не дублируют
  цель офлайн. Как и существующий browser payment_success, это зависит от открытия
  страницы подтверждения и отсутствия блокировщика Метрики; гарантированной
  доставки browser analytics нет. Фоновые рекурренты не меняются.

## Чек и ограничения приёмки

Сумма позиции уже снижена. Отдельная строка скидки передаётся как
`userRequisiteData` (ОФД 1084) и `additionalReceiptInfos`, а не отрицательная позиция.
Если годовая скидка больше, строка и аналитика называют годовую скидку.
Сумма позиций = электронная оплата; рекуррентный чек без разовой скидки.
Поддержка полей: https://developers.cloudkassir.ru/ .
У offline conversions нет произвольного поля discount:
https://yandex.com/dev/metrika/ru/management/offline-conv .
Реальный фискальный чек этим релизом не выпускается, деньги не списываются.
Отображение отдельной строки кассой требует просмотра фактически полученного чека;
прохождение теста payload не является такой проверкой.

## Проверки и выкладка

Изолированные PostgreSQL/tests: `ops/signup_discount_qa.py`, WW_TEST=1,
internal Docker network, synthetic accounts, provider calls mocked, лимиты CPU/RAM.
Frontend: Node tests + `tests/onboarding.browser.mjs` с настоящими компонентами
и подменёнными API/аккаунтом; 320/390/768/1440 px, светлая/тёмная тема, создание,
client_id, исчезновение offer, toast, истечение, оплата, дедуп целей, возврат,
свёрнутое меню. Никакие данные настоящих пользователей для этих сценариев не меняются.

Release: clean git archive; API overlay только auth/billing/schemas/два сервиса.
Перед activation: проверить совпадение текущего API image/release, runtime snapshots
root-only, candidate tests. API2 вывести из upstream через onboarding_ingress,
дождаться ухода старых Nginx workers, обновить/проверить, восстановить upstream.
Аналогично API1 (включая временный перенос named primary/docs на API2).
Затем frontend overlay index/assets, сохраняющий landing/docs/старые chunks.
БД/воркеры/шифрование/тарифные цены/секреты/CloudPayments настройки не изменяются.

После: оба /health/ready, authenticated read-only signup-discount, публичные assets,
нет новых 5xx/ошибок, мониторинг. Откат API через сохранённый previous.json,
с выведением соответствующей ноды и проверкой ready; ingress restore из snapshot.
Frontend — frontend-previous.json. Не запускать legacy automation.

## Production-приёмка

- Фронтенд выложен 25.09.2026 08:25 UTC, source `25553f5` (frontend bytes
  совпадают с проверенным clean archive `2f9804d`, последующие изменения — backend/ops).
  Image `sha256:c5d1bbb072ac99fd8cab581ede80a3b3cfb5374d9a69414a269797879ad1c9e8`.
  Entry `/assets/index-C64BJ-6K.js`. Конфиги и автоматический откат:
  `/etc/admirra/releases/frontend-readiness-25553f5/` на API1.
  Публичные index + 4 JS chunks совпали по SHA-256. Старый entry и маскот доступны.
  Landing/legal/Nginx frontend сохранены, посторонние dirty файлы не включены.
- Frontend: 41 Node-тест и изолированный браузерный прогон настоящих компонентов
  на четырёх ширинах, светлой/тёмной теме; screenshots просмотрены. Build passed.
- API candidate `6233284`: 105 тестов на изолированном PostgreSQL passed,
  включая обычную годовую оплату без signup-гранта (метка `year`, цена не меняется).
  Рабочее дерево до candidate: 129 backend-тестов passed; это не отдельное
  подтверждение всех путей итогового образа, итоговый candidate проверен отдельно.
- Read-only статус на первом production rollout: оба API и публичный домен HTTP 200,
  counts сверены с БД владельца тестового аккаунта. Повторный прогон: API1 11–23 ms,
  API2 17–25 ms, внешний HTTPS 97–224 ms. Это latency **статуса онбординга**, не дашборда.
- В маркетинговом счётчике 109911357 созданы и прочитаны обратно две цели:
  signup_offer_click = **663715339**, support_chat_click = **663715340**.
  integration_connected / payment_success / trial_to_paid существовали, не менялись.
  Использован настроенный OAuth маркетингового счётчика, не токены рекламных проектов.
  Реальные конверсии этим действием не отправлялись; появление событий в отчётах
  Метрики нужно смотреть после настоящих действий пользователей.

### Два 500 во время первого переключения

08:23:05 UTC: старый API1 (`60965ca`) вернул 500 на GET `/api/ai/comment` (5.077 s)
и GET `/api/clients/{id}/directions/stats` (5.100 s), когда API2 был выведен из upstream.
Это не транспортные 502 при рестарте: ответы пришли от приложения API1.
Запросы действительно не получили штатного ответа; не называть это ложными алертами.
Направления снова дали 200 в 08:23:21, AI comment — 200 в 08:26:21.
После первого rollout новых 5xx не было, алерты естественно погасли к 08:33:57 UTC
после выхода событий из десятиминутного окна. Алерты не отключались и не очищались.

Точная причина по Python traceback не восстановлена: старый Docker log исчез
при пересоздании API1. Времена около 5 s совместимы с ожиданием пула БД, но это
гипотеза, не установленный диагноз. PostgreSQL ошибок за интервал не показал.
Добавлен bounded root-only `pre-activation-logs.json` в helper будущих rollout,
чтобы не терять traceback. Отдельный follow-up: проверить запас ёмкости одного API
под настоящими тяжёлыми запросами при drain; не считать этот инцидент исправленным
изменением онбординга или увеличивать пул вслепую.

### Итоговый rolling update

- Оба API работают на `6233284`, image
  `sha256:b5246d3aa40165b1a535b1fa08bcb8286a7e5d57bf511363f452e6b202a201ce`.
  API2 запущен в 08:40:58 UTC, API1 — 08:42:00 UTC; restarts=0.
  На каждой ноде root-only конфиги и предыдущая версия:
  `/etc/admirra/releases/onboarding-6233284/`.
- Перед каждым restart нода исключалась из ingress; старые Nginx workers
  завершились до активации. Исходный ingress восстановлен из точного snapshot
  `/etc/admirra/releases/onboarding-ingress-6233284/` на API1.
  Runtime environment (кроме APP_RELEASE), ports, mounts и networks совпали.
  Снимки pre-activation logs сохранены на обеих нодах с правами 0600 root.
- Оба `/api/health/ready`: status=ok, role=api, release=6233284.
  Authenticated read-only приёмка: по три HTTP 200 на каждой ноде и admirra.ru,
  контракт и количество проектов сверены с БД. API1 14–35 ms, API2 23–37 ms,
  публичный HTTPS 104–199 ms (только endpoint онбординга).
- На 08:42:46 UTC новых 5xx в canary access log с 08:39:00 UTC — 0;
  ERROR/Traceback/FATAL в новых API-контейнерах — 0; Prometheus alerts=[];
  frontend image и entry не менялись при втором переключении.
- Дополнительный браузерный прогон после релиза passed: from_offer расходуется
  один раз, повторные клики поддержки не дублируют support_chat_click.
  Это изолированные события, не конверсии настоящего счётчика.

### Откат итоговой версии

На API1 из `/opt/admirra-onboarding-6233284`:
`python3 -m ops.onboarding_ingress api2 --root /etc/admirra/releases/onboarding-ingress-6233284`.
Дождаться завершения старых workers. На API2 из такого же каталога:
`python3 -m ops.deploy_dashboard_lockfix rollback --container admirra-api2-api-1 --root /etc/admirra/releases/onboarding-6233284 --release 6233284`.
Проверить readiness, восстановить ingress командой с action `restore`.
Для API1 повторить с action `api1` и container `admirra-backend-1`.
Этот откат возвращает предыдущий backend `25553f5` (онбординг уже присутствует).
Для полного отката до онбординга отдельно сохранён предыдущий backend в
`/etc/admirra/releases/onboarding-25553f5/previous.json`; его нельзя применять
без такого же drain/readiness-процесса.

Frontend rollback на API1:
`docker compose -p admirra -f /etc/admirra/releases/frontend-readiness-25553f5/frontend-previous.json up -d --no-deps --no-build --pull never frontend`.
После любого отката проверить публичные assets, status endpoint и мониторинг.
