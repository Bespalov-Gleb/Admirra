"""
Скрипт генерации еженедельного отчёта по качеству трафика.

Запуск вручную:
    python -m lead_validator.scripts.weekly_report

Запуск по расписанию (cron / Windows Task Scheduler):
    Рекомендуется запускать раз в неделю (понедельник 9:00)
"""

import asyncio
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


async def generate_and_send_report():
    """
    Генерирует еженедельный отчёт и отправляет в Telegram.
    """
    from lead_validator.services.analytics import analytics_service
    from lead_validator.services.telegram import telegram_notifier
    
    logger.info("=" * 50)
    logger.info("Генерация еженедельного отчёта по качеству трафика")
    logger.info("=" * 50)
    
    # Генерируем отчёт
    report = analytics_service.generate_weekly_report()
    
    logger.info(f"Период: {report.period_start.strftime('%d.%m.%Y')} - {report.period_end.strftime('%d.%m.%Y')}")
    logger.info(f"Всего заявок: {report.total_leads}")
    logger.info(f"Отклонено: {report.total_rejected}")
    logger.info(f"Процент мусора: {report.overall_rejection_rate:.1f}%")
    
    # Форматируем текст отчёта
    report_text = analytics_service.format_report_text(report)
    
    # Отправляем в Telegram
    if telegram_notifier.enabled:
        logger.info("Отправка отчёта в Telegram...")
        success = await telegram_notifier.send_message(report_text)
        if success:
            logger.info("✅ Отчёт успешно отправлен в Telegram")
        else:
            logger.error("❌ Не удалось отправить отчёт в Telegram")
    else:
        logger.warning("Telegram отключён, вывожу отчёт в консоль:")
        print()
        print(report_text)
        print()
    
    # Отправляем алерты по плохим источникам
    if report.bad_sources:
        logger.info(f"Найдено {len(report.bad_sources)} плохих источников")
        
        for bad_source in report.bad_sources[:5]:  # Топ 5 худших
            alert_text = analytics_service.format_alert_text(bad_source)
            if telegram_notifier.enabled:
                await telegram_notifier.send_message(alert_text)
                logger.info(f"Алерт отправлен: {bad_source.source}/{bad_source.campaign}")
    
    # Очищаем статистику после отправки отчёта
    # (раскомментировать для production)
    # analytics_service.clear_stats()
    # logger.info("Статистика очищена")
    
    logger.info("Генерация отчёта завершена")
    

async def check_bad_sources_daily():
    """
    Ежедневная проверка на плохие источники (можно запускать чаще).
    Отправляет алерты если есть источники с >70% мусора.
    """
    from lead_validator.services.analytics import analytics_service
    from lead_validator.services.telegram import telegram_notifier
    
    logger.info("Проверка плохих источников...")
    
    # Получаем источники с >70% мусора
    bad_sources = analytics_service.get_bad_sources(
        min_leads=10,
        min_rejection_rate=70.0
    )
    
    if not bad_sources:
        logger.info("Плохих источников не обнаружено")
        return
    
    logger.warning(f"Обнаружено {len(bad_sources)} критически плохих источников!")
    
    for source in bad_sources[:3]:  # Топ 3 худших
        alert_text = (
            f"🚨 *КРИТИЧЕСКИЙ АЛЕРТ*\n\n"
            f"Источник `{source.source}/{source.campaign}` "
            f"имеет {source.rejection_rate:.1f}% мусора!\n\n"
            f"Площадка: `{source.content}`\n"
            f"Заявок: {source.total_leads}, отклонено: {source.rejected_leads}\n\n"
            f"⚠️ *Рекомендуется срочно добавить в исключения*"
        )
        
        if telegram_notifier.enabled:
            await telegram_notifier.send_message(alert_text)
        else:
            print(alert_text)


def main():
    """Точка входа."""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--daily":
        # Ежедневная проверка
        asyncio.run(check_bad_sources_daily())
    else:
        # Полный еженедельный отчёт
        asyncio.run(generate_and_send_report())


if __name__ == "__main__":
    main()
