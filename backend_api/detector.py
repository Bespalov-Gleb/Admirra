import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, case, or_
from sqlalchemy.orm import Session

from core.database import get_db
from core import models, schemas, security
from backend_api.access_control import get_accessible_client_ids, assert_project_access
from backend_api.services.project_settings import get_detector_state

router = APIRouter(prefix="/detector", tags=["Detector"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _is_snoozed(alert: models.DetectorAlert, now: datetime | None = None) -> bool:
    now = now or _now()
    until = getattr(alert, "snoozed_until", None)
    return bool(alert.status == "open" and until and until > now)


def _is_not_problem(alert: models.DetectorAlert) -> bool:
    return bool(alert.status == "dismissed" or getattr(alert, "not_problem_at", None))


def _visible_filter(now: datetime):
    return and_(
        models.DetectorAlert.status == "open",
        or_(
            models.DetectorAlert.snoozed_until.is_(None),
            models.DetectorAlert.snoozed_until <= now,
        ),
    )


def _hidden_filter(now: datetime):
    return or_(
        and_(
            models.DetectorAlert.status == "open",
            models.DetectorAlert.snoozed_until.isnot(None),
            models.DetectorAlert.snoozed_until > now,
        ),
        models.DetectorAlert.status == "dismissed",
    )


def _alert_to_response(alert: models.DetectorAlert, now: datetime | None = None) -> dict:
    now = now or _now()
    hidden_reason = None
    hidden = False
    if _is_snoozed(alert, now):
        hidden = True
        hidden_reason = "snoozed"
    elif _is_not_problem(alert):
        hidden = True
        hidden_reason = "not_problem"

    channel = alert.channel.value if getattr(alert.channel, "value", None) else alert.channel
    return {
        "id": alert.id,
        "metric": alert.metric,
        "detection_level": alert.detection_level,
        "entity_id": alert.entity_id,
        "channel": channel,
        "mode": alert.mode,
        "severity": alert.severity,
        "deviation_pct": float(alert.deviation_pct) if alert.deviation_pct is not None else None,
        "baseline_value": float(alert.baseline_value) if alert.baseline_value is not None else None,
        "actual_value": float(alert.actual_value) if alert.actual_value is not None else None,
        "consecutive_days": alert.consecutive_days or 1,
        "pattern_key": alert.pattern_key,
        "hypothesis_text": alert.hypothesis_text,
        "status": alert.status,
        "opened_at": alert.opened_at,
        "dismissed_at": alert.dismissed_at,
        "snoozed_until": getattr(alert, "snoozed_until", None),
        "not_problem_at": getattr(alert, "not_problem_at", None),
        "hidden": hidden,
        "hidden_reason": hidden_reason,
    }


@router.get("/{client_id}/summary", response_model=schemas.DetectorSummaryResponse)
def get_detector_summary(
    client_id: uuid.UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    assert_project_access(db, current_user, client_id, write=False)
    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Проект не найден")

    # TZ 1.12: account-level global toggle — check project owner's setting
    owner = db.query(models.User).filter(models.User.id == client.owner_id).first()
    global_on = getattr(owner, "global_detector_enabled", True) if owner else True

    det_state = get_detector_state(client)
    warmup_status = det_state["status"] if global_on else "disabled"
    if warmup_status == "disabled":
        return {
            "warning_count": 0,
            "problem_count": 0,
            "max_severity": None,
            "warmup_status": warmup_status,
            "warmup_days_left": None,
            "hidden_count": 0,
            "alerts": [],
            "hidden_alerts": [],
        }

    now = _now()
    alerts = (
        db.query(models.DetectorAlert)
        .filter(
            models.DetectorAlert.client_id == client_id,
            _visible_filter(now),
        )
        .order_by(
            case((models.DetectorAlert.severity == "problem", 0), else_=1),
            models.DetectorAlert.opened_at.desc(),
        )
        .all()
    )
    hidden_alerts = (
        db.query(models.DetectorAlert)
        .filter(
            models.DetectorAlert.client_id == client_id,
            _hidden_filter(now),
        )
        .order_by(
            case((models.DetectorAlert.severity == "problem", 0), else_=1),
            models.DetectorAlert.opened_at.desc(),
        )
        .all()
    )

    warning_count = sum(1 for a in alerts if a.severity == "warning")
    problem_count = sum(1 for a in alerts if a.severity == "problem")
    max_severity = "problem" if problem_count > 0 else ("warning" if warning_count > 0 else None)

    warmup_days_left = None
    if warmup_status == "warming_up" and det_state.get("days_since_start") is not None:
        from core.config import get_config
        warmup_days_left = max(0, get_config().detector.warmup_days - det_state["days_since_start"])

    return {
        "warning_count": warning_count,
        "problem_count": problem_count,
        "hidden_count": len(hidden_alerts),
        "max_severity": max_severity,
        "warmup_status": warmup_status,
        "warmup_days_left": warmup_days_left,
        "alerts": [_alert_to_response(a, now) for a in alerts],
        "hidden_alerts": [_alert_to_response(a, now) for a in hidden_alerts],
    }


@router.get("/{client_id}/alerts", response_model=List[schemas.DetectorAlertResponse])
def get_detector_alerts(
    client_id: uuid.UUID,
    status: Optional[str] = None,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    assert_project_access(db, current_user, client_id, write=False)

    now = _now()
    q = db.query(models.DetectorAlert).filter(models.DetectorAlert.client_id == client_id)
    if status:
        q = q.filter(models.DetectorAlert.status == status)
    else:
        q = q.filter(models.DetectorAlert.status.in_(["open", "dismissed"]))

    return [_alert_to_response(a, now) for a in q.order_by(models.DetectorAlert.opened_at.desc()).limit(50).all()]


@router.post("/alerts/{alert_id}/dismiss")
def dismiss_alert(
    alert_id: uuid.UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    alert = db.query(models.DetectorAlert).filter(models.DetectorAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Алерт не найден")

    assert_project_access(db, current_user, alert.client_id, write=True)

    if alert.status != "open":
        raise HTTPException(status_code=400, detail="Алерт уже закрыт или скрыт")

    alert.status = "dismissed"
    alert.dismissed_at = _now()
    alert.not_problem_at = alert.dismissed_at
    alert.snoozed_until = None
    alert.snooze_source = None
    db.commit()
    db.refresh(alert)
    return _alert_to_response(alert)


@router.post("/alerts/{alert_id}/snooze")
def snooze_alert(
    alert_id: uuid.UUID,
    body: schemas.DetectorSnoozeRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    alert = db.query(models.DetectorAlert).filter(models.DetectorAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Алерт не найден")
    assert_project_access(db, current_user, alert.client_id, write=True)
    if alert.status not in ("open", "dismissed"):
        raise HTTPException(status_code=400, detail="Алерт уже закрыт")

    days = int(body.days or 1)
    if days not in (1, 3, 7):
        raise HTTPException(status_code=400, detail="Доступны сроки 1, 3 или 7 дней")
    now = _now()
    alert.status = "open"
    alert.dismissed_at = None
    alert.not_problem_at = None
    alert.snoozed_until = now + timedelta(days=days)
    alert.snooze_source = {
        "user_id": str(current_user.id),
        "days": days,
        "at": now.isoformat(),
    }
    db.commit()
    db.refresh(alert)
    return _alert_to_response(alert)


@router.post("/alerts/{alert_id}/not-problem")
def mark_alert_not_problem(
    alert_id: uuid.UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    alert = db.query(models.DetectorAlert).filter(models.DetectorAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Алерт не найден")
    assert_project_access(db, current_user, alert.client_id, write=True)
    if alert.status == "closed":
        raise HTTPException(status_code=400, detail="Алерт уже закрыт")

    now = _now()
    alert.status = "dismissed"
    alert.dismissed_at = now
    alert.not_problem_at = now
    alert.snoozed_until = None
    alert.snooze_source = None
    alert.meta = {**(alert.meta or {}), "not_problem_by": str(current_user.id)}
    db.commit()
    db.refresh(alert)
    return _alert_to_response(alert)


@router.post("/alerts/{alert_id}/restore")
def restore_alert(
    alert_id: uuid.UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    alert = db.query(models.DetectorAlert).filter(models.DetectorAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Алерт не найден")
    assert_project_access(db, current_user, alert.client_id, write=True)
    if alert.status == "closed":
        raise HTTPException(status_code=400, detail="Алерт уже закрыт")

    alert.status = "open"
    alert.dismissed_at = None
    alert.not_problem_at = None
    alert.snoozed_until = None
    alert.snooze_source = None
    db.commit()
    db.refresh(alert)
    return _alert_to_response(alert)


@router.get("/cross-project", response_model=List[schemas.DetectorCrossProjectItem])
def get_cross_project_status(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    accessible_ids = get_accessible_client_ids(db, current_user)
    if not accessible_ids:
        return []

    now = _now()
    alerts = (
        db.query(models.DetectorAlert)
        .filter(
            models.DetectorAlert.client_id.in_(accessible_ids),
            _visible_filter(now),
        )
        .all()
    )
    hidden_alerts = (
        db.query(models.DetectorAlert)
        .filter(
            models.DetectorAlert.client_id.in_(accessible_ids),
            _hidden_filter(now),
        )
        .all()
    )

    by_project: dict[uuid.UUID, list] = {}
    for a in alerts:
        by_project.setdefault(a.client_id, []).append(a)
    hidden_by_project: dict[uuid.UUID, list] = {}
    for a in hidden_alerts:
        hidden_by_project.setdefault(a.client_id, []).append(a)

    clients = (
        db.query(models.Client)
        .filter(models.Client.id.in_(accessible_ids))
        .all()
    )

    # Load owners for global toggle check (TZ 1.12)
    owner_ids = {c.owner_id for c in clients if c.owner_id}
    owners = {
        u.id: u
        for u in db.query(models.User).filter(models.User.id.in_(owner_ids)).all()
    }

    result = []
    for client in clients:
        owner = owners.get(client.owner_id)
        global_on = getattr(owner, "global_detector_enabled", True) if owner else True
        det_state = get_detector_state(client)
        status = det_state["status"] if global_on else "disabled"
        if status == "disabled":
            result.append({
                "project_id": client.id,
                "warning_count": 0,
                "problem_count": 0,
                "hidden_count": 0,
                "max_severity": None,
                "warmup_status": "disabled",
            })
            continue

        project_alerts = by_project.get(client.id, [])
        w = sum(1 for a in project_alerts if a.severity == "warning")
        p = sum(1 for a in project_alerts if a.severity == "problem")
        max_sev = "problem" if p > 0 else ("warning" if w > 0 else None)
        result.append({
            "project_id": client.id,
            "warning_count": w,
            "problem_count": p,
            "hidden_count": len(hidden_by_project.get(client.id, [])),
            "max_severity": max_sev,
            "warmup_status": status,
        })

    return result
