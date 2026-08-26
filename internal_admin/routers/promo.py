"""Superadmin: промокоды на скидку тарифа + аналитика погашений."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.database import get_db
from core import models
from internal_admin.deps import require_superadmin

router = APIRouter(prefix="/promo-codes", tags=["Internal Admin Promo"])


# ── Схемы ────────────────────────────────────────────────────────────────────
class PromoCreate(BaseModel):
    code: str
    description: Optional[str] = None
    discount_percent: int = Field(ge=1, le=100)
    active: bool = True
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    max_redemptions: Optional[int] = Field(default=None, ge=1)
    per_user_limit: int = Field(default=1, ge=0)
    monthly_only: bool = False
    applies_to_plans: Optional[list[str]] = None


class PromoUpdate(BaseModel):
    description: Optional[str] = None
    discount_percent: Optional[int] = Field(default=None, ge=1, le=100)
    active: Optional[bool] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    max_redemptions: Optional[int] = Field(default=None, ge=1)
    per_user_limit: Optional[int] = Field(default=None, ge=0)
    monthly_only: Optional[bool] = None
    applies_to_plans: Optional[list[str]] = None


def _norm_code(code: str) -> str:
    value = (code or "").strip().upper()
    if not value or len(value) > 64:
        raise HTTPException(status_code=422, detail="Код: 1–64 символа")
    return value


def _norm_plans(plans: Optional[list[str]]) -> Optional[list[str]]:
    if not plans:
        return None
    cleaned = [str(p).strip().lower() for p in plans if str(p).strip()]
    return cleaned or None


def _analytics(db: Session) -> dict:
    """{promo_code_id: {redemptions, unique_users, total_discount, total_revenue}}."""
    rows = (
        db.query(
            models.PromoRedemption.promo_code_id.label("pid"),
            func.count(models.PromoRedemption.id).label("redemptions"),
            func.count(func.distinct(models.PromoRedemption.user_id)).label("unique_users"),
            func.coalesce(func.sum(models.PromoRedemption.discount_amount), 0).label("total_discount"),
            func.coalesce(func.sum(models.PromoRedemption.final_amount), 0).label("total_revenue"),
        )
        .group_by(models.PromoRedemption.promo_code_id)
        .all()
    )
    return {
        str(r.pid): {
            "redemptions": int(r.redemptions or 0),
            "unique_users": int(r.unique_users or 0),
            "total_discount": float(r.total_discount or 0),
            "total_revenue": float(r.total_revenue or 0),
        }
        for r in rows
    }


def _serialize(p: "models.PromoCode", stats: dict) -> dict:
    s = stats.get(str(p.id), {"redemptions": 0, "unique_users": 0, "total_discount": 0.0, "total_revenue": 0.0})
    return {
        "id": str(p.id),
        "code": p.code,
        "description": p.description,
        "discount_percent": p.discount_percent,
        "active": p.active,
        "valid_from": p.valid_from.isoformat() if p.valid_from else None,
        "valid_until": p.valid_until.isoformat() if p.valid_until else None,
        "max_redemptions": p.max_redemptions,
        "per_user_limit": p.per_user_limit,
        "monthly_only": p.monthly_only,
        "applies_to_plans": p.applies_to_plans or None,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        # Аналитика: сколько уникальных пользователей оплатили с этим кодом и т.д.
        "redemptions": s["redemptions"],
        "unique_users": s["unique_users"],
        "total_discount": s["total_discount"],
        "total_revenue": s["total_revenue"],
    }


# ── Эндпоинты ────────────────────────────────────────────────────────────────
@router.get("")
def list_promo_codes(staff=Depends(require_superadmin), db: Session = Depends(get_db)):
    stats = _analytics(db)
    items = db.query(models.PromoCode).order_by(models.PromoCode.created_at.desc()).all()
    return {"items": [_serialize(p, stats) for p in items]}


@router.post("", status_code=201)
def create_promo_code(body: PromoCreate, staff=Depends(require_superadmin), db: Session = Depends(get_db)):
    code = _norm_code(body.code)
    if db.query(models.PromoCode.id).filter(models.PromoCode.code == code).first():
        raise HTTPException(status_code=409, detail="Такой промокод уже существует")
    promo = models.PromoCode(
        code=code,
        description=(body.description or None),
        discount_percent=body.discount_percent,
        active=body.active,
        valid_from=body.valid_from,
        valid_until=body.valid_until,
        max_redemptions=body.max_redemptions,
        per_user_limit=body.per_user_limit,
        monthly_only=body.monthly_only,
        applies_to_plans=_norm_plans(body.applies_to_plans),
        created_by=staff.id,
    )
    db.add(promo)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Такой промокод уже существует")
    db.refresh(promo)
    return _serialize(promo, {})


@router.patch("/{promo_id}")
def update_promo_code(promo_id: str, body: PromoUpdate, staff=Depends(require_superadmin), db: Session = Depends(get_db)):
    promo = db.query(models.PromoCode).filter(models.PromoCode.id == promo_id).first()
    if not promo:
        raise HTTPException(status_code=404, detail="Промокод не найден")
    data = body.model_dump(exclude_unset=True)
    if "applies_to_plans" in data:
        data["applies_to_plans"] = _norm_plans(data["applies_to_plans"])
    for field, value in data.items():
        setattr(promo, field, value)
    db.commit()
    db.refresh(promo)
    return _serialize(promo, _analytics(db))


@router.delete("/{promo_id}", status_code=204)
def delete_promo_code(promo_id: str, staff=Depends(require_superadmin), db: Session = Depends(get_db)):
    promo = db.query(models.PromoCode).filter(models.PromoCode.id == promo_id).first()
    if not promo:
        raise HTTPException(status_code=404, detail="Промокод не найден")
    used = db.query(models.PromoRedemption.id).filter(models.PromoRedemption.promo_code_id == promo.id).first()
    if used:
        # Есть погашения — не удаляем (иначе потеряем историю/аналитику), а выключаем.
        promo.active = False
        db.commit()
        raise HTTPException(status_code=409, detail="Промокод уже использовался — он деактивирован, но не удалён")
    db.delete(promo)
    db.commit()


@router.get("/{promo_id}/redemptions")
def promo_redemptions(promo_id: str, staff=Depends(require_superadmin), db: Session = Depends(get_db)):
    promo = db.query(models.PromoCode).filter(models.PromoCode.id == promo_id).first()
    if not promo:
        raise HTTPException(status_code=404, detail="Промокод не найден")
    rows = (
        db.query(models.PromoRedemption, models.User.email)
        .join(models.User, models.User.id == models.PromoRedemption.user_id)
        .filter(models.PromoRedemption.promo_code_id == promo.id)
        .order_by(models.PromoRedemption.redeemed_at.desc())
        .limit(500)
        .all()
    )
    return {
        "code": promo.code,
        "items": [
            {
                "user_id": str(r.PromoRedemption.user_id),
                "email": email,
                "plan_code": r.PromoRedemption.plan_code,
                "billing_period": r.PromoRedemption.billing_period,
                "original_amount": float(r.PromoRedemption.original_amount or 0),
                "discount_amount": float(r.PromoRedemption.discount_amount or 0),
                "final_amount": float(r.PromoRedemption.final_amount or 0),
                "redeemed_at": r.PromoRedemption.redeemed_at.isoformat() if r.PromoRedemption.redeemed_at else None,
            }
            for r, email in rows
        ],
    }
