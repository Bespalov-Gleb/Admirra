"""
Генерация недельных/месячных отчётов «Таблицы истории» (WeeklyReport /
MonthlyReport → выгрузка в Google Sheets).

Принцип ТЗ «Динамика»: один движок — две поверхности. Числа в истории обязаны
совпадать с дашбордом и экраном «Динамика», поэтому агрегируем периоды через
ту же модель, что и дашборд (StatsService.aggregate_summary: расход с Avito,
лиды из Метрики по выбранным целям, cost_by_platform), а НЕ через старую
упрощённую агрегацию по YandexStats/VKStats.

Расход храним «как есть» (без НДС) — это база движка; НДС накручивается на
поверхностях отображения. Только чтение из витрины фактов, к API не ходим.
"""

import calendar
import logging
from datetime import date, timedelta

from sqlalchemy.orm import Session

from core import models

logger = logging.getLogger(__name__)


def _period_summary(db: Session, client_id, d_start: date, d_end: date) -> dict:
    """Агрегат периода через единый движок дашборда (все каналы)."""
    # Ленивый импорт: reports.py подгружается из sync.py на старте — избегаем
    # любых рисков порядка импорта backend_api ↔ automation.
    from backend_api.stats_service import StatsService

    summary = StatsService.aggregate_summary(db, [client_id], d_start, d_end, "all")
    cost = float(summary.get("expenses") or 0)
    clicks = int(summary.get("clicks") or 0)
    convs = int(summary.get("leads") or 0)
    return {
        "total_cost": cost,
        "total_clicks": clicks,
        "total_conversions": convs,
        # CPC/CPA берём из движка — гарантия идентичности с дашбордом.
        "avg_cpc": float(summary.get("cpc") or 0),
        "avg_cpa": float(summary.get("cpa") or 0),
    }


def generate_weekly_report(db: Session, client_id: str, target_date: date):
    """
    Generates a weekly report for the week containing target_date.
    Week starts on Monday. Numbers come from the shared dashboard engine.
    """
    start_of_week = target_date - timedelta(days=target_date.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    vals = _period_summary(db, client_id, start_of_week, end_of_week)

    report = db.query(models.WeeklyReport).filter_by(
        client_id=client_id,
        week_start=start_of_week
    ).first()

    if report:
        report.total_cost = vals["total_cost"]
        report.total_clicks = vals["total_clicks"]
        report.total_conversions = vals["total_conversions"]
        report.avg_cpc = vals["avg_cpc"]
        report.avg_cpa = vals["avg_cpa"]
    else:
        db.add(models.WeeklyReport(
            client_id=client_id,
            week_start=start_of_week,
            week_end=end_of_week,
            total_cost=vals["total_cost"],
            total_clicks=vals["total_clicks"],
            total_conversions=vals["total_conversions"],
            avg_cpc=vals["avg_cpc"],
            avg_cpa=vals["avg_cpa"],
        ))
    db.commit()


def generate_monthly_report(db: Session, client_id: str, year: int, month: int):
    """
    Generates a monthly report for the specified month and year.
    Numbers come from the shared dashboard engine (calendar month).
    """
    start_of_month = date(year, month, 1)
    end_of_month = date(year, month, calendar.monthrange(year, month)[1])

    vals = _period_summary(db, client_id, start_of_month, end_of_month)

    report = db.query(models.MonthlyReport).filter_by(
        client_id=client_id,
        month=month,
        year=year
    ).first()

    if report:
        report.total_cost = vals["total_cost"]
        report.total_clicks = vals["total_clicks"]
        report.total_conversions = vals["total_conversions"]
        report.avg_cpc = vals["avg_cpc"]
        report.avg_cpa = vals["avg_cpa"]
    else:
        db.add(models.MonthlyReport(
            client_id=client_id,
            month=month,
            year=year,
            total_cost=vals["total_cost"],
            total_clicks=vals["total_clicks"],
            total_conversions=vals["total_conversions"],
            avg_cpc=vals["avg_cpc"],
            avg_cpa=vals["avg_cpa"],
        ))
    db.commit()
