import json
from datetime import date
from core.config import get_config

_RU_HOLIDAYS = {
    date(2025, 1, 1), date(2025, 1, 2), date(2025, 1, 3), date(2025, 1, 4),
    date(2025, 1, 5), date(2025, 1, 6), date(2025, 1, 7), date(2025, 1, 8),
    date(2025, 2, 23), date(2025, 3, 8),
    date(2025, 5, 1), date(2025, 5, 9),
    date(2025, 6, 12), date(2025, 11, 4),
    date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3), date(2026, 1, 4),
    date(2026, 1, 5), date(2026, 1, 6), date(2026, 1, 7), date(2026, 1, 8),
    date(2026, 2, 23), date(2026, 3, 8),
    date(2026, 5, 1), date(2026, 5, 9),
    date(2026, 6, 12), date(2026, 11, 4),
    date(2027, 1, 1), date(2027, 1, 2), date(2027, 1, 3), date(2027, 1, 4),
    date(2027, 1, 5), date(2027, 1, 6), date(2027, 1, 7), date(2027, 1, 8),
    date(2027, 2, 23), date(2027, 3, 8),
    date(2027, 5, 1), date(2027, 5, 9),
    date(2027, 6, 12), date(2027, 11, 4),
}

_extra_cache: set[date] | None = None


def _load_extra() -> set[date]:
    global _extra_cache
    if _extra_cache is not None:
        return _extra_cache
    raw = get_config().detector.holidays_json
    if not raw:
        _extra_cache = set()
        return _extra_cache
    try:
        items = json.loads(raw)
        _extra_cache = {date.fromisoformat(d) for d in items}
    except Exception:
        _extra_cache = set()
    return _extra_cache


def is_russian_holiday(d: date) -> bool:
    return d in _RU_HOLIDAYS or d in _load_extra()


def is_near_holiday(d: date, margin: int = 1) -> bool:
    from datetime import timedelta
    for offset in range(-margin, margin + 1):
        if is_russian_holiday(d + timedelta(days=offset)):
            return True
    return False
