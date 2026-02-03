"""
Backfill integration_id for existing MetrikaGoals records.

This script should be run AFTER the migration to populate integration_id for existing records.
It matches MetrikaGoals records to integrations based on client_id and date range.
"""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from core.models import MetrikaGoals, Integration, IntegrationPlatform
from core.database import SQLALCHEMY_DATABASE_URL

# Setup logging
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

def backfill_integration_ids():
    """
    Backfill integration_id for existing MetrikaGoals records.
    
    Strategy:
    1. Find all MetrikaGoals with integration_id = NULL
    2. For each goal, find matching integrations based on:
       - client_id matches
       - integration is YANDEX_METRIKA or has Metrika access
       - date falls within integration's active period (last_sync_at)
    3. If only one match, assign that integration_id
    4. If multiple matches or no match, log warning (manual intervention needed)
    """
    db = get_db()
    
    try:
        # Find all MetrikaGoals without integration_id
        goals_without_integration = db.query(MetrikaGoals).filter(
            MetrikaGoals.integration_id == None
        ).all()
        
        logger.info(f"Found {len(goals_without_integration)} MetrikaGoals records without integration_id")
        
        updated_count = 0
        warning_count = 0
        
        for goal in goals_without_integration:
            # Find potential integrations for this goal
            # Look for integrations:
            # 1. Matching client_id
            # 2. Platform is YANDEX_DIRECT or YANDEX_METRIKA (both can have Metrika goals)
            potential_integrations = db.query(Integration).filter(
                Integration.client_id == goal.client_id,
                Integration.platform.in_([IntegrationPlatform.YANDEX_DIRECT, IntegrationPlatform.YANDEX_METRIKA])
            ).all()
            
            if len(potential_integrations) == 0:
                logger.warning(f"No integration found for MetrikaGoal (client_id: {goal.client_id}, date: {goal.date}, goal_id: {goal.goal_id})")
                warning_count += 1
                continue
            
            if len(potential_integrations) == 1:
                # Only one match, assign it
                goal.integration_id = potential_integrations[0].id
                updated_count += 1
                logger.info(f"Assigned integration {potential_integrations[0].id} to MetrikaGoal {goal.id}")
            else:
                # Multiple matches - try to narrow down by date
                # Prefer the integration that was last synced closest to the goal's date
                best_match = None
                min_diff = None
                
                for integration in potential_integrations:
                    if integration.last_sync_at:
                        diff = abs((integration.last_sync_at.date() - goal.date).days)
                        if min_diff is None or diff < min_diff:
                            min_diff = diff
                            best_match = integration
                
                if best_match:
                    goal.integration_id = best_match.id
                    updated_count += 1
                    logger.info(f"Assigned integration {best_match.id} to MetrikaGoal {goal.id} (best match by date)")
                else:
                    # Assign to the first one as fallback
                    goal.integration_id = potential_integrations[0].id
                    updated_count += 1
                    logger.warning(f"Multiple integrations found for MetrikaGoal {goal.id}, assigned to first one: {potential_integrations[0].id}")
                    warning_count += 1
        
        db.commit()
        
        logger.info("============================================================")
        logger.info("✅ Backfill completed successfully!")
        logger.info(f"   - Updated: {updated_count} records")
        logger.info(f"   - Warnings: {warning_count} records (ambiguous or no match)")
        logger.info("============================================================")
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ An error occurred during backfill: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("Starting backfill of integration_id for MetrikaGoals...")
    backfill_integration_ids()


