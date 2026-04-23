"""
Диагностика: почему расходы/показы/клики = 0, а лиды есть (данные только из Метрики).

Источники данных:
- Расходы, Показы, Клики, CPC, CPA — из YandexStats (Директ) и VKStats (VK)
- Лиды — из MetrikaGoals (Метрика), fallback на conversions из Direct/VK
"""
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import SessionLocal
from core import models
from sqlalchemy import func


def diagnose(client_name: str = None):
    db = SessionLocal()
    try:
        print("=" * 70)
        print("ДИАГНОСТИКА: Direct vs Metrika")
        print("=" * 70)

        # Выбор клиента
        if client_name:
            clients = db.query(models.Client).filter(models.Client.name.ilike(f"%{client_name}%")).all()
        else:
            clients = db.query(models.Client).all()

        if not clients:
            print("❌ Клиенты не найдены")
            return

        # Период: эта неделя (как на дашборде)
        today = datetime.now().date()
        d_end = today
        d_start = today - timedelta(days=6)

        for client in clients:
            print(f"\n📋 Клиент: {client.name} (ID: {client.id})")
            print("-" * 70)

            # 1. Интеграции
            integrations = db.query(models.Integration).filter(
                models.Integration.client_id == client.id
            ).all()

            has_direct = any(i.platform == models.IntegrationPlatform.YANDEX_DIRECT for i in integrations)
            has_metrika = any(i.platform == models.IntegrationPlatform.YANDEX_METRIKA for i in integrations)

            print(f"\n1. Интеграции:")
            for i in integrations:
                status = i.sync_status.value if i.sync_status else "?"
                last = i.last_sync_at.strftime("%Y-%m-%d %H:%M") if i.last_sync_at else "никогда"
                err = f" | Ошибка: {i.error_message[:50]}..." if i.error_message else ""
                print(f"   - {i.platform.value}: sync={status}, last={last}{err}")

            if not has_direct:
                print("\n   ⚠️ Нет интеграции YANDEX_DIRECT! Расходы/показы/клики всегда 0.")
                print("   Решение: подключите Яндекс.Директ в настройках проекта.")

            # 2. YandexStats (Direct)
            y_total = db.query(func.count(models.YandexStats.id)).filter(
                models.YandexStats.client_id == client.id
            ).scalar()

            y_in_range = db.query(func.count(models.YandexStats.id)).filter(
                models.YandexStats.client_id == client.id,
                models.YandexStats.date >= d_start,
                models.YandexStats.date <= d_end
            ).scalar()

            y_with_campaign = db.query(func.count(models.YandexStats.id)).join(
                models.Campaign, models.YandexStats.campaign_id == models.Campaign.id
            ).filter(
                models.YandexStats.client_id == client.id,
                models.YandexStats.date >= d_start,
                models.YandexStats.date <= d_end
            ).scalar()

            y_active = db.query(
                func.sum(models.YandexStats.cost).label("cost"),
                func.sum(models.YandexStats.impressions).label("imps"),
                func.sum(models.YandexStats.clicks).label("clicks")
            ).join(models.Campaign, models.YandexStats.campaign_id == models.Campaign.id).filter(
                models.YandexStats.client_id == client.id,
                models.Campaign.is_active.is_(True),
                models.YandexStats.date >= d_start,
                models.YandexStats.date <= d_end
            ).first()

            print(f"\n2. YandexStats (Директ) за {d_start}..{d_end}:")
            print(f"   Всего записей по клиенту: {y_total}")
            print(f"   В выбранном периоде: {y_in_range}")
            print(f"   С привязанной кампанией (campaign_id): {y_with_campaign}")
            if y_active:
                print(f"   По активным кампаниям: расходы={float(y_active.cost or 0):.2f} ₽, показы={int(y_active.imps or 0)}, клики={int(y_active.clicks or 0)}")

            if y_in_range > 0 and y_with_campaign == 0:
                print("   ⚠️ Есть записи, но campaign_id = NULL! Запустите: python migrate_campaign_ids.py")

            if y_in_range == 0 and has_direct:
                print("   ⚠️ Нет данных Direct за период. Проверьте: синхронизация, выбранный профиль (agency_client_login), наличие кампаний в Директе.")

            # 3. MetrikaGoals
            m_in_range = db.query(func.sum(models.MetrikaGoals.conversion_count)).filter(
                models.MetrikaGoals.client_id == client.id,
                models.MetrikaGoals.goal_id != "all",
                models.MetrikaGoals.date >= d_start,
                models.MetrikaGoals.date <= d_end
            ).scalar()

            print(f"\n3. MetrikaGoals (Метрика) за {d_start}..{d_end}:")
            print(f"   Лиды: {int(m_in_range or 0)}")

            # 4. Итог
            print(f"\n4. Итог для дашборда:")
            costs = float(y_active.cost or 0) if y_active else 0
            imps = int(y_active.imps or 0) if y_active else 0
            clks = int(y_active.clicks or 0) if y_active else 0
            leads = int(m_in_range or 0)
            print(f"   Расходы: {costs:.2f} ₽ | Показы: {imps} | Клики: {clks} | Лиды: {leads}")

            if costs == 0 and imps == 0 and clks == 0 and leads > 0:
                print("\n   🔴 Причина: данные Direct отсутствуют, лиды идут только из Метрики.")
                print("   Действия: 1) Запустите синхронизацию Директа 2) Проверьте интеграцию и кампании")

        print("\n" + "=" * 70)

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    client_name = sys.argv[1] if len(sys.argv) > 1 else None
    diagnose(client_name)
