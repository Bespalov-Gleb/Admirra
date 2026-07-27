# AdMirra Internal Admin

Отдельное SPA для внутренней команды. Клиентский кабинет и его JWT не используются.

## Локальный запуск

```bash
npm install
npm run dev
```

Vite проксирует `/api` на `https://admirra.ru`. Для другого адреса:

```bash
VITE_API_PROXY=http://127.0.0.1:8001 npm run dev
```

## Production

Контейнер `admin_frontend` слушает только `127.0.0.1:8081`. Хостовый nginx должен
проксировать `admin.admirra.ru` на этот порт. SPA само проксирует `/api` в backend.

Первый Super Admin приглашается один раз:

```bash
docker compose run --rm backend python scripts/create_internal_superadmin.py \
  --email owner@example.com --first-name Имя --last-name Фамилия
```

Команда вернёт одноразовую ссылку сроком на 7 дней. Владелец открывает её на
`admin.admirra.ru`, сам задаёт пароль и при желании сразу подключает 2FA.

После первого входа остальных сотрудников следует добавлять через раздел
«Сотрудники» — они получают invite-ссылку и сами задают пароль.
