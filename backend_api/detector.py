import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case
from sqlalchemy.orm import Session

from core.database import get_db
from core import models, schemas, security
from backend_api.access_control import get_accessible_client_ids, assert_project_access
from backend_api.services.project_settings import get_detector_state

router = APIRouter(prefix="/detector", tags=["Detector"])


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
            "alerts": [],
        }

    alerts = (
        db.query(models.DetectorAlert)
        .filter(
            models.DetectorAlert.client_id == client_id,
            models.DetectorAlert.status == "open",
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
        "max_severity": max_severity,
        "warmup_status": warmup_status,
        "warmup_days_left": warmup_days_left,
        "alerts": alerts,
    }


@router.get("/{client_id}/alerts", response_model=List[schemas.DetectorAlertResponse])
def get_detector_alerts(
    client_id: uuid.UUID,
    status: Optional[str] = None,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    assert_project_access(db, current_user, client_id, write=False)

    q = db.query(models.DetectorAlert).filter(models.DetectorAlert.client_id == client_id)
    if status:
        q = q.filter(models.DetectorAlert.status == status)
    else:
        q = q.filter(models.DetectorAlert.status.in_(["open", "dismissed"]))

    return q.order_by(models.DetectorAlert.opened_at.desc()).limit(50).all()


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
    alert.dismissed_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}


@router.get("/cross-project", response_model=List[schemas.DetectorCrossProjectItem])
def get_cross_project_status(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    accessible_ids = get_accessible_client_ids(db, current_user)
    if not accessible_ids:
        return []

    alerts = (
        db.query(models.DetectorAlert)
        .filter(
            models.DetectorAlert.client_id.in_(accessible_ids),
            models.DetectorAlert.status == "open",
        )
        .all()
    )

    by_project: dict[uuid.UUID, list] = {}
    for a in alerts:
        by_project.setdefault(a.client_id, []).append(a)

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
            "max_severity": max_sev,
            "warmup_status": status,
        })

    return result
