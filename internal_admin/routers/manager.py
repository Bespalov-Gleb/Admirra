"""Панель менеджера: /api/manager/* (ТЗ v1.0 — все клиенты, без закрепления)."""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.database import get_db
from core import models
from internal_admin.deps import require_manager, get_current_staff
from internal_admin.models import SupportNote
from internal_admin.rbac import STAFF_ROLES, is_superadmin, staff_role_label
from internal_admin.schemas import ImpersonateResponse, SupportNoteCreate, SupportNoteResponse
from internal_admin.services.impersonate import impersonate_saas_user
from internal_admin.services import write_audit
from internal_admin.services.saas_users import list_saas_users, manager_dashboard_summary
from internal_admin.services.user_helpers import serialize_saas_user
from backend_api.services.subscription import SubscriptionService

router = APIRouter(tags=["Internal Manager"])


class BlockUserBody(BaseModel):
    reason: str = Field(..., min_length=1, max_length=2000)


@router.get("/dashboard/summary")
def manager_summary(staff=Depends(require_manager), db: Session = Depends(get_db)):
    if is_superadmin(staff):
        raise HTTPException(status_code=403, detail="Use /api/admin/dashboard for superadmin")
    return manager_dashboard_summary(db)


@router.get("/users")
def manager_list_users(
    search: str | None = None,
    plan: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=200),
    staff=Depends(require_manager),
    db: Session = Depends(get_db),
):
    offset = (page - 1) * limit
    items, total = list_saas_users(db, search=search, plan_code=plan, status=status, limit=limit, offset=offset)
    return {"items": items, "total": total, "page": page, "limit": limit}


@router.get("/users/{user_id}")
def manager_user_card(
    user_id: UUID,
    history_limit: int = Query(20, ge=1, le=200),
    staff=Depends(require_manager),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == user_id, models.User.role == models.UserRole.MANAGER).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    integrations = (
        db.query(models.Integration)
        .join(models.Client, models.Client.id == models.Integration.client_id)
        .filter(models.Client.owner_id == user.id)
        .all()
    )
    history = (
        db.query(models.HistoryEvent)
        .filter(models.HistoryEvent.account_id == user.id)
        .order_by(models.HistoryEvent.created_at.desc())
        .limit(history_limit)
        .all()
    )
    notes = (
        db.query(SupportNote)
        .filter(SupportNote.client_user_id == user_id)
        .order_by(SupportNote.created_at.desc())
        .limit(50)
        .all()
    )
    return {
        "user": serialize_saas_user(db, user),
        "integrations": [
            {
                "platform": i.platform.value,
                "account_id": i.account_id,
                "sync_status": i.sync_status.value if i.sync_status else None,
                "last_sync_at": i.last_sync_at,
                "error_message": i.error_message,
            }
            for i in integrations
        ],
        "history": [
            {
                "created_at": h.created_at,
                "description": h.description,
                "event_type": h.event_type,
                "action": h.action,
            }
            for h in history
        ],
        "notes": [
            {
                "id": str(n.id),
                "body": n.body,
                "author_email": db.query(models.User.email).filter(models.User.id == n.author_user_id).scalar(),
                "created_at": n.created_at,
                "can_edit": n.author_user_id == staff.id
                and (datetime.now(timezone.utc) - n.created_at).total_seconds() < 3600,
            }
            for n in notes
        ],
    }


@router.get("/users/{user_id}/notes")
def manager_list_notes(user_id: UUID, staff=Depends(require_manager), db: Session = Depends(get_db)):
    notes = (
        db.query(SupportNote)
        .filter(SupportNote.client_user_id == user_id)
        .order_by(SupportNote.created_at.desc())
        .all()
    )
    return {
        "items": [
            {
                "id": str(n.id),
                "body": n.body,
                "author_email": db.query(models.User.email).filter(models.User.id == n.author_user_id).scalar(),
                "created_at": n.created_at,
            }
            for n in notes
        ]
    }


@router.post("/users/{user_id}/notes", response_model=SupportNoteResponse)
def manager_add_note(
    user_id: UUID,
    body: SupportNoteCreate,
    staff=Depends(require_manager),
    db: Session = Depends(get_db),
):
    note = SupportNote(client_user_id=user_id, author_user_id=staff.id, body=body.body.strip())
    db.add(note)
    db.commit()
    db.refresh(note)
    return SupportNoteResponse(id=note.id, body=note.body, author_email=staff.email, created_at=note.created_at)


