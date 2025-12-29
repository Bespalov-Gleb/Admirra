from core.database import SessionLocal
from core import models
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cleanup")

def cleanup():
    db = SessionLocal()
    try:
        logger.info("Starting database cleanup...")
        
        # Delete statistics data
        logger.info("Deleting statistics...")
        db.query(models.YandexStats).delete()
        db.query(models.YandexKeywords).delete()
        db.query(models.YandexGroups).delete()
        db.query(models.VKStats).delete()
        db.query(models.MetrikaGoals).delete()
        
        # Delete reports
        logger.info("Deleting reports...")
        db.query(models.WeeklyReport).delete()
        db.query(models.MonthlyReport).delete()
        
        # Delete integrations and clients
        logger.info("Deleting integrations and clients...")
        # Note: Order matters due to foreign keys. 
        # Integrations first, then Clients.
        db.query(models.Integration).delete()
        db.query(models.Client).delete()
        
        db.commit()
        logger.info("Database cleanup completed successfully. Only user accounts remain.")
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    cleanup()
