import asyncio
import sys
import os

# Add parent directory to sys.path to allow imports from core
sys.path.append(os.getcwd())

from core.database import SessionLocal
from core.models import Integration
from sqlalchemy import select

async def check_error():
    db = SessionLocal()
    try:
        search_str = 'kcu-stroi-412538-fibw'
        print(f"Searching for '{search_str}' in all relevant tables...")
        
        from core.models import Integration, Campaign, Client
        from sqlalchemy import or_

        # 1. Search in Integrations
        integrations = db.execute(select(Integration).where(
            or_(
                Integration.account_id.contains(search_str),
                Integration.agency_client_login.contains(search_str),
                Integration.error_message.contains(search_str)
            )
        )).scalars().all()
        
        if integrations:
            print(f"Found {len(integrations)} integrations:")
            for integration in integrations:
                print(f"--- Integration {integration.id} ---")
                print(f"Account: {integration.account_id}, Agency: {integration.agency_client_login}")
                print(f"Status: {integration.sync_status}, Error: {integration.error_message}")
        else:
            print("No integrations found with this ID.")

        # 2. Search in Campaigns
        campaigns = db.execute(select(Campaign).where(
            or_(
                Campaign.external_id.contains(search_str),
                Campaign.name.contains(search_str)
            )
        )).scalars().all()
        
        if campaigns:
            print(f"Found {len(campaigns)} campaigns:")
            for c in campaigns:
                print(f"Campaign: {c.name}, External ID: {c.external_id}, Integration ID: {c.integration_id}")
        else:
            print("No campaigns found with this ID.")

        # 3. Always list all integrations just in case
        print("\nAll current integrations in DB:")
        all_ints = db.execute(select(Integration)).scalars().all()
        for i in all_ints:
             print(f"- {i.account_id} (Platform: {i.platform}, Status: {i.sync_status})")
            
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(check_error())
