# Мобильный график и подсказка — 25.09.2026

Источник `246fb0c`, pushed; frontend-only release.

Причина: tooltip был `position: fixed` с viewport-координатами, скрывался
только при уходе мыши. Touch сохранял активную точку, прокрутка вложенного
MainLayout её не сбрасывала. Кроме того, mobile SVG наследовал desktop
aspect-ratio 880/300; ResizeObserver подключался только при первоначальном mount.

Исправления:
- График получает по 8 px дополнительной ширины внутри карточки; заголовки
  и controls сохраняют отступы. Mobile SVG/area используют intrinsic aspect ratio.
- Наблюдатель ширины переподключается при появлении SVG после смены вкладки.
- Подсказка absolute внутри chart-area, позиция ограничена реальными размерами
  подсказки и графика. Координаты точки получены через SVG getScreenCTM.
- Закрытие: scroll с capture (включая вложенный MainLayout), wheel, outside
  pointerdown, Escape, touch move/cancel, resize/visual viewport, скрытие вкладки,
  смена серии. Touchmove не открывает её повторно во время жеста прокрутки.
- Наблюдатели/обработчики удаляются при unmount. Данные/API/расчёты не меняются.

Проверки: 36 Node regression tests; browser fixture с production composable,
hover handler и dashboard CSS, 30 позиций в двух режимах на ширинах
320/375/390/430/1200; вложенный скролл, внешнее нажатие, touch cancel/move,
resize, unmount. Нет JS errors/overflow; содержимое тестовых подсказок не
обрезается. Скриншот mobile просмотрен. Browser fixture изолирован через
WW_TEST=1, localhost-only, без production credentials/API. Production build OK.

Сборка из clean git archive, старые dirty MainLayout/SignIn/landing не включены.
Overlay сохраняет лендинг/документы/старые chunks. Deploy helper подтвердил
неизменность env/mounts/ports/Nginx/public docs и API/DB/automation IDs.

Production:
- Image `sha256:a44f903be1360379ac545a42821f71a3cd3db6e43cc3c0619617c763c4908052`.
- Entry `/assets/index-Dw1pK8p7.js`.
- Build/deployer `/opt/admirra-chart-246fb0c`, API1.
- Active/previous/acceptance `/etc/admirra/releases/frontend-readiness-246fb0c/`.
- Public index verified; API ready. Workers/API2/host Nginx unchanged.

Откат frontend (сначала сверить текущий image):

```sh
docker compose -p admirra \
  -f /etc/admirra/releases/frontend-readiness-246fb0c/frontend-previous.json \
  up -d --no-deps --no-build --pull never frontend
```
