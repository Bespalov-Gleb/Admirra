"""
Скрипт для проверки дубликатов в таблице vk_stats
Проверяет наличие нескольких записей для одной кампании и даты
"""
from core.database import SessionLocal
from core import models
from sqlalchemy import func, and_

def check_duplicates():
    """Проверяет наличие дубликатов в vk_stats"""
    db = SessionLocal()
    try:
        # Ищем дубликаты: записи с одинаковыми client_id, campaign_id и date
        duplicates_query = db.query(
            models.VKStats.client_id,
            models.VKStats.campaign_id,
            models.VKStats.date,
            func.count(models.VKStats.id).label('count'),
            func.sum(models.VKStats.conversions).label('total_conversions'),
            func.sum(models.VKStats.cost).label('total_cost'),
            func.sum(models.VKStats.clicks).label('total_clicks')
        ).group_by(
            models.VKStats.client_id,
            models.VKStats.campaign_id,
            models.VKStats.date
        ).having(
            func.count(models.VKStats.id) > 1
        )
        
        duplicates = duplicates_query.all()
        
        if duplicates:
            print(f"⚠️ НАЙДЕНО {len(duplicates)} ДУБЛИКАТОВ В vk_stats:\n")
            print("=" * 100)
            
            total_duplicate_records = 0
            total_extra_conversions = 0
            
            for dup in duplicates:
                count = dup.count
                total_duplicate_records += count
                
                # Получаем все записи для этого дубликата
                records = db.query(models.VKStats).filter(
                    and_(
                        models.VKStats.client_id == dup.client_id,
                        models.VKStats.campaign_id == dup.campaign_id,
                        models.VKStats.date == dup.date
                    )
                ).all()
                
                # Получаем название кампании
                campaign = db.query(models.Campaign).filter_by(id=dup.campaign_id).first()
                campaign_name = campaign.name if campaign else "Unknown"
                
                print(f"\n📊 Кампания: {campaign_name}")
                print(f"   Client ID: {dup.client_id}")
                print(f"   Campaign ID: {dup.campaign_id}")
                print(f"   Дата: {dup.date}")
                print(f"   Количество записей: {count} (должна быть 1!)")
                print(f"   Сумма conversions: {dup.total_conversions}")
                print(f"   Сумма cost: {dup.total_cost}")
                print(f"   Сумма clicks: {dup.total_clicks}")
                
                # Показываем детали каждой записи
                print(f"   Детали записей:")
                for idx, record in enumerate(records, 1):
                    print(f"      Запись {idx} (ID: {record.id}):")
                    print(f"        - conversions: {record.conversions}")
                    print(f"        - cost: {record.cost}")
                    print(f"        - clicks: {record.clicks}")
                    print(f"        - cpc: {record.cpc}")
                    print(f"        - cpa: {record.cpa}")
                
                # Если есть несколько записей, показываем разницу
                if count > 1:
                    # Берем первую запись как эталон
                    first_record = records[0]
                    other_conversions = sum(r.conversions for r in records[1:])
                    extra_conversions = other_conversions
                    total_extra_conversions += extra_conversions
                    
                    print(f"   ⚠️ Дополнительные conversions от дубликатов: {extra_conversions}")
                    print(f"   ⚠️ Если удалить дубликаты, останется: {first_record.conversions} conversions")
            
            print("\n" + "=" * 100)
            print(f"\n📈 СТАТИСТИКА ДУБЛИКАТОВ:")
            print(f"   Всего групп с дубликатами: {len(duplicates)}")
            print(f"   Всего дублирующихся записей: {total_duplicate_records}")
            print(f"   Дополнительных conversions от дубликатов: {total_extra_conversions}")
            print(f"   Если удалить дубликаты, будет удалено записей: {total_duplicate_records - len(duplicates)}")
            
            # Проверяем, может ли это объяснить разницу в 2 раза
            print(f"\n🔍 АНАЛИЗ:")
            if len(duplicates) > 0:
                avg_duplicates = total_duplicate_records / len(duplicates)
                print(f"   Среднее количество записей на дубликат: {avg_duplicates:.2f}")
                if avg_duplicates >= 2.0:
                    print(f"   ⚠️ ВНИМАНИЕ: Среднее количество записей >= 2, это может объяснить разницу в 2 раза!")
            
            return True
        else:
            print("✅ Дубликатов не найдено!")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при проверке дубликатов: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def check_campaign_totals():
    """Проверяет общее количество conversions по кампаниям"""
    db = SessionLocal()
    try:
        # Группируем по кампаниям и суммируем conversions
        campaign_totals = db.query(
            models.Campaign.id,
            models.Campaign.name,
            models.Campaign.external_id,
            func.count(models.VKStats.id).label('record_count'),
            func.sum(models.VKStats.conversions).label('total_conversions'),
            func.sum(models.VKStats.cost).label('total_cost'),
            func.sum(models.VKStats.clicks).label('total_clicks')
        ).join(
            models.VKStats, models.VKStats.campaign_id == models.Campaign.id
        ).group_by(
            models.Campaign.id,
            models.Campaign.name,
            models.Campaign.external_id
        ).order_by(
            func.sum(models.VKStats.conversions).desc()
        ).limit(20).all()
        
        print("\n" + "=" * 100)
        print("📊 ТОП-20 КАМПАНИЙ ПО CONVERSIONS:")
        print("=" * 100)
        
        for camp in campaign_totals:
            print(f"\n{camp.name} (ID: {camp.external_id})")
            print(f"   Записей в БД: {camp.record_count}")
            print(f"   Всего conversions: {camp.total_conversions}")
            print(f"   Всего cost: {camp.total_cost}")
            print(f"   Всего clicks: {camp.total_clicks}")
            
            # Если записей больше, чем дней в периоде, это подозрительно
            if camp.record_count > 365:
                print(f"   ⚠️ ПОДОЗРИТЕЛЬНО: Записей больше, чем дней в году!")
        
    except Exception as e:
        print(f"❌ Ошибка при проверке totals: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 100)
    print("ПРОВЕРКА ДУБЛИКАТОВ В vk_stats")
    print("=" * 100)
    
    has_duplicates = check_duplicates()
    
    if has_duplicates:
        print("\n" + "=" * 100)
        print("РЕКОМЕНДАЦИИ:")
        print("=" * 100)
        print("1. Добавить уникальный индекс на (client_id, campaign_id, date) в таблицу vk_stats")
        print("2. Удалить дублирующиеся записи, оставив только одну для каждой комбинации")
        print("3. Пересоздать синхронизацию для очистки данных")
        print("=" * 100)
    
    check_campaign_totals()

