"""The legacy attribution lookback, shared by legacy and durable collection."""
from datetime import datetime, timedelta
import os


def goal_window(date_from, date_to, *, first_sync):
    start = datetime.strptime(date_from, "%Y-%m-%d").date()
    end = datetime.strptime(date_to, "%Y-%m-%d").date()
    if start > end:
        raise ValueError("Invalid Metrika date window")
    if first_sync:
        start = end - timedelta(days=89)
    try:
        lookback = int(os.getenv("METRIKA_GOALS_LOOKBACK_DAYS", "30"))
        start = min(start, end - timedelta(days=lookback))
    except (ValueError, OverflowError):
        pass  # Preserve legacy behavior for malformed optional lookback.
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]
