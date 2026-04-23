# Vue 3 + Vite

This template should help get you started developing with Vue 3 in Vite. The template uses Vue 3 `<script setup>` SFCs, check out the [script setup docs](https://v3.vuejs.org/api/sfc-script-setup.html#sfc-script-setup) to learn more.

Learn more about IDE Support for Vue in the [Vue Docs Scaling up Guide](https://vuejs.org/guide/scaling-up/tooling.html#ide-support).

## Лендинг AdMirra (`/admirra/`)

Статика лежит **только** в `public/admirra/` (Vite копирует `public` в корень сборки). Страница `Landing.vue` открывает её через `<iframe src="/admirra/index.html">`. Обновляйте вёрстку **только** в этой папке; дубликаты в корне репозитория не используются.

После копирования новой вёрстки из внешней папки (например `Downloads\admirra (1)`) проверьте ссылки: вход и регистрация должны вести на **`/signin`** и **`/signup`** с атрибутом **`target="_top"`** (чтобы переход работал из iframe). Файлы `entry.html` и `reg.html` в проекте — редиректы на эти маршруты SPA.
