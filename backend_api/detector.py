import uuid
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, case, or_
from sqlalchemy.orm import Session

from core.database import get_db
from core import models, schemas, security
from backend_api.access_control import get_accessible_client_ids, assert_project_access, get_team_context
from backend_api.services.project_settings import get_detector_state

router = APIRouter(prefix="/detector", tags=["Detector"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _assert_detector_access(db: Session, user: models.User, client_id: uuid.UUID, *, write: bool = False) -> None:
    """Detector information is an agency-only workspace, never client-facing."""
    context = assert_project_access(db, user, client_id, write=write)
    if context.team_role == models.TeamMemberRole.CLIENT.value:
        raise HTTPException(status_code=403, detail="Детектор доступен только команде агентства")


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
        "meta": alert.meta,
    }


def _plan_status(db: Session, client_id: uuid.UUID, today) -> str:
    from backend_api.services.detector_iteration3 import _latest_budgets, _latest_targets
    budgets = _latest_budgets(db, client_id, today)
    targets = _latest_targets(db, client_id, today)
    active_budget_channels = {
        channel for channel, row in budgets.items()
        if row and float(row.amount or 0) > 0 and channel is not None
    }
    active_target_channels = {
        row.channel for row in targets
        if row.channel is not None and row.control_enabled and float(row.target_cpa or 0) > 0
    }
    # A project-wide budget (channel=None) covers whichever channels hold a
    # target CPL; alone it is a budget without a CPL — «дозаполните».
    total_budget = budgets.get(None)
    if total_budget and float(total_budget.amount or 0) > 0:
        active_budget_channels |= active_target_channels or {"__total__"}
    if active_budget_channels or active_target_channels:
        return "configured" if active_budget_channels == active_target_channels else "incomplete"
    latest_end = (
        db.query(models.ProjectBudget.period_end)
        .filter(models.ProjectBudget.client_id == client_id)
        .order_by(models.ProjectBudget.period_end.desc())
        .first()
    )
    return "expired" if latest_end and latest_end[0] < today else "missing"


def _effective_onboarding_dismissed(db: Session, client: models.Client, today) -> datetime | None:
    """§6: a new plan period finishing without a follow-up plan resurrects the
    onboarding banner regardless of an earlier dismissal."""
    until = getattr(client, "detector_onboarding_dismissed_until", None)
    if not until:
        return None
    from core.config import get_config
    dismissed_at = until - timedelta(days=get_config().detector.onboarding_dismiss_days)
    period_ended_after_dismiss = (
        db.query(models.ProjectBudget.id)
        .filter(
            models.ProjectBudget.client_id == client.id,
            models.ProjectBudget.period_end < today,
            models.ProjectBudget.period_end >= dismissed_at.date(),
        )
        .first()
    )
    if period_ended_after_dismiss:
        return None
    return until


def _plan_completion_pct(db: Session, client_id: uuid.UUID, plan_status: str, today) -> float | None:
    if plan_status != "expired":
        return None
    from backend_api.services.detector_iteration3 import plan_completion
    try:
        completion = plan_completion(db, client_id, today)
        return float(completion["pct"]) if completion else None
    except Exception:
        return None


@router.get("/{client_id}/summary", response_model=schemas.DetectorSummaryResponse)
def get_detector_summary(
    client_id: uuid.UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    _assert_detector_access(db, current_user, client_id, write=False)
    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Проект не найден")

    # TZ 1.12: account-level global toggle — check project owner's setting
    owner = db.query(models.User).filter(models.User.id == client.owner_id).first()
    global_on = getattr(owner, "global_detector_enabled", True) if owner else True

    det_state = get_detector_state(client)
    warmup_status = det_state["status"] if global_on else "disabled"
    if warmup_status in {"disabled", "paused"}:
        today = _now().date()
        plan_status = _plan_status(db, client_id, today)
        return {
            "warning_count": 0,
            "problem_count": 0,
            "max_severity": None,
            "warmup_status": warmup_status,
            "warmup_days_left": None,
            "hidden_count": 0,
            "alerts": [],
            "hidden_alerts": [],
            "plan_status": plan_status,
            "plan_completion_pct": _plan_completion_pct(db, client_id, plan_status, today),
            "sync_issues": [],
            "onboarding_dismissed_until": _effective_onboarding_dismissed(db, client, today),
        }

    now = _now()
    from backend_api.services.detector_iteration3 import sync_issues_for_client
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
        warmup_days_left = max(0, int(det_state.get("warmup_days") or 7) - det_state["days_since_start"])

    plan_status = _plan_status(db, client_id, now.date())
    return {
        "warning_count": warning_count,
        "problem_count": problem_count,
        "hidden_count": len(hidden_alerts),
        "max_severity": max_severity,
        "warmup_status": warmup_status,
        "warmup_days_left": warmup_days_left,
        "alerts": [_alert_to_response(a, now) for a in alerts],
        "hidden_alerts": [_alert_to_response(a, now) for a in hidden_alerts],
        "plan_status": plan_status,
        "plan_completion_pct": _plan_completion_pct(db, client_id, plan_status, now.date()),
        "sync_issues": sync_issues_for_client(db, client_id, now.date()),
        "onboarding_dismissed_until": _effective_onboarding_dismissed(db, client, now.date()),
    }


@router.get("/{client_id}/alerts", response_model=List[schemas.DetectorAlertResponse])
def get_detector_alerts(
    client_id: uuid.UUID,
    status: Optional[str] = None,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    _assert_detector_access(db, current_user, client_id, write=False)

    now = _now()
    q = db.query(models.DetectorAlert).filter(models.DetectorAlert.client_id == client_id)
    if status:
        q = q.filter(models.DetectorAlert.status == status)
    else:
        q = q.filter(models.DetectorAlert.status.in_(["open", "dismissed"]))

    return [_alert_to_response(a, now) for a in q.order_by(models.DetectorAlert.opened_at.desc()).limit(50).all()]


@router.get("/{client_id}/campaign-highlights")
def get_campaign_highlights(
    client_id: uuid.UUID,
    start_date: str,
    end_date: str,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    _assert_detector_access(db, current_user, client_id, write=False)
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Даты должны быть в формате YYYY-MM-DD")
    if end < start:
        raise HTTPException(status_code=400, detail="Дата окончания не может быть раньше даты начала")
    from backend_api.services.detector_iteration3 import campaign_highlights
    return {"items": campaign_highlights(db, client_id, start, end)}


@router.post("/alerts/{alert_id}/dismiss")
def dismiss_alert(
    alert_id: uuid.UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    alert = db.query(models.DetectorAlert).filter(models.DetectorAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Алерт не найден")

    _assert_detector_access(db, current_user, alert.client_id, write=True)

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
    _assert_detector_access(db, current_user, alert.client_id, write=True)
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
    _assert_detector_access(db, current_user, alert.client_id, write=True)
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
    _assert_detector_access(db, current_user, alert.client_id, write=True)
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


@router.post("/{client_id}/onboarding/dismiss")
def dismiss_plan_onboarding(
    client_id: uuid.UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """Hide the plan onboarding for its configured, finite period."""
    _assert_detector_access(db, current_user, client_id, write=True)
    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Проект не найден")
    from core.config import get_config
    from backend_api.services.history import log_history_event
    client.detector_onboarding_dismissed_until = _now() + timedelta(days=get_config().detector.onboarding_dismiss_days)
    # §8: показы/скрытия/клики плашки — метрика успеха итерации.
    log_history_event(
        db,
        actor=current_user,
        event_type="detector",
        action="plan_onboarding_dismissed",
        description="Плашка «Задайте план» скрыта",
        client_id=client_id,
        target_type="plan_onboarding",
    )
    db.commit()
    return {"dismissed_until": client.detector_onboarding_dismissed_until}


@router.post("/{client_id}/onboarding/event")
def track_plan_onboarding_event(
    client_id: uuid.UUID,
    body: dict,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """§8: аналитика плашки «Задайте план» — показы и клики CTA.

    Заполнение плана после клика ловится существующими событиями history
    от PUT /budgets и /target-cpa: воронка собирается по client_id.
    """
    _assert_detector_access(db, current_user, client_id, write=False)
    event = str((body or {}).get("event") or "").strip().lower()
    if event not in ("shown", "clicked"):
        raise HTTPException(status_code=422, detail="event должен быть shown или clicked")
    from backend_api.services.history import log_history_event
    log_history_event(
        db,
        actor=current_user,
        event_type="detector",
        action=f"plan_onboarding_{event}",
        description="Плашка «Задайте план» показана" if event == "shown" else "Клик по CTA «Задать план»",
        client_id=client_id,
        target_type="plan_onboarding",
        meta={"plan_status": _plan_status(db, client_id, _now().date())},
    )
    db.commit()
    return {"ok": True}


@router.get("/cross-project", response_model=List[schemas.DetectorCrossProjectItem])
def get_cross_project_status(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    if get_team_context(db, current_user).team_role == models.TeamMemberRole.CLIENT.value:
        return []
    accessible_ids = get_accessible_client_ids(db, current_user)
    if not accessible_ids:
        return []

    now = _now()
    from backend_api.services.detector_iteration3 import sync_issues_for_client
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
        if status in {"disabled", "paused"}:
            result.append({
                "project_id": client.id,
                "warning_count": 0,
                "problem_count": 0,
                "hidden_count": 0,
                "max_severity": None,
                "warmup_status": status,
                "plan_status": _plan_status(db, client.id, now.date()),
                "sync_issue_count": 0,
            })
            continue

        project_alerts = by_project.get(client.id, [])
        w = sum(1 for a in project_alerts if a.severity == "warning")
        p = sum(1 for a in project_alerts if a.severity == "problem")
        max_sev = "problem" if p > 0 else ("warning" if w > 0 else None)
        # Поповер-превью (ТЗ ит.2, п.2.4): топ-3 короткими фразами, красные сверху
        top = sorted(
            project_alerts,
            key=lambda a: (0 if a.severity == "problem" else 1, -(a.consecutive_days or 0)),
        )[:3]
        result.append({
            "project_id": client.id,
            "warning_count": w,
            "problem_count": p,
            "hidden_count": len(hidden_by_project.get(client.id, [])),
            "max_severity": max_sev,
            "warmup_status": status,
            "plan_status": _plan_status(db, client.id, now.date()),
            "sync_issue_count": len(sync_issues_for_client(db, client.id, now.date())),
            "top_alerts": [
                {
                    "id": a.id,
                    "severity": a.severity,
                    "hypothesis_text": a.hypothesis_text,
                    "metric": a.metric,
                    "checks": list((a.meta or {}).get("checks") or []),
                }
                for a in top
            ],
        })

    return result
