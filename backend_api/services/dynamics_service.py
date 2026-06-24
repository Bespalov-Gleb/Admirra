"""
Сервис экрана «Динамика» — продольный ряд периодов (месяцы / недели ПН–ВС)
с дельтами к предыдущему периоду.

Принцип ТЗ: «один движок, две поверхности». Числа обязаны совпадать с дашбордом
и «Таблицей истории», поэтому агрегацию периода берём из той же модели, что и
дашборд (StatsService.aggregate_summary — Метрика-лиды, cost_by_platform, мультицель),
а НЕ из старого упрощённого reports.py.

Только чтение из витрины фактов; к API площадок не обращаемся (бэкафилл — отдельно).
"""

from __future__ import annotations

import calendar
import uuid
from datetime import date, timedelta
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from core import models
from backend_api.stats_service import StatsService

_RU_MONTHS = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]
_RU_MONTHS_NOM = [
    "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]


def _month_buckets(d_from: date, d_to: date):
    """Календарные месяцы, пересекающие [d_from, d_to]. Период = полный месяц."""
    y, m = d_from.year, d_from.month
    while (y, m) <= (d_to.year, d_to.month):
        start = date(y, m, 1)
        end = date(y, m, calendar.monthrange(y, m)[1])
        yield start, end, f"{_RU_MONTHS_NOM[m]} {y}"
        m += 1
        if m > 12:
            m = 1
            y += 1


def _week_buckets(d_from: date, d_to: date):
    """Недели ПН–ВС, пересекающие [d_from, d_to]. Период = полная неделя."""
    cur = d_from - timedelta(days=d_from.weekday())  # ближайший понедельник <= d_from
    while cur <= d_to:
        end = cur + timedelta(days=6)
        label = f"{cur.day} {_RU_MONTHS[cur.month][:3]} – {end.day} {_RU_MONTHS[end.month][:3]}"
        yield cur, end, label
        cur += timedelta(days=7)


def _pct_delta(curr: float, prev: float) -> Optional[float]:
    curr = float(curr or 0)
    prev = float(prev or 0)
    if prev == 0:
        return None  # нет базы для сравнения
    return round((curr - prev) / prev * 100, 1)


def get_dynamics_series(
    db: Session,
    client_ids: List[uuid.UUID],
    d_from: date,
    d_to: date,
    platform: str = "all",
    campaign_ids: Optional[List[uuid.UUID]] = None,
    granularity: str = "month",
) -> dict:
    if not client_ids:
        return {"granularity": granularity, "goals": [], "periods": []}

    today = date.today()
    buckets = list(
        _week_buckets(d_from, d_to) if granularity == "week" else _month_buckets(d_from, d_to)
    )

    # Динамический набор целевых колонок: выбранные цели Метрики проекта + их имена.
    selected_goal_ids = [
        str(g) for g in StatsService.get_selected_metrika_goal_ids(db, client_ids, platform)
    ]
    goal_names: dict = {}
    if selected_goal_ids:
        for gid, gname in (
            db.query(models.MetrikaGoals.goal_id, models.MetrikaGoals.goal_name)
            .filter(
                models.MetrikaGoals.client_id.in_(client_ids),
                models.MetrikaGoals.goal_id.in_(selected_goal_ids),
            )
            .distinct()
            .all()
        ):
            if gid and gid not in goal_names and gname:
                goal_names[str(gid)] = gname
    goals_meta = [{"id": gid, "name": goal_names.get(gid, gid)} for gid in selected_goal_ids]

    periods = []
    for start, end, label in buckets:
        summary = StatsService.aggregate_summary(
            db, client_ids, start, end, platform, campaign_ids
        )
        cost = float(summary.get("expenses") or 0)
        clicks = int(summary.get("clicks") or 0)
        impressions = int(summary.get("impressions") or 0)
        cost_by_platform = summary.get("cost_by_platform") or {}

        # Лиды по каждой выбранной цели за период (из MetrikaGoals).
        goal_counts: dict = {}
        if selected_goal_ids:
            rows = (
                db.query(
                    models.MetrikaGoals.goal_id,
                    func.sum(models.MetrikaGoals.conversion_count).label("cnt"),
                )
                .filter(
                    models.MetrikaGoals.client_id.in_(client_ids),
                    models.MetrikaGoals.goal_id.in_(selected_goal_ids),
                    models.MetrikaGoals.date >= start,
                    models.MetrikaGoals.date <= end,
                )
                .group_by(models.MetrikaGoals.goal_id)
                .all()
            )
            goal_counts = {str(gid): int(cnt or 0) for gid, cnt in rows}

        goals = {}
        for gid in selected_goal_ids:
            cnt = goal_counts.get(gid, 0)
            goals[gid] = {
                "count": cnt,
                # CPA цели = расход периода ÷ конверсии этой цели (сколько платим за это действие).
                "cpa": round(cost / cnt, 2) if cnt > 0 else None,
            }

        # Сводная Яндекса: все конверсии Яндекса + общий CPL (только для Яндекса).
        yandex_cost = float(cost_by_platform.get("yandex") or 0)
        yandex_convs = int(summary.get("leads") or 0) if platform == "yandex" else None
        yandex_summary = None
        if platform in ("yandex", "all") and yandex_cost > 0:
            y_sum = (
                summary if platform == "yandex"
                else StatsService.aggregate_summary(db, client_ids, start, end, "yandex", campaign_ids)
            )
            yconv = int(y_sum.get("leads") or 0)
            yandex_summary = {
                "conversions": yconv,
                "cpl": round(yandex_cost / yconv, 2) if yconv > 0 else None,
            }

        periods.append({
            "label": label,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "incomplete": end >= today,  # текущий период ещё не завершён
            "cost": round(cost, 2),
            "impressions": impressions,
            "clicks": clicks,
            "ctr": round(clicks / impressions * 100, 2) if impressions > 0 else 0,
            "cpc": round(cost / clicks, 2) if clicks > 0 else 0,
            "leads": int(summary.get("leads") or 0),
            "cost_by_platform": {
                "yandex": round(float(cost_by_platform.get("yandex") or 0), 2),
                "vk": round(float(cost_by_platform.get("vk") or 0), 2),
                "avito": round(float(cost_by_platform.get("avito") or 0), 2),
            },
            "goals": goals,
            "yandex_summary": yandex_summary,
        })

    # Дельты к предыдущему периоду ряда (предрасчёт на бэке).
    for i, p in enumerate(periods):
        prev = periods[i - 1] if i > 0 else None
        p["deltas"] = {} if not prev else {
            "cost": _pct_delta(p["cost"], prev["cost"]),
            "impressions": _pct_delta(p["impressions"], prev["impressions"]),
            "clicks": _pct_delta(p["clicks"], prev["clicks"]),
            "ctr": _pct_delta(p["ctr"], prev["ctr"]),
            "cpc": _pct_delta(p["cpc"], prev["cpc"]),
            "leads": _pct_delta(p["leads"], prev["leads"]),
        }
        p["goal_deltas"] = {}
        if prev:
            for gid in selected_goal_ids:
                p["goal_deltas"][gid] = {
                    "count": _pct_delta(p["goals"][gid]["count"], prev["goals"][gid]["count"]),
                    "cpa": _pct_delta(p["goals"][gid]["cpa"] or 0, prev["goals"][gid]["cpa"] or 0),
                }

    return {"granularity": granularity, "goals": goals_meta, "periods": periods}
