# AI-комментарий: одно нажатие вместо плашек, 25.09.2026

## Поведение

- Убрана техническая DataReadinessNotice из AI-панели и её дублирующая кнопка.
  Убрана блокирующая накладка общей синхронизации: она обещала автоматическое
  обновление комментария, которого в действительности не было.
- Без действия пользователя — обычный пустой блок или сохранённый комментарий.
  Ни открытие страницы, ни приход статуса ready сами не запускают LLM.
- «Получить комментарий» / «Обновить» создаёт один локальный intent:
  GET ai/comment (coverage preflight без LLM) → при необходимости ожидание
  data-refresh → один POST ai/generate-report. Короткий skeleton:
  «Подготавливаем анализ…» → «Формируем комментарий…» → результат.
- Held от предыдущей попытки можно повторить тем же нажатием, если сервер
  разрешает: один POST подготовки /retry. Если текущая подготовка упала,
  бесконечных повторных запусков нет. Показывается ошибка и «Повторить».
- GET временные сбои: до трёх попыток, 1/2 s backoff; ожидание данных до 10 минут
  или server deadline, что раньше, polling 10 s. Все запросы имеют timeout.
- **POST генерации никогда автоматически не повторяется**, включая 409 после
  изменения данных во время LLM, 502, disconnect и timeout. Сетевой сбой после
  отправки не доказывает, что модель не отработала. Не добавляли обещание durable
  exactly-once между вкладками/перезагрузками: один intent защищён локальным
  single-flight; существующий серверный cache/throttle остаётся.
- Смена проекта, дат, папки, канала или уход со страницы отменяют ожидание;
  поздний ответ старого intent не публикуется и не запускает генерацию.
  Abort уже отправленного POST не гарантирует остановку работы на сервере.
- Ручная отправка отчётов, подтверждение отправки и детектор не переводились
  на автозапуск; их общий DataReadinessNotice не изменён.

## Проверка достаточности данных

`ai.freshness` использует `direct_freshness.period`: выбранный период и предыдущий
равной длины, без dynamics=True и без дополнительных шести месяцев.
Это соответствует контексту комментария: `_build_comment_context` использует
aggregate_summary.trends для изменений KPI. `requirements` проверяет кампании
и выбранные цели Метрики; не требует детекторного warmup. Поэтому проверки
полноты не ослаблялись и backend/DB/воркеры не менялись.

Dashboard comment не списывает видимый AI-лимит по существующему backend-коду;
реальные вызовы провайдера остаются платными для сервиса. Preflight и polling
не вызывают модель. Повтор после потери ответа — только осознанное действие.

## Тесты

- 16 новых Node сценариев: fresh/waiting/held, двойной клик, GET recovery,
  POST 409/429/5xx/disconnect без replay, deadline, legacy/invalid status,
  scope/unmount cancellation и защита нового intent от старого ответа.
- Вместе с sync/readiness regression: 37/37 passed.
- Chromium: шесть сценариев **на извлечённых настоящих template, состоянии,
  triggerAiComment и стилях AI-панели**; остальные части дашборда исключены.
  Настоящие Vue/Axios, синтетический API, всё внешнее IO заблокировано.
  Fresh, waiting→готово без второго клика, held, POST 502, смена scope, unmount.
  Скриншоты desktop idle/waiting и 390px mobile просмотрены; overflow нет.
- Это не запуск платной генерации в production и не full-page E2E всего дашборда.

## Выкладка

Только frontend overlay из clean git archive, без dirty MainLayout/SignIn/landing.
Сохранить public landing/legal и старые chunks. Не менять Nginx keepalive,
API, БД, воркеры, схему и настройки оплаты. Старые открытые вкладки обновить.

### Production acceptance

- Source **64c45d9**, pushed; frontend запущен 25.09.2026 12:56:47 UTC.
- Image `sha256:cd4685ef18524f5cac4fb8a9a2dc65f93543385db64b1e1e8c175c6159fb72c4`;
  entry `/assets/index-lqRwTCME.js`, dashboard `/assets/GeneralStats3-CiytNKOk.js`.
  Публичный dashboard chunk совпал с clean build по SHA256
  `d148e5c6fda1354a86d63b598eb959bae0d10340d910dfa133681fda955c601c`.
- Overlay подтвердил неизменность landing/legal/Nginx и API/DB контейнеров.
  В 12:57:05 UTC оба API ready=ok, release 32a8d9e, alerts=[].
- Snapshot/rollback compose:
  `/etc/admirra/releases/frontend-readiness-64c45d9/`, previous=fdf2f4a.
  Build context `/opt/admirra-ai-64c45d9/frontend/`.