@router.patch("/notes/{note_id}")
def manager_edit_note(
    note_id: UUID,
    body: SupportNoteCreate,
    staff=Depends(require_manager),
    db: Session = Depends(get_db),
):
    note = db.query(SupportNote).filter(SupportNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if note.author_user_id != staff.id:
        raise HTTPException(status_code=403, detail="Cannot edit another author's note")
    age = (datetime.now(timezone.utc) - note.created_at).total_seconds()
    if age > 3600:
        raise HTTPException(status_code=403, detail="Edit window expired (1 hour)")
    note.body = body.body.strip()
    db.commit()
    return {"ok": True}


@router.get("/users/{user_id}/activity")
def manager_user_activity(
    user_id: UUID,
    limit: int = Query(20, ge=1, le=200),
    staff=Depends(require_manager),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(models.HistoryEvent)
        .filter(models.HistoryEvent.account_id == user_id)
        .order_by(models.HistoryEvent.created_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "items": [
            {
                "created_at": h.created_at,
                "event_type": h.event_type,
                "action": h.action,
                "description": h.description,
            }
            for h in rows
        ]
    }


@router.post("/users/{user_id}/impersonate", response_model=ImpersonateResponse)
def manager_impersonate(
    user_id: str,
    request: Request,
    staff=Depends(require_manager),
    db: Session = Depends(get_db),
):
    if is_superadmin(staff):
        raise HTTPException(status_code=403, detail="Use /api/admin/auth/users/{id}/impersonate")
    return impersonate_saas_user(request=request, staff=staff, db=db, target_user_id=user_id)


@router.post("/users/{user_id}/reset-sessions")
def manager_reset_sessions(user_id: UUID, staff=Depends(require_manager), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    write_audit(
        db,
        staff=staff,
        action="user_sessions_reset",
        target_type="user",
        target_id=str(user_id),
        description="Сброс сессий пользователя",
    )
    db.commit()
    return {"ok": True, "note": "Session revoke for SaaS JWT is app-level; audit logged"}


@router.post("/users/{user_id}/block")
def manager_block_user(
    user_id: UUID,
    body: BlockUserBody,
    staff=Depends(require_manager),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    user.block_reason = body.reason.strip()
    write_audit(db, staff=staff, action="user_blocked", target_type="user", target_id=str(user_id), meta={"reason": body.reason})
    db.commit()
    return {"ok": True}


@router.get("/events")
def manager_global_events(
    period: str | None = None,
    event_type: str | None = None,
    search: str | None = None,
    user_id: UUID | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    staff=Depends(require_manager),
    db: Session = Depends(get_db),
):
    from datetime import timedelta

    days = {"today": 1, "yesterday": 2, "week": 7, "month": 30}.get(period or "week", 7)
    dt_from = datetime.now(timezone.utc) - timedelta(days=days)
    query = db.query(models.HistoryEvent).filter(models.HistoryEvent.created_at >= dt_from)
    if event_type:
        query = query.filter(models.HistoryEvent.event_type == event_type)
    if user_id:
        query = query.filter(models.HistoryEvent.account_id == user_id)
    if search:
        from sqlalchemy import func

        like = f"%{search.strip().lower()}%"
        query = query.filter(func.lower(func.coalesce(models.HistoryEvent.description, "")).like(like))
    offset = (page - 1) * limit
    rows = query.order_by(models.HistoryEvent.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "items": [
            {
                "created_at": h.created_at,
                "user_id": str(h.account_id) if h.account_id else None,
                "event_type": h.event_type,
                "action": h.action,
                "description": h.description,
            }
            for h in rows
        ],
        "page": page,
        "limit": limit,
    }


@router.get("/staff")
def manager_staff_readonly(staff=Depends(require_manager), db: Session = Depends(get_db)):
    """ТЗ: менеджер видит список сотрудников только для просмотра."""
    if is_superadmin(staff):
        raise HTTPException(status_code=403, detail="Use /api/admin/staff")
    rows = db.query(models.User).filter(models.User.role.in_(STAFF_ROLES)).order_by(models.User.email).all()
    return {
        "items": [
            {
                "user_id": str(u.id),
                "email": u.email,
                "full_name": (u.first_name or "") + (" " + u.last_name if u.last_name else ""),
                "role": u.role.value,
                "role_label": staff_role_label(u.role),
                "status": (u.staff_status.value if u.staff_status else ("active" if u.is_active else "inactive")),
            }
            for u in rows
        ]
    }


@router.get("/integrations")
def manager_integrations_readonly(staff=Depends(require_manager), db: Session = Depends(get_db)):
    from internal_admin.routers.integrations import _build_providers

    if is_superadmin(staff):
        raise HTTPException(status_code=403, detail="Use /api/admin/integrations")
    data = _build_providers(db, include_financials=False)
    for provider in data["providers"]:
        for key in list(provider.keys()):
            if key.endswith("_masked") or key in {"balance_usd", "spend_usd_month", "alert_threshold_usd"}:
                provider.pop(key, None)
    return data


@router.get("/ai/usage")
def manager_ai_usage(
    threshold: int = Query(85, ge=1, le=100),
    staff=Depends(require_manager),
    db: Session = Depends(get_db),
):
    """Использование AI без расходов OpenAI в $ (ТЗ: менеджеру скрыты финансы)."""
    if is_superadmin(staff):
        raise HTTPException(status_code=403, detail="Use /api/admin/ai-limits")
    items = []
    for u in db.query(models.User).filter(models.User.role == models.UserRole.MANAGER).all():
        plan = SubscriptionService.get_user_plan(db, u)
        used = int(u.ai_requests_used or 0)
        limit = max(int(plan.max_ai_requests_per_period), 1)
        pct = round(used * 100 / limit, 2)
        items.append(
            {
                "user_id": str(u.id),
                "email": u.email,
                "full_name": u.first_name or u.email,
                "plan_code": plan.code,
                "used": used,
                "limit": limit,
                "used_percent": pct,
                "close_to_limit": pct >= threshold,
            }
        )
    items.sort(key=lambda x: x["used_percent"], reverse=True)
    return {
        "threshold_percent": threshold,
        "close_to_limit": [x for x in items if x["close_to_limit"]],
        "items": items,
    }
