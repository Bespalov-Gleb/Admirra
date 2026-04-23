import sys
import os

sys.path.append(os.getcwd())

from core.database import SessionLocal
from core import models

def link_old_stats_to_campaigns():
    db = SessionLocal()
    try:
        print("=" * 70)
        print("ПАЙВАСТИ МАЪЛУМОТҲОИ КӮҲНА БА КАМПАНИЯҲОИ НАВ")
        print("=" * 70)
        
        # Get the client "трафик аккаунт"
        client = db.query(models.Client).filter(
            models.Client.name == "трафик аккаунт"
        ).first()
        
        if not client:
            print("❌ Мизоҷ пайдо нашуд!")
            return
        
        print(f"\nМизоҷ: {client.name} (ID: {client.id})")
        
        # Get stats without campaign_id
        orphan_stats = db.query(models.YandexStats).filter(
            models.YandexStats.client_id == client.id,
            models.YandexStats.campaign_id == None
        ).all()
        
        print(f"Маълумот бе campaign_id: {len(orphan_stats)} сатр")
        
        # Get stats with campaign names
        stats_with_names = db.query(
            models.YandexStats.campaign_name,
            models.YandexStats.campaign_id
        ).filter(
            models.YandexStats.client_id == client.id
        ).distinct().all()
        
        print(f"\nНомҳои кампанияҳо дар маълумот:")
        for s in stats_with_names:
            print(f"  - {s.campaign_name} (campaign_id: {s.campaign_id})")
        
        # Get current campaigns
        integration = db.query(models.Integration).filter(
            models.Integration.client_id == client.id,
            models.Integration.platform == models.IntegrationPlatform.YANDEX_DIRECT
        ).first()
        
        if not integration:
            print("\n❌ Интегратсия пайдо нашуд!")
            return
        
        campaigns = db.query(models.Campaign).filter(
            models.Campaign.integration_id == integration.id
        ).all()
        
        print(f"\nКампанияҳои ҷорӣ ({len(campaigns)}):")
        for c in campaigns:
            print(f"  - {c.name} (ID: {c.id}, ExtID: {c.external_id}, Active: {c.is_active})")
        
        # Strategy: Create campaigns for old stats if they don't exist
        print("\n" + "=" * 70)
        print("ЭҶОДИ КАМПАНИЯҲО БАРОИ МАЪЛУМОТҲОИ КӮҲНА")
        print("=" * 70)
        
        unique_campaign_names = db.query(
            models.YandexStats.campaign_name
        ).filter(
            models.YandexStats.client_id == client.id
        ).distinct().all()
        
        created_count = 0
        updated_count = 0
        
        for (campaign_name,) in unique_campaign_names:
            if not campaign_name:
                continue
            
            # Check if campaign exists
            existing = db.query(models.Campaign).filter(
                models.Campaign.integration_id == integration.id,
                models.Campaign.name == campaign_name
            ).first()
            
            if not existing:
                # Create new campaign
                new_campaign = models.Campaign(
                    integration_id=integration.id,
                    external_id=f"historical_{campaign_name.replace(' ', '_')}",
                    name=campaign_name,
                    is_active=True  # Make it active so it shows in dashboard
                )
                db.add(new_campaign)
                db.flush()
                created_count += 1
                print(f"✓ Эҷод: {campaign_name}")
                
                # Link stats to this campaign
                db.query(models.YandexStats).filter(
                    models.YandexStats.client_id == client.id,
                    models.YandexStats.campaign_name == campaign_name
                ).update({"campaign_id": new_campaign.id})
                updated_count += db.query(models.YandexStats).filter(
                    models.YandexStats.client_id == client.id,
                    models.YandexStats.campaign_name == campaign_name
                ).count()
            else:
                # Link stats to existing campaign
                count = db.query(models.YandexStats).filter(
                    models.YandexStats.client_id == client.id,
                    models.YandexStats.campaign_name == campaign_name,
                    models.YandexStats.campaign_id == None
                ).update({"campaign_id": existing.id})
                if count > 0:
                    updated_count += count
                    print(f"✓ Пайваст: {campaign_name} ({count} сатр)")
        
        db.commit()
        
        print(f"\n" + "=" * 70)
        print(f"НАТИҶА:")
        print(f"  Кампанияҳои нав: {created_count}")
        print(f"  Сатрҳои навсозишуда: {updated_count}")
        print("=" * 70)
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Хато: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    link_old_stats_to_campaigns()
