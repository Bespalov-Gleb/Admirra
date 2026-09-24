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
Фактический image/release и production smoke фиксируются после выкладки.
