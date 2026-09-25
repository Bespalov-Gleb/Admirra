# Компактное ожидание детектора

Подготовка истории теперь показывается одной нейтральной строкой
«Анализируем данные…», без рамки, uppercase и повторяющего пояснения.
DataReadinessNotice остаётся смонтирован: polling, остановка в скрытой вкладке,
отмена при unmount и refresh-data после ready сохранены. Скрыт только waiting
без ошибок, через opt-in quietWaiting; таблицы/прочие потребители не изменены.

Сбой polling становится видимым состоянием с кнопкой «Проверить статус»;
held/истечение ожидания сохраняют объяснение и разрешённую сервером кнопку
повтора. Ошибка одного источника приоритетнее ожидания другого. Warmup нового
плана и настоящие предупреждения/проблемы детектора не менялись. Ready не
приравнивается к «всё хорошо»: родитель повторно получает выводы детектора.

Проверки: 37 Node тестов, изолированный Chromium на настоящих компонентах
(ready→автообновление, дедупликация, hidden/unmount, polling error, held→retry,
generic consumer без автозапуска платного действия). Скриншоты desktop/mobile
390px/light/dark просмотрены, горизонтального overflow нет.

Выкладка только frontend overlay из clean archive; сохраняет предыдущую
правку AI-комментария, landing/legal и старые chunks. API, БД, воркеры и Nginx
не меняются. Чужие незакоммиченные MainLayout/SignIn/landing не включаются.

## Production

Выкатан source **df33462**, image
`sha256:881f3e40840b21265d2a17fedfe93c5cd61991744ea8760eba5bdc07e05dfbfc`.
Entry `/assets/index-SLyZg9ft.js`; публичный GeneralStats3-BN9cCC4a.js совпал
с clean build по SHA256. Overlay подтвердил неизменность landing/legal/Nginx,
API/DB/legacy automation. На 25.09.2026 13:39 UTC alerts=[], оба API ready=ok.
Previous/active compose и acceptance:
`/etc/admirra/releases/frontend-readiness-df33462/`, предыдущий source=64c45d9.
