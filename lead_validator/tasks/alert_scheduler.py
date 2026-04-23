"""
Scheduled task для автоматических оповещений о плохих источниках трафика.

Запускается раз в день, анализирует данные за последние 7 дней и отправляет
алерты в Telegram при превышении порога мусора (50% по умолчанию).
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import List
from lead_validator.services.analytics import analytics_service, SourceStats
from lead_validator.services.telegram import telegram_notifier
from lead_validator.services.placement_blacklist import placement_blacklist
from lead_validator.config import settings

logger = logging.getLogger("lead_validator.alert_scheduler")


class AlertScheduler:
    """
    Планировщик для автоматических оповещений.
    
    Использует APScheduler для запуска задач по расписанию.
    """
    
    def __init__(self):
        self.alert_threshold_percent = settings.ALERT_THRESHOLD_PERCENT
        self.alert_lookback_days = settings.ALERT_LOOKBACK_DAYS
        self.min_leads_for_alert = settings.ALERT_MIN_LEADS
        
    async def check_and_send_alerts(self):
        """
        Проверить источники трафика и отправить алерты.
        
        Запускается по расписанию (раз в день).
        """
        logger.info("Starting daily alert check...")
        
        try:
            # Получаем плохие источники
            bad_sources = analytics_service.get_bad_sources(
                min_leads=self.min_leads_for_alert,
                min_rejection_rate=self.alert_threshold_percent
            )
            
            if not bad_sources:
                logger.info("No bad sources found, no alerts needed")
                return
            
            logger.info(f"Found {len(bad_sources)} bad sources, sending alerts...")
            
            # Отправляем алерт для каждого плохого источника
            for source in bad_sources:
                try:
                    alert_text = analytics_service.format_alert_text(source)
                    await telegram_notifier.send_message(alert_text)
                    logger.info(f"Alert sent for source: {source.source}/{source.campaign}")
                    
                    # Небольшая задержка между сообщениями
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Failed to send alert for {source.source}: {e}")
            
            logger.info(f"Alert check completed, sent {len(bad_sources)} alerts")
            
            # Обновляем динамический чёрный список
            try:
                added_count = await placement_blacklist.update_blacklist()
                if added_count > 0:
                    logger.info(f"Updated placement blacklist: {added_count} new placements added")
            except Exception as e:
                logger.error(f"Error updating blacklist: {e}")
            
        except Exception as e:
            logger.error(f"Error in alert check: {e}", exc_info=True)
    
    async def send_weekly_report(self):
        """
        Отправить еженедельный отчёт в Telegram.
        
        Запускается раз в неделю (например, по понедельникам).
        """
        logger.info("Generating weekly report...")
        
        try:
            report = analytics_service.generate_weekly_report()
            report_text = analytics_service.format_report_text(report)
            
            await telegram_notifier.send_message(report_text)
            logger.info("Weekly report sent successfully")
            
            # Очищаем статистику после отправки отчёта
            # analytics_service.clear_stats()  # Раскомментировать если нужно
            
        except Exception as e:
            logger.error(f"Error sending weekly report: {e}", exc_info=True)


# Глобальный экземпляр
alert_scheduler = AlertScheduler()


async def run_daily_alerts():
    """Функция для запуска из планировщика."""
    await alert_scheduler.check_and_send_alerts()


async def run_weekly_report():
    """Функция для запуска еженедельного отчёта."""
    await alert_scheduler.send_weekly_report()

