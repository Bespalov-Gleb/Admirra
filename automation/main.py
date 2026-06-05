from apscheduler.schedulers.asyncio import AsyncIOScheduler
from automation.sync import sync_data
import asyncio
import logging
import pytz
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MSK = pytz.timezone("Europe/Moscow")

SYNC_HOURS_MSK = [3]  # 03:00 МСК, один ночной автосинк в сутки

async def sync_with_log():
    now_msk = datetime.now(MSK).strftime("%Y-%m-%d %H:%M МСК")
    logger.info("=" * 60)
    logger.info(f"🔄 Автосинхронизация ЗАПУЩЕНА — {now_msk}")
    logger.info("=" * 60)
    try:
        await sync_data()
        finish_msk = datetime.now(MSK).strftime("%Y-%m-%d %H:%M МСК")
        logger.info("=" * 60)
        logger.info(f"✅ Автосинхронизация ЗАВЕРШЕНА — {finish_msk}")
        logger.info("=" * 60)
    except Exception as e:
        finish_msk = datetime.now(MSK).strftime("%Y-%m-%d %H:%M МСК")
        logger.error("=" * 60)
        logger.error(f"❌ Автосинхронизация ОШИБКА — {finish_msk}: {e}")
        logger.error("=" * 60)
        raise

async def main():
    scheduler = AsyncIOScheduler(timezone=MSK)

    for hour in SYNC_HOURS_MSK:
        scheduler.add_job(
            sync_with_log,
            "cron",
            hour=hour,
            minute=0,
            id=f"sync_all_data_{hour:02d}00",
        )

    next_runs = ", ".join(f"{h:02d}:00" for h in SYNC_HOURS_MSK)
    logger.info(f"✅ Планировщик запущен. Синхронизация по МСК: {next_runs}")

    scheduler.start()

    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        logger.info("✅ Планировщик остановлен.")

if __name__ == "__main__":
    asyncio.run(main())
