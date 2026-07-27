"""Алиасы ТЗ: /api/admin/sessions, /api/admin/audit-log."""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.database import get_db
from core import models
from internal_admin.deps import require_superadmin
from internal_admin.models import AdminAuditLog, AdminStaffSession
from internal_admin.services import write_audit
from internal_admin.services.user_helpers import user_full_name

sessions_router = APIRouter(prefix="/sessions", tags=["Internal Admin Sessions"])
audit_router = APIRouter(prefix="/audit-log", tags=["Internal Admin Audit"])


@sessions_router.get("")
def list_sessions(staff=Depends(require_superadmin), db: Session = Depends(get_db)):
    rows = (
        db.query(AdminStaffSession)
        .filter(AdminStaffSession.is_active.is_(True))
        .order_by(AdminStaffSession.last_seen_at.desc())
        .limit(100)
        .all()
    )
    items = []
    for s in rows:
        user = db.query(models.User).filter(models.User.id == s.staff_user_id).first()
        items.append(
            {
                "id": str(s.id),
                "staff_email": user.email if user else None,
                "staff_name": user_full_name(user) if user else None,
                "role": user.role.value if user else None,
                "ip_address": s.ip_address,
                "city": s.city,
                "user_agent": s.user_agent,
                "last_seen_at": s.last_seen_at,
                "created_at": s.created_at,
                "online": True,
            }
        )
    return {"items": items}


@sessions_router.delete("/{session_id}")
def delete_session(session_id: UUID, staff=Depends(require_superadmin), db: Session = Depends(get_db)):
    row = db.query(AdminStaffSession).filter(AdminStaffSession.id == session_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    row.is_active = False
    row.revoked_at = datetime.now(timezone.utc)
    write_audit(db, staff=staff, action="staff_session_revoked", target_type="session", target_id=str(session_id))
    db.commit()
    return {"ok": True}


@audit_router.get("")
def audit_log(
    staff_email: str | None = None,
    action: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    days: int = Query(365, ge=1, le=3650),
    staff=Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    dt_from = datetime.now(timezone.utc) - timedelta(days=days)
    query = db.query(AdminAuditLog).filter(AdminAuditLog.created_at >= dt_from)
    if staff_email:
        query = query.filter(AdminAuditLog.staff_email == staff_email.strip().lower())
    if action:
        query = query.filter(AdminAuditLog.action == action)
    offset = (page - 1) * limit
    rows = query.order_by(AdminAuditLog.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "items": [
            {
                "id": str(r.id),
                "created_at": r.created_at,
                "staff_email": r.staff_email,
                "action": r.action,
                "description": r.description,
                "target_type": r.target_type,
                "target_id": r.target_id,
            }
            for r in rows
        ],
        "page": page,
        "limit": limit,
    }
