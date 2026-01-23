"""
Сервис еженедельных отчётов по качеству трафика.

Уровень 8 по ТЗ:
- Агрегация отклонённых заявок по источникам
- Расчёт коэффициента качества
- Отправка отчётов в Telegram
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict

from lead_validator.config import settings

logger = logging.getLogger("lead_validator.analytics")


@dataclass
class SourceStats:
    """Статистика по источнику трафика."""
    source: str
    campaign: str
    content: str  # Площадка в РСЯ
    total_leads: int = 0
    rejected_leads: int = 0
    rejection_reasons: Dict[str, int] = field(default_factory=dict)
    
    @property
    def rejection_rate(self) -> float:
        """Процент отклонённых заявок."""
        if self.total_leads == 0:
            return 0.0
        return (self.rejected_leads / self.total_leads) * 100
    
    @property
    def is_bad_source(self) -> bool:
        """Источник считается плохим если >50% мусора."""
        return self.rejection_rate > 50 and self.rejected_leads >= 5


@dataclass  
class WeeklyReport:
    """Еженедельный отчёт по качеству трафика."""
    period_start: datetime
    period_end: datetime
    total_leads: int = 0
    total_rejected: int = 0
    sources: List[SourceStats] = field(default_factory=list)
    top_rejection_reasons: Dict[str, int] = field(default_factory=dict)
    bad_sources: List[SourceStats] = field(default_factory=list)
    
    @property
    def overall_rejection_rate(self) -> float:
        """Общий процент отклонений."""
        if self.total_leads == 0:
            return 0.0
        return (self.total_rejected / self.total_leads) * 100


class AnalyticsService:
    """
    Сервис аналитики и отчётности.
    
    Функции:
    - Агрегация статистики по источникам
    - Генерация еженедельных отчётов
    - Определение плохих площадок
    - Отправка алертов в Telegram
    """
    
    def __init__(self):
        # In-memory хранилище для статистики
        # В production использовать Redis или БД
        self._stats: Dict[str, SourceStats] = {}
        self._daily_stats: Dict[str, Dict] = {}  # По дням
        
    def _get_source_key(
        self, 
        utm_source: Optional[str],
        utm_campaign: Optional[str],
        utm_content: Optional[str]
    ) -> str:
        """Создать ключ для группировки по источнику."""
        return f"{utm_source or 'direct'}|{utm_campaign or 'none'}|{utm_content or 'none'}"
    
    def record_lead(
        self,
        utm_source: Optional[str] = None,
        utm_campaign: Optional[str] = None,
        utm_content: Optional[str] = None,
        rejected: bool = False,
        rejection_reason: Optional[str] = None
    ):
        """
        Записать статистику по лиду.
        
        Args:
            utm_source: Источник трафика
            utm_campaign: Кампания
            utm_content: Площадка (для РСЯ)
            rejected: Был ли лид отклонён
            rejection_reason: Причина отклонения
        """
        key = self._get_source_key(utm_source, utm_campaign, utm_content)
        
        if key not in self._stats:
            self._stats[key] = SourceStats(
                source=utm_source or "direct",
                campaign=utm_campaign or "none",
                content=utm_content or "none"
            )
        
        stats = self._stats[key]
        stats.total_leads += 1
        
        if rejected:
            stats.rejected_leads += 1
            if rejection_reason:
                # Группируем причины
                reason_group = rejection_reason.split(":")[0]
                stats.rejection_reasons[reason_group] = \
                    stats.rejection_reasons.get(reason_group, 0) + 1
        
        logger.debug(f"Recorded lead for {key}: rejected={rejected}")
    
    def get_bad_sources(self, min_leads: int = 5, min_rejection_rate: float = 50.0) -> List[SourceStats]:
        """
        Получить список плохих источников.
        
        Args:
            min_leads: Минимальное кол-во заявок для анализа
            min_rejection_rate: Минимальный % отклонений для признания плохим
            
        Returns:
            Список плохих источников, отсортированный по % отклонений
        """
        bad_sources = []
        
        for stats in self._stats.values():
            if stats.total_leads >= min_leads and stats.rejection_rate >= min_rejection_rate:
                bad_sources.append(stats)
        
        # Сортируем по проценту отклонений (худшие первые)
        bad_sources.sort(key=lambda x: x.rejection_rate, reverse=True)
        
        return bad_sources
    
    def generate_weekly_report(self) -> WeeklyReport:
        """
        Генерировать еженедельный отчёт.
        
        Returns:
            WeeklyReport с агрегированными данными
        """
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        
        report = WeeklyReport(
            period_start=week_ago,
            period_end=now
        )
        
        # Агрегируем по всем источникам
        all_reasons: Dict[str, int] = defaultdict(int)
        
        for stats in self._stats.values():
            report.total_leads += stats.total_leads
            report.total_rejected += stats.rejected_leads
            report.sources.append(stats)
            
            for reason, count in stats.rejection_reasons.items():
                all_reasons[reason] += count
        
        # Топ причин отклонения
        report.top_rejection_reasons = dict(
            sorted(all_reasons.items(), key=lambda x: x[1], reverse=True)[:10]
        )
        
        # Плохие источники
        report.bad_sources = self.get_bad_sources()
        
        return report
    
    def format_report_text(self, report: WeeklyReport) -> str:
        """
        Форматировать отчёт для Telegram.
        
        Args:
            report: WeeklyReport
            
        Returns:
            Текст отчёта в Markdown
        """
        lines = [
            "📊 *ЕЖЕНЕДЕЛЬНЫЙ ОТЧЁТ ПО КАЧЕСТВУ ТРАФИКА*",
            "",
            f"📅 Период: {report.period_start.strftime('%d.%m.%Y')} - {report.period_end.strftime('%d.%m.%Y')}",
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            f"📈 *Общая статистика:*",
            f"• Всего заявок: {report.total_leads}",
            f"• Отклонено: {report.total_rejected}",
            f"• Процент мусора: {report.overall_rejection_rate:.1f}%",
            "",
        ]
        
        # Топ причин отклонения
        if report.top_rejection_reasons:
            lines.append("❌ *Топ причин отклонения:*")
            for reason, count in list(report.top_rejection_reasons.items())[:5]:
                lines.append(f"• {reason}: {count}")
            lines.append("")
        
        # Плохие источники
        if report.bad_sources:
            lines.append("🚨 *ПЛОХИЕ ИСТОЧНИКИ (>50% мусора):*")
            lines.append("")
            
            for source in report.bad_sources[:10]:
                lines.append(
                    f"⚠️ `{source.source}/{source.campaign}`\n"
                    f"   Площадка: `{source.content}`\n"
                    f"   Заявок: {source.total_leads}, отклонено: {source.rejected_leads} "
                    f"({source.rejection_rate:.1f}%)"
                )
                lines.append("")
            
            lines.append("💡 _Рекомендуется добавить эти площадки в исключения_")
        else:
            lines.append("✅ Плохих источников не обнаружено")
        
        return "\n".join(lines)
    
    def format_alert_text(self, bad_source: SourceStats) -> str:
        """
        Форматировать алерт о плохом источнике.
        
        Args:
            bad_source: Статистика плохого источника
            
        Returns:
            Текст алерта
        """
        return (
            f"🚨 *АЛЕРТ: Плохой источник трафика*\n\n"
            f"Источник: `{bad_source.source}`\n"
            f"Кампания: `{bad_source.campaign}`\n"
            f"Площадка: `{bad_source.content}`\n\n"
            f"📊 Статистика за 7 дней:\n"
            f"• Всего заявок: {bad_source.total_leads}\n"
            f"• Отклонено: {bad_source.rejected_leads}\n"
            f"• Процент мусора: {bad_source.rejection_rate:.1f}%\n\n"
            f"💡 *Рекомендуется добавить в исключения*"
        )
    
    def clear_stats(self):
        """Очистить статистику (после генерации отчёта)."""
        self._stats.clear()
        logger.info("Analytics stats cleared")
    
    def get_source_stats(
        self,
        utm_source: Optional[str] = None,
        utm_campaign: Optional[str] = None,
        utm_content: Optional[str] = None
    ) -> Optional[SourceStats]:
        """Получить статистику по конкретному источнику."""
        key = self._get_source_key(utm_source, utm_campaign, utm_content)
        return self._stats.get(key)


# Глобальный экземпляр
analytics_service = AnalyticsService()
