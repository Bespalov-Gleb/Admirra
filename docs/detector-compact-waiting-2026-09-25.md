# Компактное ожидание детектора

> Обновление 26.09: штатные плашки теперь полностью скрыты, см. раздел ниже.
> Описание однострочного ожидания относится к предыдущей версии df33462.

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

## 26.09: убрать все штатные стадии подготовки

Пользователь повторно увидел initial/no-receipt и ready состояния: первая правка
касалась только waiting. Source **4ca12c8** скрывает весь слот через `v-show`,
когда это обычная проверка / waiting / ready, включая отступы. Poller остаётся
смонтирован и выполняет GET с прежним интервалом; ready обновляет summary один раз,
без кнопки «Обновить выводы детектора». Новый opt-in `quietRoutine` также убирает
внутреннюю ready-плашку. Generic consumers без этого prop не меняются.
Проектный key гарантирует отмену poller при переходе к другому проекту.

Held/poll_error остаются видимыми и дают ручной повтор. Warmup плана и настоящие
отклонения не меняются; скрытие служебного статуса не означает признание неполной
истории готовой и не обходит backend freshness guards.

Проверки: Chromium на реальных компонентах с синтетическим API (initial, waiting,
initial ready, waiting→ready, повтор receipt без цикла, no layout box,
error/retry, hidden tab, unmount, plan warmup, generic paid actions только по клику),
24 Node regression tests, clean build 962 modules. Desktop/mobile screenshots
просмотрены. Полный authenticated production E2E не запускался.

Выкатан frontend overlay `4ca12c8`, image
`sha256:5f81b9fd693f7b09e281bbd1f4275eaf1bf51598556d92fab9a0b53694149f6a`,
entry `/assets/index-7jLsuM6R.js`, dashboard `/assets/GeneralStats3-y0XSo1Ub.js`.
Snapshot `/etc/admirra/releases/frontend-readiness-4ca12c8/`, previous=14d1014.
Overlay подтвердил публичные assets/index и сохранность landing/legal/nginx,
API/DB/automation. API, worker, кеш настройки и БД не менялись.
