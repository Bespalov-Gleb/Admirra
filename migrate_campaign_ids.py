#!/usr/bin/env python3
"""
Migrate existing YandexStats and VKStats records to populate campaign_id field.
This is needed because old records were saved without campaign_id.
"""

import sys
from sqlalchemy.orm import Session
from core.database import SessionLocal
from core import models
from datetime import datetime

def migrate_yandex_stats(db: Session):
    """Link YandexStats to campaigns by matching campaign_name and external_id"""
    print("Migrating YandexStats...")
    
    # Get all YandexStats without campaign_id
    stats_without_campaign = db.query(models.YandexStats).filter(
        models.YandexStats.campaign_id == None
    ).all()
    
    print(f"Found {len(stats_without_campaign)} YandexStats records without campaign_id")
    
    updated = 0
    for stat in stats_without_campaign:
        # Find matching campaign by integration's client_id and campaign_name
        # First, find all integrations for this client
        integrations = db.query(models.Integration).filter(
            models.Integration.client_id == stat.client_id,
            models.Integration.platform == models.IntegrationPlatform.YANDEX_DIRECT
        ).all()
        
        # Try to find campaign in any of the integrations
        campaign = None
        for integration in integrations:
            # Try to match by name first
            campaign = db.query(models.Campaign).filter(
                models.Campaign.integration_id == integration.id,
                models.Campaign.name == stat.campaign_name
            ).first()
            
            if campaign:
                break
        
        if campaign:
            stat.campaign_id = campaign.id
            updated += 1
        else:
            print(f"  WARNING: Could not find campaign for stat: {stat.campaign_name} (date: {stat.date})")
    
    db.commit()
    print(f"✅ Updated {updated} YandexStats records")
    return updated

def migrate_vk_stats(db: Session):
    """Link VKStats to campaigns by matching campaign_name"""
    print("\nMigrating VKStats...")
    
    # Get all VKStats without campaign_id
    stats_without_campaign = db.query(models.VKStats).filter(
        models.VKStats.campaign_id == None
    ).all()
    
    print(f"Found {len(stats_without_campaign)} VKStats records without campaign_id")
    
    updated = 0
    for stat in stats_without_campaign:
        # Find matching campaign
        integrations = db.query(models.Integration).filter(
            models.Integration.client_id == stat.client_id,
            models.Integration.platform == models.IntegrationPlatform.VK_ADS
        ).all()
        
        campaign = None
        for integration in integrations:
            campaign = db.query(models.Campaign).filter(
                models.Campaign.integration_id == integration.id,
                models.Campaign.name == stat.campaign_name
            ).first()
            
            if campaign:
                break
        
        if campaign:
            stat.campaign_id = campaign.id
            updated += 1
        else:
            print(f"  WARNING: Could not find campaign for stat: {stat.campaign_name} (date: {stat.date})")
    
    db.commit()
    print(f"✅ Updated {updated} VKStats records")
    return updated

def main():
    db = SessionLocal()
    try:
        print("=" * 60)
        print("Starting campaign_id migration")
        print("=" * 60)
        
        yandex_updated = migrate_yandex_stats(db)
        vk_updated = migrate_vk_stats(db)
        
        print("\n" + "=" * 60)
        print(f"✅ Migration completed successfully!")
        print(f"   - YandexStats updated: {yandex_updated}")
        print(f"   - VKStats updated: {vk_updated}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()

