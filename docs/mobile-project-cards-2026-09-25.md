# Мобильные карточки — 25.09.2026

## Scope

По явному запросу владельца опубликованы только ранее подготовленные мобильные
правки: `MobileProjectTile.vue`, `mobile.css`, их SSR и browser tests.

- Один канал: убрать повторную строку расход/лиды/CPL. Баланс остаётся.
- Несколько каналов: сохранить разбивку. Нет каналов/не выбраны цели:
  сохранить объяснение, не выдавать отсутствие данных за нулевые показатели.
- Кнопки слева направо: другие действия → настройки → отчёт → аналитика.
  У папок нет меню действий над проектом. Обработчики событий не изменены.
- Дополнительные 8 px белого пространства под периодом на мобильной странице
  проектов; dashboard slice и desktop не меняются.

Сравнение с deployed source `6c00e1d`: до этого релиза новых committed изменений
в src/public не было. MainLayout, SignIn, landing и все посторонние untracked
ресурсы не включены. Сборка сделана из `git archive 63815bc`, не dirty worktree.
Статические public-файлы вообще не переносятся в production overlay.

## Проверки

- 36 Node tests passed (utils + 6 SSR component tests).
- Browser fixture: 20 вариантов — 320/375/390/430 px, папка/проект,
  0/1/2 канала, невыбранные цели; нет горизонтального overflow и JS ошибок.
- Проверены фактические клики и события settings/report/open, открытие меню,
  порядок кнопок, баланс и отступ. Скриншот 390 px просмотрен.
- Production build successful (только предупреждение о возрасте Browserslist).
- Fixture запускается с `WW_TEST=1 WW_TEST_ID=mobile-cards-20260925`, блокирует
  внешние запросы и не использует реальные проекты/авторизацию.

## Production

Source: `63815bc`, pushed to `metrics-fallback-fix`.
Frontend image:
`sha256:b99bdde1ccc99c90b60a1b00186830f966ff0b17f96645a874eef03c1fa86692`.
SPA entry: `/assets/index-DbhGAFgo.js`.
Host: API1, `/opt/admirra-mobile-63815bc`.
Active/previous/acceptance: `/etc/admirra/releases/frontend-readiness-63815bc/`
(название prefix сохранено общим deploy helper).

Overlay основан на предыдущем production image `6119ccfe…`, меняет только SPA
index и hashed assets, сохраняет старые chunks для открытых вкладок. Deploy
helper проверил неизменность landing, legal files, Nginx config, env, mounts,
ports, API/DB/legacy automation IDs; API readiness и публичные HTML успешны.
Worker-сервисы, API2 и host Nginx не изменяются.

Откат только frontend, сначала сверить текущий image с указанным выше:

```sh
docker compose -p admirra \
  -f /etc/admirra/releases/frontend-readiness-63815bc/frontend-previous.json \
  up -d --no-deps --no-build --pull never frontend
```

Не выполнять blanket compose из старого checkout. Оставшиеся локальные
тестовые изменения MainLayout/SignIn/landing владелец просил не трогать.
