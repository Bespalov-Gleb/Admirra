# Документы и проверка Яндекс ID — 24.09.2026

## Изменения

Три публичных документа (`agreement`, `user-agreement`, `personal-data`):
настоящий `/landing-new/assets/img/logo.png` в шапке и футере; шапка с текущего
production лендинга, её навигация и действия. Якоря ведут на главную (`/#...`),
а не на отсутствующие разделы документа. Мобильное меню открывается кнопкой,
закрывается Escape, кликом вне шапки, уходом фокуса, переходом по ссылке и
сменой breakpoint. Никаких auth guard, редиректов авторизации или тяжёлого
landing JS на документах нет. CSS/JS имеют версию URL для сброса старого кэша.

Юридический текст сохранён: все три SHA-256 проверены существующим тестом.
Пять Node tests passed. Изолированный static preview: все три страницы на
1440/1024/768/390/320 px без горизонтального переполнения, оба логотипа загружены;
мобильное меню и Escape/outside click проверены. Desktop/mobile/footer screenshots
просмотрены. Проверки делались в отдельном headless browser context, не в личном
Chrome владельца. Локальные незакоммиченные mobile/landing/SignIn изменения не входят.

## Яндекс — установленное, не предположение

Обе production формы в чистых браузерных контекстах открыли OAuth:

- `/signup` и `/signin` → один и тот же `client_id`;
- origin `https://oauth.yandex.ru`;
- redirect `https://admirra.ru/auth/yandex/callback`;
- scope `login:email login:info`.

Обе кнопки используют `useOAuthLogin.startYandexLogin`; callback общий.
В шестичасовом доступном ingress-log до browser probe: два authorize HTTP200,
один callback HTTP200; отказавшего Yandex callback не обнаружено. В проверенных
логах обоих production API нет SQLAlchemy/psycopg2 или основных Python runtime
exceptions. Это НЕ доказательство успешной регистрации нового пользователя:
авторизация у провайдера/создание аккаунта в этом browser probe не выполнялись,
переход к провайдеру прерывался после фиксации параметров URL. OAuth state/code,
токены и credentials в отчёт не выводились.

Причина сообщения владельца пока не воспроизведена. Запрошен точный этап и текст
ошибки/скрин. До получения воспроизведения код авторизации и настройки приложения
Яндекса не менялись; не выдавать проверку одинаковых ссылок за исправление бага.

## Деплой

Только пять static document assets поверх pinned действующего frontend image,
без rebuild SPA/лендинга, без изменений API, workers, ingress, схемы и env.
`ops/Dockerfile.legal-branding`; rollback — прежний frontend image/config.
Выложено: source `cca1ca7`, image
`sha256:de7359bb6a79f4b3c729195f4a5dd3ce7c460a1a725fcf20da07fa00e7ec4701`.
Root-only release: `/etc/admirra/releases/legal-brand-cca1ca7/`;
`frontend-active.json`, `frontend-previous.json`, `acceptance.json`.
Публичные пять файлов побайтно совпали с source. Checksums SPA index, landing
index и active nginx config не изменились; env/mounts/ports сохранены.
Container IDs backend/DB/остановленной legacy automation прежние, API ready.
Workers и upstream balance 1:1 не трогались.
Повторный browser smoke непосредственно `https://admirra.ru`: 3 документа ×
5 размеров экрана прошли, оба лого загружены, переполнения нет, мобильное меню
и закрытие работают. Технический локальный preview остановлен после проверки.
