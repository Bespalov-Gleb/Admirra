# Исправление метрик VK Ads на дашборде

## Проблема
На дашборде следующие метрики из интеграции VK Ads отображались как нули:
- **Лиды** (должны отображать "Результат" из VK)
- **Средняя CPC** (средняя цена клика)
- **Средняя CPA** (средняя цена цели)

## Анализ

### Структура ответа VK Ads API

VK Ads API v2 возвращает статистику в следующей структуре:

```json
{
  "items": [
    {
      "id": 12345,
      "rows": [
        {
          "date": "2026-02-01",
          "base": {
            "shows": 1000,
            "clicks": 50,
            "spent": "1500.50",
            "cpc": "30.01",
            "vk": {
              "goals": 10,
              "cpa": "150.05",
              "cr": 20.0
            }
          }
        }
      ]
    }
  ]
}
```

### Обнаруженная ошибка

Код пытался получить данные как `base.get("vk.goals")` и `base.get("vk.cpa")`, но VK API возвращает **вложенную структуру**: `base["vk"]["goals"]` и `base["vk"]["cpa"]`.

## Решение

### 1. Исправлен парсинг ответа VK API (`trafic_agent/automation/vk_ads.py`)

**До:**
```python
vk_cpc = base.get("cpc")
vk_cpa = base.get("vk.cpa")  # ❌ Неправильно - ищет ключ "vk.cpa"
conversions_val = int(base.get("vk.goals", 0))  # ❌ Неправильно
```

**После:**
```python
vk_section = base.get("vk", {})  # ✅ Получаем вложенный объект "vk"
vk_cpc = base.get("cpc")
vk_cpa = vk_section.get("cpa")  # ✅ Правильно - base["vk"]["cpa"]
conversions_val = int(vk_section.get("goals", 0))  # ✅ Правильно - base["vk"]["goals"]
```

### 2. Добавлена обработка нулевых и отсутствующих значений

Если VK API возвращает `cpc=0` или `vk.cpa=0`, система автоматически рассчитывает эти метрики:

```python
# Расчет CPC если API вернул 0
if vk_cpc is None or vk_cpc == 0 or (isinstance(vk_cpc, str) and float(vk_cpc) == 0):
    clicks_val = int(base.get("clicks", 0))
    cost_val = float(base.get("spent", 0))
    vk_cpc = cost_val / clicks_val if clicks_val > 0 else 0.0

# Расчет CPA если API вернул 0
if vk_cpa is None or vk_cpa == 0 or (isinstance(vk_cpa, str) and float(vk_cpa) == 0):
    cost_val = float(base.get("spent", 0))
    vk_cpa = cost_val / conversions_val if conversions_val > 0 else 0.0
```

### 3. Добавлено логирование для отладки (`trafic_agent/automation/sync.py`)

Добавлены предупреждения, если данные отсутствуют:
```python
if s['conversions'] == 0:
    logger.warning(f"⚠️ VK campaign has 0 conversions - this may be expected if no goals were reached")
if s.get('cpc') == 0 or s.get('cpc') is None:
    logger.debug(f"🔍 VK campaign has CPC=0 or None")
if s.get('cpa') == 0 or s.get('cpa') is None:
    logger.debug(f"🔍 VK campaign has CPA=0 or None")
```

## Изменения в коде

### Измененные файлы:

1. **`trafic_agent/automation/vk_ads.py`**
   - Исправлен парсинг вложенной структуры VK API
   - Улучшена обработка нулевых значений CPC и CPA
   - Добавлена документация по структуре ответа API

2. **`trafic_agent/automation/sync.py`**
   - Добавлено логирование для отладки нулевых метрик

3. **`trafic_agent/alembic/versions/a1b2c3d4e5f7_add_cpc_cpa_to_vk_stats.py`**
   - Миграция уже существовала (добавляет поля `cpc` и `cpa` в таблицу `vk_stats`)

## Проверка

### База данных

Модель `VKStats` уже содержит необходимые поля:
```python
class VKStats(Base):
    __tablename__ = "vk_stats"
    # ...
    conversions = Column(BigInteger, default=0)  # vk.goals - Результат (лиды)
    cpc = Column(Numeric(20, 2), nullable=True)  # Средняя цена клика
    cpa = Column(Numeric(20, 2), nullable=True)  # vk.cpa - Средняя цена цели
```

### Сервис статистики

Сервис `StatsService` (`trafic_agent/backend_api/stats_service.py`) уже правильно агрегирует метрики:
- Использует взвешенное среднее для CPC и CPA
- Корректно суммирует conversions из `VKStats`

## Следующие шаги

### 1. Применить миграцию базы данных

```bash
cd trafic_agent
python -m alembic upgrade head
```

### 2. Запустить синхронизацию данных

```bash
# Синхронизировать данные за последние 7 дней
python -m automation.sync 7
```

### 3. Проверить дашборд

После синхронизации на дашборде должны отображаться:
- **Лиды** = количество целевых действий (vk.goals)
- **Ср. CPC** = средняя цена клика
- **Ср. CPA** = средняя цена цели

## Примечания

### Маппинг метрик

| Дашборд | VK API | Описание |
|---------|--------|----------|
| **Лиды** | `base.vk.goals` | Количество достижений целей (Результат) |
| **Ср. CPC** | `base.cpc` или `spent / clicks` | Средняя цена клика (eCPC) |
| **Ср. CPA** | `base.vk.cpa` или `spent / goals` | Средняя цена цели |
| **Расход** | `base.spent` | Общая потраченная сумма |
| **Клики** | `base.clicks` | Количество кликов |
| **Показы** | `base.shows` | Количество показов |

### Формулы расчета

Если VK API не возвращает метрику или возвращает 0, система рассчитывает её автоматически:

- **CPC** = `Расход / Клики`
- **CPA** = `Расход / Лиды (Результат)`
- **CTR** = `(Клики / Показы) * 100%`
- **CR** = `(Лиды / Клики) * 100%`

## Тестирование

Создан тестовый скрипт `test_vk_stats_fix.py` для проверки:
1. Парсинга вложенной структуры API
2. Расчета CPC/CPA при нулевых значениях
3. Обработки кампаний без конверсий

Запуск тестов:
```bash
python trafic_agent/test_vk_stats_fix.py
```

## Заключение

Исправление устраняет проблему с отображением метрик VK Ads на дашборде. Теперь система:
- ✅ Корректно извлекает данные из вложенной структуры VK API
- ✅ Автоматически рассчитывает CPC и CPA при необходимости
- ✅ Сохраняет все метрики в базу данных
- ✅ Отображает их на дашборде с правильными значениями

