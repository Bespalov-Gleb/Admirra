from apscheduler.schedulers.asyncio import AsyncIOScheduler
from automation.sync import sync_data
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    scheduler = AsyncIOScheduler()
    
    # Run sync every 6 hours
    scheduler.add_job(sync_data, 'interval', hours=6, id='sync_all_data')
    
    # Also run immediately on start for testing
    scheduler.add_job(sync_data, 'date', id='sync_now')
    
    logger.info("Automation scheduler started.")
    scheduler.start()

    try:
        # Keep the process running
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Automation scheduler stopped.")

if __name__ == "__main__":
    asyncio.run(main())
