"""Superadmin: пользователи SaaS (ТЗ v1.0)."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.database import get_db
from core import models
from internal_admin.deps import require_superadmin
from internal_admin.schemas import BlockUserBody
from internal_admin.services import write_audit
from internal_admin.services.impersonate import impersonate_saas_user
from internal_admin.services.saas_users import list_saas_users
from internal_admin.services.user_helpers import serialize_saas_user
from internal_admin.schemas import ImpersonateResponse
from fastapi import Request

router = APIRouter(prefix="/users", tags=["Internal Admin Users"])


@router.get("")
def list_users(
    search: str | None = None,
    plan: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=200),
    staff=Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    offset = (page - 1) * limit
    items, total = list_saas_users(db, search=search, plan_code=plan, status=status, limit=limit, offset=offset)
    return {"items": items, "total": total, "page": page, "limit": limit}


@router.get("/{user_id}")
def user_card(
    user_id: UUID,
    history_limit: int = Query(30, ge=1, le=200),
    staff=Depends(require_superadmin),
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
    return {
        "user": serialize_saas_user(db, user),
        "integrations": [
            {
                "id": str(i.id),
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
                "id": str(h.id),
                "created_at": h.created_at,
                "event_type": h.event_type,
                "action": h.action,
                "description": h.description,
            }
            for h in history
        ],
    }


@router.post("/{user_id}/impersonate", response_model=ImpersonateResponse)
def impersonate_user(
    user_id: str,
    request: Request,
    staff=Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    return impersonate_saas_user(request=request, staff=staff, db=db, target_user_id=user_id)


@router.post("/{user_id}/reset-sessions")
def reset_user_sessions(user_id: UUID, staff=Depends(require_superadmin), db: Session = Depends(get_db)):
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
    return {"ok": True}


@router.post("/{user_id}/block")
def block_user(
    user_id: UUID,
    body: BlockUserBody,
    staff=Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    user.block_reason = body.reason.strip()
    write_audit(
        db,
        staff=staff,
        action="user_blocked",
        target_type="user",
        target_id=str(user_id),
        meta={"reason": body.reason},
    )
    db.commit()
    return {"ok": True}


@router.post("/{user_id}/unblock")
def unblock_user(user_id: UUID, staff=Depends(require_superadmin), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = True
    user.block_reason = None
    write_audit(db, staff=staff, action="user_unblocked", target_type="user", target_id=str(user_id))
    db.commit()
    return {"ok": True}


@router.patch("/{user_id}/ai-limit")
def patch_ai_limit(
    user_id: UUID,
    limit: int = Query(..., ge=0, le=100000),
    staff=Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    write_audit(
        db,
        staff=staff,
        action="ai_limit_changed",
        target_type="user",
        target_id=str(user_id),
        meta={"new_limit": limit},
    )
    db.commit()
    return {"ok": True, "note": "Per-user AI limit override not persisted yet; use tariff plan limits"}
