"""Best-effort visit memory: never wait behind sync/report source locks."""
from datetime import datetime, timedelta, timezone
from core import models


def record_visit(db, client_id, start, end, platform, result):
    # Caller has authorized the project. A concurrent writer owns the latest
    # state; skip this optional sample rather than making the dashboard wait.
    client = (db.query(models.Client).filter(models.Client.id == client_id)
              .populate_existing().with_for_update(skip_locked=True).first())
    if client is None:
        db.rollback()
        return False
    now = datetime.now(timezone.utc)
    previous_view = client.last_dashboard_viewed_at
    if previous_view and previous_view.tzinfo is None:
        previous_view = previous_view.replace(tzinfo=timezone.utc)
    stored = client.last_dashboard_snapshot if isinstance(client.last_dashboard_snapshot, dict) else {}
    current = {
        "calculation_version": result.get("calculation_version"), "captured_at": now.isoformat(),
        "period_from": start.isoformat(), "period_to": end.isoformat(), "platform": platform or "all",
        "expenses": float(result.get("expenses") or 0), "leads": int(result.get("leads") or 0),
        "clicks": int(result.get("clicks") or 0), "impressions": int(result.get("impressions") or 0),
        "cpl": float(result.get("cpa") or 0),
    }
    previous = stored.get("current" if previous_view is None or now - previous_view >= timedelta(minutes=30)
                          else "previous")
    client.last_dashboard_snapshot = {"previous": previous, "current": current}
    if previous_view is None or now - previous_view >= timedelta(minutes=5):
        client.last_dashboard_viewed_at = now
    db.commit()
    return True
