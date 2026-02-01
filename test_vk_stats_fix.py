"""
Тестовый скрипт для проверки исправлений VK Ads API интеграции:
- Проверка получения conversions (vk.goals)
- Проверка расчета CPC (средняя цена клика)
- Проверка расчета CPA (средняя цена цели)
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trafic_agent.automation.vk_ads import VKAdsAPI
from datetime import datetime, timedelta

async def test_vk_api_structure():
    """Тестирует структуру ответа VK API и парсинг метрик"""
    
    # Пример ответа VK API из файла vk_response_example.json
    sample_response = {
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
    
    print("=" * 80)
    print("ТЕСТ ПАРСИНГА СТРУКТУРЫ VK API")
    print("=" * 80)
    
    # Создаем тестовый экземпляр API (без токена для теста парсинга)
    api = VKAdsAPI("test_token", "test_account")
    
    # Создаем моковый names_map
    names_map = {12345: "Тестовая кампания"}
    
    # Парсим ответ
    results = api._parse_response(sample_response, names_map)
    
    print(f"\n✅ Parsed {len(results)} row(s):\n")
    for result in results:
        print(f"📊 Date: {result['date']}")
        print(f"   Campaign: {result['campaign_name']} (ID: {result['campaign_id']})")
        print(f"   Impressions: {result['impressions']}")
        print(f"   Clicks: {result['clicks']}")
        print(f"   Cost: {result['cost']} RUB")
        print(f"   Conversions (Лиды/Результат): {result['conversions']}")
        print(f"   CPC (Средняя цена клика): {result['cpc']} RUB")
        print(f"   CPA (Средняя цена цели): {result['cpa']} RUB")
        print()
    
    # Проверяем корректность данных
    assert len(results) == 1, "Должна быть одна строка результата"
    assert results[0]['conversions'] == 10, f"Conversions должны быть 10, получено: {results[0]['conversions']}"
    assert results[0]['cpc'] == 30.01, f"CPC должен быть 30.01, получено: {results[0]['cpc']}"
    assert results[0]['cpa'] == 150.05, f"CPA должен быть 150.05, получено: {results[0]['cpa']}"
    
    print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО!")
    print("=" * 80)

async def test_vk_api_with_zero_values():
    """Тестирует расчет CPC и CPA когда API возвращает нулевые значения"""
    
    # Пример ответа с нулевыми CPC и CPA (требуется расчет)
    sample_response = {
        "items": [
            {
                "id": 67890,
                "rows": [
                    {
                        "date": "2026-02-01",
                        "base": {
                            "shows": 2000,
                            "clicks": 100,
                            "spent": "2500.00",
                            "cpc": "0",  # Нулевое значение - должно быть рассчитано
                            "vk": {
                                "goals": 25,
                                "cpa": "0",  # Нулевое значение - должно быть рассчитано
                                "cr": 25.0
                            }
                        }
                    }
                ]
            }
        ]
    }
    
    print("\n" + "=" * 80)
    print("ТЕСТ РАСЧЕТА CPC И CPA ПРИ НУЛЕВЫХ ЗНАЧЕНИЯХ ОТ API")
    print("=" * 80)
    
    # Создаем тестовый экземпляр API
    api = VKAdsAPI("test_token", "test_account")
    names_map = {67890: "Кампания с нулевыми метриками"}
    
    # Парсим ответ
    results = api._parse_response(sample_response, names_map)
    
    print(f"\n✅ Parsed {len(results)} row(s):\n")
    for result in results:
        print(f"📊 Date: {result['date']}")
        print(f"   Campaign: {result['campaign_name']} (ID: {result['campaign_id']})")
        print(f"   Impressions: {result['impressions']}")
        print(f"   Clicks: {result['clicks']}")
        print(f"   Cost: {result['cost']} RUB")
        print(f"   Conversions (Лиды/Результат): {result['conversions']}")
        print(f"   CPC (рассчитано): {result['cpc']} RUB (expected: {2500/100} = 25.00)")
        print(f"   CPA (рассчитано): {result['cpa']} RUB (expected: {2500/25} = 100.00)")
        print()
    
    # Проверяем корректность расчетов
    expected_cpc = 2500.00 / 100  # cost / clicks = 25.00
    expected_cpa = 2500.00 / 25   # cost / conversions = 100.00
    
    assert len(results) == 1, "Должна быть одна строка результата"
    assert results[0]['conversions'] == 25, f"Conversions должны быть 25, получено: {results[0]['conversions']}"
    assert results[0]['cpc'] == expected_cpc, f"CPC должен быть {expected_cpc}, получено: {results[0]['cpc']}"
    assert results[0]['cpa'] == expected_cpa, f"CPA должен быть {expected_cpa}, получено: {results[0]['cpa']}"
    
    print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО!")
    print("=" * 80)

async def test_vk_api_with_no_conversions():
    """Тестирует обработку случая когда conversions = 0"""
    
    sample_response = {
        "items": [
            {
                "id": 11111,
                "rows": [
                    {
                        "date": "2026-02-01",
                        "base": {
                            "shows": 500,
                            "clicks": 20,
                            "spent": "300.00",
                            "cpc": "15.00",
                            "vk": {
                                "goals": 0,  # Нет конверсий
                                "cpa": "0",
                                "cr": 0.0
                            }
                        }
                    }
                ]
            }
        ]
    }
    
    print("\n" + "=" * 80)
    print("ТЕСТ ОБРАБОТКИ НУЛЕВЫХ КОНВЕРСИЙ")
    print("=" * 80)
    
    api = VKAdsAPI("test_token", "test_account")
    names_map = {11111: "Кампания без конверсий"}
    
    results = api._parse_response(sample_response, names_map)
    
    print(f"\n✅ Parsed {len(results)} row(s):\n")
    for result in results:
        print(f"📊 Date: {result['date']}")
        print(f"   Campaign: {result['campaign_name']} (ID: {result['campaign_id']})")
        print(f"   Conversions (Лиды/Результат): {result['conversions']}")
        print(f"   CPC: {result['cpc']} RUB")
        print(f"   CPA: {result['cpa']} RUB (должен быть 0.0 при нулевых конверсиях)")
        print()
    
    # Проверяем корректность
    assert results[0]['conversions'] == 0, "Conversions должны быть 0"
    assert results[0]['cpc'] == 15.00, f"CPC должен быть 15.00, получено: {results[0]['cpc']}"
    assert results[0]['cpa'] == 0.0, f"CPA должен быть 0.0 при conversions=0, получено: {results[0]['cpa']}"
    
    print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО!")
    print("=" * 80)

async def main():
    """Главная функция для запуска всех тестов"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЙ VK ADS API" + " " * 23 + "║")
    print("╚" + "=" * 78 + "╝")
    print()
    
    try:
        # Тест 1: Парсинг структуры API
        await test_vk_api_structure()
        
        # Тест 2: Расчет при нулевых значениях
        await test_vk_api_with_zero_values()
        
        # Тест 3: Обработка нулевых конверсий
        await test_vk_api_with_no_conversions()
        
        print("\n" + "=" * 80)
        print("🎉 ВСЕ ТЕСТЫ УСПЕШНО ПРОЙДЕНЫ!")
        print("=" * 80)
        print()
        print("Следующие шаги:")
        print("1. Запустить миграцию БД: python -m alembic upgrade head")
        print("2. Запустить синхронизацию VK кампаний: python -m automation.sync 7")
        print("3. Проверить дашборд - метрики Лиды, CPC и CPA должны отображаться")
        print()
        
    except AssertionError as e:
        print(f"\n❌ ТЕСТ ПРОВАЛЕН: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

