"""Сервисы внутренней админки."""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from core.config import get_config
from internal_admin.models import AdminAuditLog, AdminSetting, AiUsageLog


DEFAULT_SETTINGS: dict[str, Any] = {
    "team_2fa_required": False,
    "support_impersonation_allowed": True,
    "session_logging_enabled": True,
    "ip_whitelist_enabled": False,
    "ip_whitelist": [],
    "maintenance_mode": False,
    "registration_enabled": True,
    "team_email_alerts_enabled": True,
    "trial_days": 14,
    "openai_balance_usd": 87.20,
    "openai_alert_threshold_usd": 50.0,
    "integration_unisender_status": "connected",
    "integration_max_status": "coming_soon",
}


def get_setting(db: Session, key: str) -> Any:
    row = db.query(AdminSetting).filter(AdminSetting.key == key).first()
    if not row:
        return DEFAULT_SETTINGS.get(key)
    return row.value


def get_all_settings(db: Session) -> dict[str, Any]:
    out = dict(DEFAULT_SETTINGS)
    for row in db.query(AdminSetting).all():
        out[row.key] = row.value
    return out


def set_setting(db: Session, key: str, value: Any, updated_by: Optional[UUID] = None) -> None:
    row = db.query(AdminSetting).filter(AdminSetting.key == key).first()
    if row:
        row.value = value
        row.updated_by = updated_by
    else:
        db.add(AdminSetting(key=key, value=value, updated_by=updated_by))
    db.flush()


def write_audit(
    db: Session,
    *,
    staff: Optional[Any],
    action: str,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    description: Optional[str] = None,
    meta: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    db.add(
        AdminAuditLog(
            staff_user_id=getattr(staff, "id", None),
            staff_email=getattr(staff, "email", None),
            action=action,
            target_type=target_type,
            target_id=target_id,
            description=description,
            meta=meta,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    )


def log_ai_usage(
    db: Session,
    *,
    user_id: Optional[UUID],
    action: str,
    tokens_input: int = 0,
    tokens_output: int = 0,
    meta: Optional[dict] = None,
) -> AiUsageLog:
    total = max(0, tokens_input) + max(0, tokens_output)
    usd_per_1k = get_config().internal_admin.openai_usd_per_1k_tokens
    cost = Decimal(str(total)) / Decimal("1000") * Decimal(str(usd_per_1k))
    row = AiUsageLog(
        user_id=user_id,
        action=action,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        tokens_total=total,
        cost_usd=str(cost.quantize(Decimal("0.0001"))),
        meta=meta,
    )
    db.add(row)
    return row


def estimate_tokens_from_text(text: str) -> int:
    """Грубая оценка: ~4 символа на токен."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def month_ai_cost_usd(db: Session, dt_from: datetime) -> float:
    rows = db.query(AiUsageLog).filter(AiUsageLog.created_at >= dt_from).all()
    total = Decimal("0")
    for r in rows:
        try:
            total += Decimal(r.cost_usd or "0")
        except Exception:
            pass
    return float(total.quantize(Decimal("0.01")))
