# Детектор: подготовка истории и статус готовности

## Диагностика БВК Новый / ВК

24.09 две последние ручные синхронизации завершились SUCCESS примерно за 7 секунд.
Детектор дополнительно запросил историю 04.08–24.09; два history.backfill задания
завершились без ошибок (окна 04.08–02.09 и 03.09–16.09). Текущие даты уже были
подтверждены обычным обновлением. На момент проверки consumer readiness = ready,
очереди queued/running пусты. Не было основания перезапускать синхронизацию.

Наблюдаемая проблема UI: одинаковый текст одновременно в DetectorBanner и
DataReadinessNotice; заголовок смешивает отсутствие текущей статистики с
неподтверждённой историей; завершение вложенного polling не обновляло summary.

## Исправлено

- Одна компактная строка пояснения вместо вложенной второй карточки.
- Состояния: проверяем полноту / подготавливаем историю / приостановлено / готово.
- Готовность один раз на receipt+deadline вызывает только чтение detector summary.
  Старый баннер снимается по ответу backend, не оптимистически.
- Никаких автоматических AI-запросов, экспорта таблиц или отправки отчётов.
  Общий компонент сохраняет отдельное ручное событие `ready-action`.
- В скрытой вкладке polling приостанавливается; после возвращения один status GET.
  Повторные статусы ready не образуют цикл. Ошибка сети требует явной проверки;
  unmount отменяет запрос/таймер. Предел ожидания и разрешение retry сохранены.
- Светлая/тёмная темы, mobile 390px без горизонтального переполнения. Исправлен
  scoped/global селектор, чтобы dark-стили не применялись к корневому `.dark`.

Это frontend hotfix, **не ускорение загрузки данных из VK**. Coverage/freshness,
24-часовой порог по умолчанию, исторические окна и backfill workers не менялись.
Пересмотр повторного обновления давней истории требует отдельной политики
свежести и backend-тестов; не заменять доказанную полноту на `last_sync_at`.

## Проверки

- 30 Node utility tests passed, включая 7 readiness tests.
- Изолированный browser fixture `tests/readiness.browser.mjs`: waiting→ready
  удаляет баннер, дубли ready не повторяют summary refresh; generic consumers
  не выполняют action без клика; hidden/unmount/error/held/retry проверены.
  Только mock API, без production credentials или реальных синхронизаций.
- Скриншоты desktop/mobile/dark просмотрены; computed dark colors проверены.
- Production build из clean git archive, без owner dirty файлов. Контрольный
  rebuild прежнего source aeefa00 совпал с production index SHA256
  `631349582dcc18f90759409378269f5d36ce3b203f01a6fef5753deab36d9371`.

## Production

Source `6c00e1d` (UI commit `0ce9d24` + theme/deploy follow-up), pushed.
Image `sha256:6119ccfe0a40e9461f42b16f6bbb53f883857da57dc078c9ccdb34a0c9957660`.
SPA entry `/assets/index-Dc1ARDEc.js`.
Active/previous configs and acceptance:
`/etc/admirra/releases/frontend-readiness-6c00e1d/` on server1.
Build/deployer `/opt/admirra-frontend-readiness-6c00e1d/`.

Overlay replaces only SPA index + hashed assets, keeping existing landing,
documents and older chunks. Verified their checksums, env/mounts/ports and
unchanged API/DB/legacy automation container IDs; API ready. No worker changes.
Public `/`, `/signin`, `/ai`, legal document and old entry all HTTP200; new
readiness JS bytes match the built artifact. Waiting-state acceptance is the
isolated fixture, not a fabricated live customer refresh.

Rollback frontend only (first verify active image has not changed since):

```sh
docker compose -p admirra -f /etc/admirra/releases/frontend-readiness-6c00e1d/frontend-previous.json up -d --no-deps --no-build --pull never frontend
```

Do not run blanket compose from the legacy checkout. Leave owner changes in
MobileProjectTile/mobile.css/MainLayout/SignIn/landing untouched.
