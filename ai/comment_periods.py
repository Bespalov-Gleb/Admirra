"""Стандартные периоды AI-комментария к дашборду (ТЗ §12, раздел 6).

Комментарий кэшируется по трём стандартным периодам, которые пересчитываются
на суточной синхронизации и переключаются мгновенно. Произвольные диапазоны
дат не кэшируются — для них фронт показывает кнопку «Рассчитать».
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Dict, Optional, Tuple

# МСК = UTC+3 (без переходов на летнее время)
_MSK = timezone(timedelta(hours=3))

# Человеко-читаемые названия периодов для меты
PERIOD_LABELS = {
    "this_week": "эта неделя",
    "this_month": "этот месяц",
    "last_7_days": "последние 7 дней",
}


def _today_msk() -> date:
    return datetime.now(_MSK).date()


def standard_periods(today: Optional[date] = None) -> Dict[str, Tuple[date, date]]:
    """Границы трёх стандартных периодов на заданную дату (по умолчанию — сегодня МСК)."""
    d = today or _today_msk()
    monday = d - timedelta(days=d.weekday())
    first_of_month = d.replace(day=1)
    return {
        "this_week": (monday, d),
        "this_month": (first_of_month, d),
        "last_7_days": (d - timedelta(days=6), d),
    }


def _as_date(value) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None


def period_key_for(start, end, today: Optional[date] = None) -> Optional[str]:
    """Ключ стандартного периода для диапазона (start, end) или None для произвольного."""
    s, e = _as_date(start), _as_date(end)
    if s is None or e is None:
        return None
    for key, (ps, pe) in standard_periods(today).items():
        if s == ps and e == pe:
            return key
    return None
