# Сводка изменений: Avito Ads, Метрика, Яндекс Директ

Кратко для деплоя и ревью. Ветка с этими правками — `metrics-fallback-fix`.

---

## Зачем

1. **Avito Ads** — подключение, синк РК и статистики, дашборд с фильтром `platform=avito`.
2. **Лиды Avito** — из Метрики (в API Avito лидов нет).
3. **Яндекс Директ** — в визарде список кабинетов по официальным методам API.

---

## База данных

Файл: `sql/avito_ads_integration.sql`

- Enum `integrationplatform`: значение `AVITO_ADS`
- Таблица `avito_stats` (аналог `yandex_stats` / `vk_stats`)

**Миграции Alembic на сервере не гонять.** Применить SQL:

```bash
cd trafic_agent
docker compose exec db psql -U postgres -d saas_project -f - < sql/avito_ads_integration.sql
```

---

## Backend: Avito

| Файл | Суть |
|------|------|
| `automation/avito_ads.py` | Клиент API: token, balance, campaigns, stats |
| `automation/avito_integration_helpers.py` | Metrika-интеграция клиента, `metrika_profile_login()` |
| `automation/sync.py` | Ветка `AVITO_ADS`: синк в `avito_stats`, затем цели Метрики |
| `backend_api/integrations.py` | `POST /integrations/avito/connect`, counters/goals через Metrika |
| `core/models.py` | `AvitoStats`, enum платформы |

**Авторизация Avito:** только `client_id` + `client_secret` (client_credentials).

---

## Backend: лиды Avito + Метрика

| Что | Как |
|-----|-----|
| Расход, показы, клики | `avito_stats` |
| Лиды, CPA (сводка) | `metrika_goals` того же `client_id` |
| Синк лидов после Avito | `_sync_metrika_goals_for_direct(..., direct_traffic_only=False)` |
| Дашборд `platform=avito` | `stats_service.py` / `stats.py` — лиды из MetrikaGoals |

**Не сделано:** лиды и CPA **по каждой РК Avito** в таблице кампаний.

---

## Backend: профили Яндекс Директ

`GET /integrations/{id}/profiles` — по [документации Директа](https://yandex.ru/dev/direct/doc/ru/):

| Источник | Метод API | Client-Login | Имя в UI |
|----------|-----------|--------------|----------|
| Личный кабинет | [Clients.get](https://yandex.ru/dev/direct/doc/ru/clients/get) | нет | `Organization.Name`, иначе `ClientInfo` (представитель) |
| Клиенты агентства | [AgencyClients.get](https://yandex.ru/dev/direct/doc/ru/agencyclients/get) | нет | `Organization.Name`, иначе `ClientInfo` (название клиента) |
| Делегированные кабинеты | `ManagedLogins` из Clients.get* | да, для каждого логина | `Organization.Name` через Clients.get |

\* `ManagedLogins` **не описан** в enum `FieldNames`, но API возвращает его — используем только как список логинов для `Client-Login`. Это **не** гарантированный аналог выпадающего списка «Выбрать организацию» в UI Директа.

**Важно по доке Clients.get:** при заголовке `Client-Login` поля `Login` и `ClientInfo` относятся к **представителю**, не к организации. Для названия кабинета запрашиваем `OrganizationFieldNames: ["Name"]`.

Типы в ответе API (`personal`, `agency_client`, `managed`) — **внутренние метки** приложения, не поля Яндекса.

Ручной ввод логина в визарде **не предусмотрен**.

`AccountManagement` используется только для **баланса** (Direct Pro), не для списка профилей.

---

## Frontend

| Область | Изменения |
|---------|-----------|
| `IntegrationWizard.vue` | Avito: connect, OAuth Метрики, шаги counters/goals |
| `IntegrationStep2.vue` | Подписи: Личный / Клиент агентства / Кабинет |
| Дашборд | Фильтр Avito: `GeneralStats3`, `useDashboardStats.js` |

---

## Деплой

```bash
git pull
docker compose up -d --build backend frontend
# SQL — если ещё не применяли (см. выше)
```
