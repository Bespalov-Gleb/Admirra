from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
import logging
import os
import pytz
from datetime import datetime

from core.database import SessionLocal
from core import models

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MSK = pytz.timezone("Europe/Moscow")

# 03:00 МСК — ставим авто-задачи в очередь; 05:00 — отчёты после окна синка.
SYNC_HOUR_MSK = int(os.getenv("AUTO_SYNC_HOUR_MSK", "3"))
REPORTS_HOUR_MSK = int(os.getenv("AUTO_REPORTS_HOUR_MSK", "5"))
AUTO_SYNC_DAYS = int(os.getenv("AUTO_SYNC_DAYS", "7"))


async def enqueue_auto_sync():
    """Ставит все интеграции активных клиентов в общую очередь синхронизации.

    Сам синк выполняет честный воркер в backend (per-client cap, инкрементальность,
    ретраи). Здесь только планирование — никакой тяжёлой работы и обращений к API.
    """
    now_msk = datetime.now(MSK).strftime("%Y-%m-%d %H:%M МСК")
    logger.info("=" * 60)
    logger.info(f"🌙 Автосинхронизация: постановка задач в очередь — {now_msk}")

    from backend_api.sync_jobs import enqueue_sync_job

    db = SessionLocal()
    try:
        integration_ids = [
            row[0]
            for row in (
                db.query(models.Integration.id)
                .join(models.Client, models.Client.id == models.Integration.client_id)
                .filter(models.Client.status == models.ClientStatus.ACTIVE)
                .all()
            )
        ]
    finally:
        db.close()

    enqueued = 0
    for integration_id in integration_ids:
        try:
            # start_worker=False — воркер держит backend, automation только планирует
            enqueue_sync_job(
                integration_id,
                days=AUTO_SYNC_DAYS,
                trigger="auto",
                start_worker=False,
            )
            enqueued += 1
        except Exception as e:
            logger.error(f"Failed to enqueue auto-sync for integration {integration_id}: {e}")

    logger.info(f"✅ Поставлено в очередь {enqueued}/{len(integration_ids)} интеграций")
    logger.info("=" * 60)


async def run_reports():
    """Ночные отчёты + выгрузка в Google Sheets после окна синхронизации."""
    now_msk = datetime.now(MSK).strftime("%Y-%m-%d %H:%M МСК")
    logger.info(f"📊 Генерация отчётов и выгрузка в Sheets — {now_msk}")
    try:
        from automation.sync import run_post_sync_reports
        # Блокирующая SQL-работа — уводим в поток, чтобы не держать event loop
        await asyncio.to_thread(run_post_sync_reports)
        logger.info("✅ Отчёты сгенерированы")
    except Exception as e:
        logger.error(f"❌ Ошибка генерации отчётов: {e}")


async def main():
    scheduler = AsyncIOScheduler(timezone=MSK)

    scheduler.add_job(
        enqueue_auto_sync,
        "cron",
        hour=SYNC_HOUR_MSK,
        minute=0,
        id="auto_sync_enqueue",
    )
    scheduler.add_job(
        run_reports,
        "cron",
        hour=REPORTS_HOUR_MSK,
        minute=0,
        id="auto_reports",
    )

    logger.info(
        "✅ Планировщик запущен. Постановка синка: %02d:00 МСК, отчёты: %02d:00 МСК",
        SYNC_HOUR_MSK,
        REPORTS_HOUR_MSK,
    )

    scheduler.start()

    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        logger.info("✅ Планировщик остановлен.")


if __name__ == "__main__":
    asyncio.run(main())
