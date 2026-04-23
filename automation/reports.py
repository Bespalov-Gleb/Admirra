from sqlalchemy.orm import Session
from core import models
from sqlalchemy import func, extract
from datetime import date, timedelta
import logging

logger = logging.getLogger(__name__)

def generate_weekly_report(db: Session, client_id: str, target_date: date):
    """
    Generates a weekly report for the week containing target_date.
    Week starts on Monday.
    """
    start_of_week = target_date - timedelta(days=target_date.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    # Aggregate Yandex stats
    yandex_summary = db.query(
        func.sum(models.YandexStats.cost).label("cost"),
        func.sum(models.YandexStats.clicks).label("clicks"),
        func.sum(models.YandexStats.conversions).label("conversions")
    ).filter(
        models.YandexStats.client_id == client_id,
        models.YandexStats.date >= start_of_week,
        models.YandexStats.date <= end_of_week
    ).first()

    # Aggregate VK stats
    vk_summary = db.query(
        func.sum(models.VKStats.cost).label("cost"),
        func.sum(models.VKStats.clicks).label("clicks"),
        func.sum(models.VKStats.conversions).label("conversions")
    ).filter(
        models.VKStats.client_id == client_id,
        models.VKStats.date >= start_of_week,
        models.VKStats.date <= end_of_week
    ).first()

    total_cost = float((yandex_summary.cost or 0) + (vk_summary.cost or 0))
    total_clicks = int((yandex_summary.clicks or 0) + (vk_summary.clicks or 0))
    total_convs = int((yandex_summary.conversions or 0) + (vk_summary.conversions or 0))

    avg_cpc = total_cost / total_clicks if total_clicks > 0 else 0
    avg_cpa = total_cost / total_convs if total_convs > 0 else 0

    # Save or update report
    report = db.query(models.WeeklyReport).filter_by(
        client_id=client_id, 
        week_start=start_of_week
    ).first()

    if report:
        report.total_cost = total_cost
        report.total_clicks = total_clicks
        report.total_conversions = total_convs
        report.avg_cpc = avg_cpc
        report.avg_cpa = avg_cpa
    else:
        db.add(models.WeeklyReport(
            client_id=client_id,
            week_start=start_of_week,
            week_end=end_of_week,
            total_cost=total_cost,
            total_clicks=total_clicks,
            total_conversions=total_convs,
            avg_cpc=avg_cpc,
            avg_cpa=avg_cpa
        ))
    db.commit()

def generate_monthly_report(db: Session, client_id: str, year: int, month: int):
    """
    Generates a monthly report for the specified month and year.
    """
    # Aggregate data for the month
    yandex_summary = db.query(
        func.sum(models.YandexStats.cost).label("cost"),
        func.sum(models.YandexStats.clicks).label("clicks"),
        func.sum(models.YandexStats.conversions).label("conversions")
    ).filter(
        models.YandexStats.client_id == client_id,
        extract('year', models.YandexStats.date) == year,
        extract('month', models.YandexStats.date) == month
    ).first()

    vk_summary = db.query(
        func.sum(models.VKStats.cost).label("cost"),
        func.sum(models.VKStats.clicks).label("clicks"),
        func.sum(models.VKStats.conversions).label("conversions")
    ).filter(
        models.VKStats.client_id == client_id,
        extract('year', models.VKStats.date) == year,
        extract('month', models.VKStats.date) == month
    ).first()

    total_cost = float((yandex_summary.cost or 0) + (vk_summary.cost or 0))
    total_clicks = int((yandex_summary.clicks or 0) + (vk_summary.clicks or 0))
    total_convs = int((yandex_summary.conversions or 0) + (vk_summary.conversions or 0))

    avg_cpc = total_cost / total_clicks if total_clicks > 0 else 0
    avg_cpa = total_cost / total_convs if total_convs > 0 else 0

    # Save or update report
    report = db.query(models.MonthlyReport).filter_by(
        client_id=client_id, 
        month=month,
        year=year
    ).first()

    if report:
        report.total_cost = total_cost
        report.total_clicks = total_clicks
        report.total_conversions = total_convs
        report.avg_cpc = avg_cpc
        report.avg_cpa = avg_cpa
    else:
        db.add(models.MonthlyReport(
            client_id=client_id,
            month=month,
            year=year,
            total_cost=total_cost,
            total_clicks=total_clicks,
            total_conversions=total_convs,
            avg_cpc=avg_cpc,
            avg_cpa=avg_cpa
        ))
    db.commit()
