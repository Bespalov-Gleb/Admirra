# TraficAgent - Платформа аналитики рекламных кампаний

SaaS-платформа для управления и анализа рекламных кампаний с поддержкой интеграций Яндекс.Директ, VK Ads и Яндекс.Метрика.

## 📋 Содержание

- [Описание](#описание)
- [Возможности](#возможности)
- [Технологический стек](#технологический-стек)
- [Быстрый старт](#быстрый-старт)
- [Установка и настройка](#установка-и-настройка)
- [Структура проекта](#структура-проекта)
- [API документация](#api-документация)
- [Разработка](#разработка)
- [Деплой](#деплой)
- [Поддержка](#поддержка)

## 🎯 Описание

TraficAgent — это комплексная платформа для управления рекламными кампаниями и валидации лидов, которая позволяет:

- Подключать несколько рекламных аккаунтов через OAuth 2.0
- Автоматически синхронизировать статистику кампаний
- Анализировать эффективность рекламы в едином интерфейсе
- Отслеживать конверсии и цели из Яндекс.Метрики
- Генерировать отчеты и дашборды
- **Валидировать входящие лиды** с многоуровневой системой проверок
- Отсеивать до 90% мусорных заявок автоматически
- Отслеживать источники некачественного трафика

## ✨ Возможности

### Интеграции
- ✅ **Яндекс.Директ** — полная поддержка API v5, включая агентский режим
- ✅ **VK Ads** — управление рекламными кампаниями ВКонтакте
- ✅ **Яндекс.Метрика** — отслеживание целей и конверсий
- ✅ **OAuth 2.0** — безопасная авторизация через официальные API

### Функционал
- 🔐 **Мультипользовательская система** с ролями (Admin, Manager)
- 📊 **Дашборды** с агрегированной статистикой по всем кампаниям
- 🔄 **Автоматическая синхронизация** данных по расписанию
- 📈 **Аналитика** показов, кликов, расходов, конверсий
- 🎯 **Управление целями** из Яндекс.Метрики
- 📋 **Проекты и клиенты** — организация работы с несколькими аккаунтами
- 🔍 **Фильтры и поиск** по кампаниям и проектам
- 📱 **Адаптивный интерфейс** на Vue.js

### Валидация лидов (Lead Validator)
- 🛡️ **Многоуровневая валидация** — 8 уровней проверок от антибот до аналитики
- 🤖 **Антибот-защита** — honeypot, JavaScript-токен, время заполнения, CAPTCHA
- 📞 **Валидация контактов** — проверка телефонов и email через DaData
- 🔄 **Дедупликация** — автоматическое обнаружение повторных заявок
- 🚫 **Спам-фильтры** — проверка через внешние API и чёрные списки
- 📊 **Аналитика источников** — отслеживание качества трафика по площадкам
- 🔔 **Автоматические оповещения** — алерты о плохих источниках в Telegram
- 📈 **Отчётность** — детальные отчёты по качеству трафика для подрядчиков

## 🛠 Технологический стек

### Backend
- **FastAPI** — современный веб-фреймворк для Python
- **PostgreSQL** — реляционная база данных
- **SQLAlchemy** — ORM для работы с БД
- **Alembic** — миграции базы данных
- **APScheduler** — планировщик задач для синхронизации
- **httpx** — асинхронный HTTP-клиент для API запросов
- **python-jose** — JWT токены для аутентификации

### Frontend
- **Vue.js 3** — прогрессивный JavaScript фреймворк
- **Tailwind CSS** — utility-first CSS фреймворк
- **Vite** — сборщик и dev-сервер
- **Vue Router** — маршрутизация
- **Axios** — HTTP-клиент

### Инфраструктура
- **Docker** и **Docker Compose** — контейнеризация
- **Nginx** — веб-сервер для фронтенда
- **PostgreSQL 15** — база данных

## 🚀 Быстрый старт

### Требования
- Docker и Docker Compose
- Git

### Запуск проекта

```bash
# Клонировать репозиторий
git clone <repository-url>
cd trafic_agent

# Скопировать .env.example в .env и заполнить необходимые переменные
cp .env.example .env
# Отредактируйте .env файл, добавив ваши токены (см. раздел "Настройка токенов")

# Запустить все сервисы
docker compose up -d

# Проверить статус
docker compose ps
```

После запуска:
- **Frontend**: http://localhost:8080
- **Backend API**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs

**Важно:** Перед первым запуском обязательно настройте минимально необходимые переменные окружения (см. раздел "Минимальные требования для запуска").

## 📦 Установка и настройка

### 1. Настройка переменных окружения

Скопируйте файл `.env.example` в `.env` и заполните все необходимые переменные:

```bash
cp .env.example .env
```

Откройте `.env` и заполните значения для вашего окружения. Подробные инструкции по получению токенов см. в разделе ниже.

### 2. Настройка OAuth приложений

#### Яндекс.Директ
1. Перейдите в [Яндекс.OAuth](https://oauth.yandex.ru/)
2. Создайте новое приложение
3. Укажите redirect URI: `https://yourdomain.com/auth/yandex/callback`
4. Включите права доступа:
   - `direct:api` — доступ к API Яндекс.Директ
   - `metrika:read` — чтение данных Метрики
5. Скопируйте `Client ID` и `Client Secret` в `.env`

#### VK Ads (Authorization Code Grant)
1. Перейдите в [VK Ads API](https://ads.vk.com/hq/settings/access) (требуется доступ к рекламному кабинету)
2. Создайте OAuth-клиент или используйте существующий
3. Укажите redirect URI: `https://yourdomain.com/auth/vk/callback` (должен быть зарегистрирован в настройках приложения)
4. Включите права доступа (scope):
   - `read_ads` — чтение статистики и рекламных кампаний
   - `read_payments` — чтение денежных транзакций и баланса
   - `create_ads` — создание и редактирование настроек РК, баннеров, аудиторий
5. Скопируйте `Client ID` и `Client Secret` в `.env`:
   ```
   VK_CLIENT_ID=your_client_id
   VK_CLIENT_SECRET=your_client_secret
   ```

**Важно:** 
- Доступ к схеме Authorization Code Grant предоставляется только проверенным приложениям по запросу
- Документация: https://ads.vk.com/doc/api/info/Авторизация%20в%20API#AuthorizationCodeGrant
- При обмене кода на токен `client_secret` не требуется (используется только `client_id`)

#### myTarget
1. Зарегистрируйтесь в [myTarget Sandbox](https://target-sandbox.my.com) (для тестирования)
2. Создайте приложение в кабинете песочницы
3. Укажите redirect URI: `https://yourdomain.com/auth/mytarget/callback`
4. Отправьте запрос на доступ к API Authorization Code Grant, указав:
   - Название приложения
   - Краткое описание функциональности
   - Домен приложения
   - redirect_uri
   - Контактные данные ответственного лица (имя, email, телефон)
5. После получения доступа скопируйте `Client ID` и `Client Secret` в `.env`
6. Для боевого окружения используйте `https://target.my.com` или `https://target.vk.ru`

**Важно:** Приложение должно уметь получать токен для пользователя myTarget по схеме Authorization Code Grant. После тестирования в песочнице можно запросить доступ к боевому API.

### 3. Настройка токенов для валидации лидов

#### DaData API (обязательно)
DaData используется для валидации телефонов и email адресов.

1. Зарегистрируйтесь на [dadata.ru](https://dadata.ru/)
2. Перейдите в раздел [API ключи](https://dadata.ru/profile/#info)
3. Скопируйте `API ключ` и `Секретный ключ` в `.env`:
   ```
   DADATA_API_KEY=your_api_key
   DADATA_SECRET_KEY=your_secret_key
   ```

#### Telegram Bot (для уведомлений)
1. Создайте бота через [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте команду `/newbot` и следуйте инструкциям
3. Скопируйте токен бота в `.env`:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token
   ```
4. Получите Chat ID:
   - Напишите боту любое сообщение
   - Откройте в браузере: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Найдите `chat.id` в ответе
   - Скопируйте в `.env`:
     ```
     TELEGRAM_CHAT_ID=your_chat_id
     ```

#### Yandex SmartCaptcha (опционально)
1. Перейдите в [Yandex Cloud Console](https://console.cloud.yandex.ru/)
2. Создайте капчу в разделе "SmartCaptcha"
3. Получите `Client Key` и `Server Key`
4. Скопируйте в `.env`:
   ```
   SMARTCAPTCHA_CLIENT_KEY=your_client_key
   SMARTCAPTCHA_SERVER_KEY=your_server_key
   SMARTCAPTCHA_ENABLED=true
   ```

#### VK API Token (для проверки соцсетей, опционально)
**Важно:** метод `users.search` доступен только с **пользовательским OAuth-токеном**. Сервисный ключ даёт ошибку 1051.
1. Перейдите на [dev.vk.com](https://dev.vk.com/)
2. Создайте приложение (тип: Standalone)
3. Получите **пользовательский OAuth-токен**:
   - Откройте в браузере: `https://oauth.vk.com/authorize?client_id=ВАШ_APP_ID&scope=offline&redirect_uri=https://oauth.vk.com/blank.html&response_type=token`
   - Подставьте ваш Application ID из настроек приложения
   - Войдите в VK и разрешите доступ
   - После редиректа скопируйте `access_token` из URL (параметр после `#access_token=`)
4. Скопируйте в `.env`:
   ```
   VK_API_TOKEN=your_vk_user_oauth_token
   ```

#### SpravPortal WhoCalls API (опционально, платно)
1. Зарегистрируйтесь на [spravportal.ru](https://spravportal.ru/)
2. Получите API ключ в личном кабинете
3. Скопируйте в `.env`:
   ```
   SPRAVPORTAL_API_KEY=your_api_key
   ```

#### Kaspersky Who Calls API (опционально, платно)
1. Зарегистрируйтесь на [who-calls.ru](https://who-calls.ru/)
2. Получите API ключ в личном кабинете
3. Скопируйте в `.env`:
   ```
   KASPERSKY_API_KEY=your_api_key
   ```

#### Bitrix24 Webhook (опционально)
1. Войдите в ваш Bitrix24 портал
2. Перейдите в раздел "Приложения" → "Входящий вебхук"
3. Создайте новый вебхук с правами:
   - `crm` — доступ к CRM
   - `crm.contact` — работа с контактами
   - `crm.deal` — работа со сделками
4. Скопируйте URL вебхука в `.env`:
   ```
   BITRIX24_WEBHOOK_URL=https://your-portal.bitrix24.ru/rest/1/webhook_code/
   ```

#### Airtable (опционально, для логирования отклонённых заявок)
1. Создайте базу в [Airtable](https://airtable.com/)
2. Создайте таблицу `rejected_leads` с полями:
   - Phone, Email, Name, Rejection Reason, UTM Source, UTM Campaign, UTM Content, Client IP, Created At
3. Получите API ключ: [Account → API](https://airtable.com/api)
4. Получите Base ID из URL базы: `https://airtable.com/appXXXXXXXXXXXXXX`
5. Скопируйте в `.env`:
   ```
   AIRTABLE_API_KEY=your_api_key
   AIRTABLE_BASE_ID=your_base_id
   AIRTABLE_TABLE_NAME=rejected_leads
   ```

#### Яндекс.Метрика (опционально, для офлайн-конверсий)
1. Получите OAuth токен через [Яндекс.OAuth](https://oauth.yandex.ru/)
2. Получите ID счётчика из URL: `https://metrika.yandex.ru/dashboard?id=XXXXXX`
3. Скопируйте в `.env`:
   ```
   METRICA_COUNTER_ID=your_counter_id
   METRICA_OAUTH_TOKEN=your_oauth_token
   METRICA_ENABLED=true
   ```

### 4. Инициализация базы данных

База данных инициализируется автоматически при первом запуске. Если нужно применить миграции вручную:

```bash
docker compose exec backend alembic upgrade head
```

### 5. Создание первого пользователя

```bash
# Войти в контейнер backend
docker compose exec backend python

# В Python консоли:
from core.database import SessionLocal
from core.models import User, UserRole
from core.security import get_password_hash

db = SessionLocal()
user = User(
    email="admin@example.com",
    username="admin",
    password_hash=get_password_hash("your_password"),
    role=UserRole.ADMIN
)
db.add(user)
db.commit()
```

## 📋 Минимальные требования для запуска

### Для базовой работы системы валидации лидов

**Обязательно:**
- ✅ `DADATA_API_KEY` и `DADATA_SECRET_KEY` — для валидации телефонов и email
- ✅ `REDIS_ENABLED=true` и `REDIS_URL` — для дедупликации и rate limiting

**Рекомендуется:**
- ✅ `TELEGRAM_BOT_TOKEN` и `TELEGRAM_CHAT_ID` — для уведомлений о новых лидах
- ✅ `SMARTCAPTCHA_CLIENT_KEY` и `SMARTCAPTCHA_SERVER_KEY` — для защиты от ботов

**Опционально:**
- `VK_API_TOKEN` — проверка соцсетей (бесплатно, но ограниченно)
- `GETCONTACT_API_KEY` и `GETCONTACT_API_URL` — внешний провайдер GetContact
- `NUMBUSTER_API_KEY` и `NUMBUSTER_API_URL` — внешний провайдер NumBuster
- `SPRAVPORTAL_API_KEY` или `KASPERSKY_API_KEY` — проверка спам-номеров (платно)
- `BITRIX24_WEBHOOK_URL` — интеграция с CRM для поиска дубликатов
- `AIRTABLE_API_KEY` и `AIRTABLE_BASE_ID` — логирование отклонённых заявок
- `GETCONTACT_API_KEY` или `NUMBUSTER_API_KEY` — расширенная проверка соцсетей (платно)
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` — email-выгрузка заявок и **письма аутентификации** (подтверждение регистрации, код входа). При необходимости: `SMTP_USE_TLS`.
- `FRONTEND_URL` — публичный URL админ-панели (для ссылок в письмах, например `https://app.example.com`).
- `AUTH_RESEND_COOLDOWN_SEC` — минимальный интервал между повторными письмами подтверждения (по умолчанию 60).

**Миграция БД (Docker / ручной SQL):** при включении подтверждения email выполните скрипт `scripts/docker_two_factor_auth.sql` (колонки `users`, таблица `login_otp_challenges`, однократный `UPDATE` для существующих пользователей).

### Для работы с рекламными платформами

**Обязательно для каждой платформы:**
- Яндекс.Директ: `YANDEX_CLIENT_ID` и `YANDEX_CLIENT_SECRET`
- VK Ads: `VK_CLIENT_ID` и `VK_CLIENT_SECRET`
- myTarget: `MYTARGET_CLIENT_ID` и `MYTARGET_CLIENT_SECRET`

## 📁 Структура проекта

```
trafic_agent/
├── backend_api/          # FastAPI приложение
│   ├── main.py           # Точка входа, настройка приложения
│   ├── auth.py           # Аутентификация и авторизация
│   ├── integrations.py  # Управление интеграциями
│   ├── stats.py          # Статистика и аналитика
│   ├── clients.py        # Управление клиентами/проектами
│   └── campaigns.py      # Управление кампаниями
│
├── core/                 # Ядро приложения
│   ├── models.py         # SQLAlchemy модели
│   ├── schemas.py        # Pydantic схемы
│   ├── database.py       # Настройка БД
│   └── security.py       # Безопасность, шифрование токенов
│
├── automation/           # Автоматизация и синхронизация
│   ├── sync.py          # Основная логика синхронизации
│   ├── yandex_direct.py # API клиент Яндекс.Директ
│   ├── vk_ads.py        # API клиент VK Ads
│   ├── yandex_metrica.py # API клиент Яндекс.Метрика
│   ├── mytarget.py      # API клиент myTarget
│   └── reports.py        # Генерация отчетов
│
├── lead_validator/       # Модуль валидации лидов
│   ├── config.py         # Конфигурация и настройки
│   ├── router.py         # API endpoints
│   ├── schemas.py        # Pydantic схемы
│   ├── validators.py     # Основная логика валидации
│   ├── webhook_router.py # Webhook endpoints (Tilda, Marquiz)
│   ├── services/         # Сервисы валидации
│   │   ├── dadata.py     # Валидация телефонов/email
│   │   ├── redis_service.py # Дедупликация и rate limiting
│   │   ├── telegram.py   # Уведомления в Telegram
│   │   ├── spam_checker.py # Проверка спам-номеров
│   │   ├── bitrix_service.py # Интеграция с Bitrix24
│   │   ├── social_checker.py # Проверка соцсетей
│   │   ├── utm_validator.py # Валидация UTM-меток
│   │   └── ...
│   └── tasks/            # Scheduled tasks
│       └── alert_scheduler.py # Автоматические оповещения
│
├── admin-panel-vue-main/ # Frontend приложение
│   └── admin-panel-vue-main/
│       ├── src/
│       │   ├── views/    # Страницы приложения
│       │   ├── components/ # Vue компоненты
│       │   ├── composables/ # Vue composables
│       │   ├── router/    # Маршрутизация
│       │   └── api/       # API клиент
│       └── package.json
│
├── alembic/             # Миграции БД
│   └── versions/
│
├── tests/                # Тесты
│   ├── test_sync.py
│   └── test_yandex_direct.py
│
├── docker-compose.yml    # Docker Compose конфигурация
├── Dockerfile           # Backend Dockerfile
├── requirements.txt     # Python зависимости
└── README.md            # Этот файл
```

## 📚 API документация

### Базовый URL
```
http://localhost:8001/api
```

### Основные эндпоинты

#### Аутентификация
- `POST /api/auth/register` — регистрация пользователя
- `POST /api/auth/login` — вход в систему
- `GET /api/auth/me` — текущий пользователь

#### Интеграции
- `POST /api/integrations/` — создать интеграцию
- `GET /api/integrations/` — список интеграций
- `GET /api/integrations/{id}` — детали интеграции
- `PATCH /api/integrations/{id}` — обновить интеграцию
- `POST /api/integrations/{id}/discover-campaigns` — обнаружить кампании
- `GET /api/integrations/{id}/profiles` — список профилей (для Яндекс.Директ)
- `GET /api/integrations/{id}/goals` — список целей Метрики
- `GET /api/integrations/{id}/campaigns-stats` — статистика кампаний

#### Статистика
- `GET /api/stats/dashboard` — дашборд с агрегированной статистикой
- `GET /api/stats/campaigns` — статистика по кампаниям

#### Клиенты/Проекты
- `GET /api/clients/` — список клиентов/проектов
- `POST /api/clients/` — создать клиента/проект

#### Валидация лидов
- `POST /api/lead/` — принять и валидировать лид
- `GET /api/lead/check-phone` — ручная проверка телефона
- `GET /api/reports/quality` — отчёт по качеству трафика
- `GET /api/reports/blacklist` — список площадок в чёрном списке

Полная документация доступна по адресу: **http://localhost:8001/docs** (Swagger UI)

### Документация по валидации лидов

- [PHONE_SETUP_CHECKLIST.md](PHONE_SETUP_CHECKLIST.md) — чеклист настройки модуля валидации
- [SOCIAL_CHECKER_DOCS.md](SOCIAL_CHECKER_DOCS.md) — документация по проверке соцсетей
- [TZ_ANALYSIS_AND_PLAN.md](TZ_ANALYSIS_AND_PLAN.md) — анализ ТЗ и план реализации

## 💻 Разработка

### Локальная разработка (без Docker)

#### Backend
```bash
# Установить зависимости
pip install -r requirements.txt

# Настроить переменные окружения
export DATABASE_URL="postgresql://postgres:password@localhost:5432/saas_project"
export YANDEX_CLIENT_ID="your_id"
export YANDEX_CLIENT_SECRET="your_secret"

# Запустить сервер
uvicorn backend_api.main:app --reload --port 8001
```

#### Frontend
```bash
cd admin-panel-vue-main/admin-panel-vue-main

# Установить зависимости
npm install

# Запустить dev-сервер
npm run dev
```

### Запуск тестов
```bash
# Backend тесты
docker compose exec backend pytest

# Или локально
pytest tests/
```

### Миграции БД
```bash
# Создать новую миграцию
docker compose exec backend alembic revision --autogenerate -m "description"

# Применить миграции
docker compose exec backend alembic upgrade head

# Откатить миграцию
docker compose exec backend alembic downgrade -1
```

### Полное пересоздание базы данных

Для полного пересоздания БД (удаление всех данных и создание новой БД со схемой из моделей SQLAlchemy):

#### Способ 1: Выполнение команды напрямую (рекомендуется)

**В Docker:**
```bash
# Python скрипт (рекомендуется)
docker compose exec backend python recreate_db.py

# Или bash скрипт
docker compose exec backend bash recreate_db.sh
```

#### Способ 2: Вход в контейнер и выполнение внутри

**Шаг 1: Зайти в контейнер backend**
```bash
docker compose exec backend bash
```

После выполнения этой команды вы окажетесь внутри контейнера (приглашение изменится на что-то вроде `root@container_id:/app#`).

**Шаг 2: Выполнить скрипт внутри контейнера**
```bash
# Перейти в директорию проекта (если нужно)
cd /app

# Выполнить Python скрипт
python recreate_db.py

# Или bash скрипт
bash recreate_db.sh
```

**Шаг 3: Выйти из контейнера**
```bash
exit
```

#### Способ 3: Локально (без Docker)

**Требования:**
- PostgreSQL должен быть запущен локально
- Python 3.8+ установлен
- SQLAlchemy установлен (обычно уже есть в зависимостях)

```bash
# Убедитесь, что DATABASE_URL установлен в .env или переменных окружения
python recreate_db.py

# Или
bash recreate_db.sh
```

#### Проверка статуса контейнеров

Перед выполнением скрипта убедитесь, что контейнеры запущены:
```bash
# Проверить статус всех контейнеров
docker compose ps

# Если контейнеры не запущены, запустите их
docker compose up -d

# Проверить логи backend контейнера
docker compose logs backend
```

#### Пример полного процесса

```bash
# 1. Проверить, что контейнеры запущены
docker compose ps

# 2. Выполнить скрипт пересоздания БД
docker compose exec backend python recreate_db.py

# Ожидаемый вывод:
# ============================================================
# 🔄 Пересоздание базы данных
# ============================================================
# 
# 📊 База данных: saas_project
# 🔗 URL подключения: postgresql://postgres@***
# 
# ✅ Подключение к PostgreSQL установлено
# 
# 🗑️  Удаление базы данных 'saas_project'...
# ✅ База данных 'saas_project' успешно удалена
# 
# 🆕 Создание базы данных 'saas_project'...
# ✅ База данных 'saas_project' успешно создана
# 
# 🧹 Очистка остатков типов ENUM...
# ✅ Очистка завершена
# 
# 📦 Создание схемы БД из моделей SQLAlchemy...
# ✅ Схема БД успешно создана из моделей
#    Все таблицы, индексы и типы ENUM созданы
# 
# ============================================================
# ✅ База данных успешно пересоздана!
# ============================================================
```

#### Устранение проблем

**Ошибка: "container is not running"**
```bash
# Запустить контейнеры
docker compose up -d

# Подождать несколько секунд, пока контейнеры запустятся
sleep 5

# Повторить команду
docker compose exec backend python recreate_db.py
```

**Ошибка: "DATABASE_URL не установлен"**
```bash
# Проверить переменные окружения в контейнере
docker compose exec backend env | grep DATABASE_URL

# Если переменная не установлена, проверьте .env файл
cat .env | grep DATABASE_URL
```

**Ошибка: "Multiple head revisions" (старая версия скрипта)**
```bash
# Новый скрипт не использует Alembic, поэтому эта ошибка больше не возникает
# Если используете старую версию, обновите скрипт или выполните:
# docker compose exec backend alembic upgrade heads
```

**Ошибка: "ImportError: cannot import name 'Base'"**
```bash
# Убедитесь, что вы находитесь в правильной директории
# В контейнере: cd /app
docker compose exec backend pip install alembic
```

**Ошибка: "Multiple head revisions are present" (при использовании Alembic вручную)**
Эта ошибка возникает, когда в проекте есть несколько веток миграций. Скрипт автоматически определяет это и применяет все heads. Если автоматическое определение не сработало:

```bash
# Применить все head-ревизии
docker compose exec backend alembic upgrade heads

# Или объединить миграции в одну ветку (рекомендуется для долгосрочного решения)
docker compose exec backend alembic merge -m "merge heads" heads
docker compose exec backend alembic upgrade head
```

**⚠️ Внимание:** Скрипт полностью удаляет все данные из базы данных! Используйте только для разработки и тестирования. Перед использованием в production обязательно сделайте резервную копию.

### Логи
```bash
# Логи всех сервисов
docker compose logs -f

# Логи конкретного сервиса
docker compose logs -f backend
docker compose logs -f db
```

## 🚢 Деплой

### Production деплой

1. **Обновить переменные окружения** в `docker-compose.yml`:
   - Использовать сильные пароли для БД
   - Указать production OAuth credentials
   - Настроить CORS для вашего домена

2. **Собрать и запустить**:
```bash
docker compose build --no-cache
docker compose up -d
```

3. **Деплой фронтенда** (если используется системный Nginx):
```bash
./deploy-frontend.sh
```

### Обновление приложения
```bash
# Остановить контейнеры
docker compose down

# Обновить код
git pull

# Пересобрать и запустить
docker compose build
docker compose up -d

# Применить миграции (если есть)
docker compose exec backend alembic upgrade head
```

### Бэкапы базы данных
```bash
# Создать бэкап
docker compose exec db pg_dump -U postgres saas_project > backup.sql

# Восстановить из бэкапа
docker compose exec -T db psql -U postgres saas_project < backup.sql
```

## 🔒 Безопасность

- ✅ Токены OAuth шифруются перед сохранением в БД
- ✅ Пароли хешируются с использованием bcrypt
- ✅ JWT токены для аутентификации API
- ✅ PostgreSQL порт закрыт для внешнего доступа
- ✅ CORS настроен для защиты от CSRF
- ✅ Валидация всех входных данных через Pydantic

## 🐛 Решение проблем

### База данных не подключается
```bash
# Проверить статус БД
docker compose ps db

# Проверить логи
docker compose logs db

# Пересоздать БД (⚠️ удалит все данные)
docker compose down -v
docker compose up -d
```

### Ошибки OAuth
- Убедитесь, что redirect URI точно совпадает с настройками в OAuth приложении
- Проверьте, что все необходимые права доступа включены
- Для Яндекс: приложение должно быть опубликовано или добавлены тестовые пользователи

### Проблемы с синхронизацией
- Проверьте логи: `docker compose logs backend | grep sync`
- Убедитесь, что токены не истекли
- Проверьте доступность API рекламных платформ

## 📝 Лицензия

[Указать лицензию]

## 👥 Авторы

[Указать авторов]

## 📞 Поддержка

Для вопросов и поддержки:
- Создайте Issue в репозитории
- Email: [указать email]

---

**Версия**: 1.0.0  
**Последнее обновление**: 2026-01-18
