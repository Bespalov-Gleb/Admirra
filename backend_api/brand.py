import os
import uuid
import logging
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from core import models, security
from core.database import get_db
from backend_api.services.subscription import SubscriptionService

logger = logging.getLogger("api.brand")

router = APIRouter(prefix="/brand", tags=["Brand / White Label"])

UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", "uploads")).resolve()
BRAND_DIR = UPLOADS_DIR / "brand"
BRAND_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg"}
MAX_LOGO_SIZE = 2 * 1024 * 1024
HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


class BrandSettingsResponse(BaseModel):
    brand_logo_url: Optional[str] = None
    brand_color: Optional[str] = None
    brand_pdf_header: Optional[str] = None
    brand_pdf_signature: Optional[str] = None
    brand_custom_domain: Optional[str] = None
    brand_domain_status: Optional[str] = None
    whitelabel_available: bool = False


class BrandSettingsUpdate(BaseModel):
    brand_color: Optional[str] = None
    brand_pdf_header: Optional[str] = None
    brand_pdf_signature: Optional[str] = None
    brand_custom_domain: Optional[str] = None


def _check_wl(user: models.User, db: Session) -> bool:
    sub = (
        db.query(models.Subscription)
        .filter(
            models.Subscription.user_id == user.id,
            models.Subscription.status.in_([
                models.SubscriptionStatus.ACTIVE,
                models.SubscriptionStatus.TRIAL,
            ]),
        )
        .order_by(models.Subscription.created_at.desc())
        .first()
    )
    if not sub:
        return False
    if sub.plan_id:
        plan = db.query(models.TariffPlan).filter(models.TariffPlan.id == sub.plan_id).first()
        if plan:
            return bool(getattr(plan, "whitelabel_included", False))
    plan = SubscriptionService.get_user_plan(db, user)
    return str(plan.code or "").lower() == "standard"


@router.get("", response_model=BrandSettingsResponse)
def get_brand(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    return BrandSettingsResponse(
        brand_logo_url=current_user.brand_logo_url,
        brand_color=current_user.brand_color,
        brand_pdf_header=current_user.brand_pdf_header,
        brand_pdf_signature=current_user.brand_pdf_signature,
        brand_custom_domain=current_user.brand_custom_domain,
        brand_domain_status=current_user.brand_domain_status or "none",
        whitelabel_available=_check_wl(current_user, db),
    )


@router.put("", response_model=BrandSettingsResponse)
def update_brand(
    body: BrandSettingsUpdate,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    wl = _check_wl(current_user, db)
    if not wl:
        raise HTTPException(status_code=403, detail="White Label недоступен на вашем тарифе")

    if body.brand_color is not None:
        if body.brand_color and not HEX_COLOR_RE.match(body.brand_color):
            raise HTTPException(status_code=400, detail="Некорректный HEX-цвет")
        current_user.brand_color = body.brand_color
    if body.brand_pdf_header is not None:
        current_user.brand_pdf_header = body.brand_pdf_header
    if body.brand_pdf_signature is not None:
        current_user.brand_pdf_signature = body.brand_pdf_signature
    if body.brand_custom_domain is not None:
        old = current_user.brand_custom_domain
        current_user.brand_custom_domain = body.brand_custom_domain
        if body.brand_custom_domain and body.brand_custom_domain != old:
            current_user.brand_domain_status = "pending"
        elif not body.brand_custom_domain:
            current_user.brand_domain_status = "none"

    db.commit()
    db.refresh(current_user)

    return BrandSettingsResponse(
        brand_logo_url=current_user.brand_logo_url,
        brand_color=current_user.brand_color,
        brand_pdf_header=current_user.brand_pdf_header,
        brand_pdf_signature=current_user.brand_pdf_signature,
        brand_custom_domain=current_user.brand_custom_domain,
        brand_domain_status=current_user.brand_domain_status or "none",
        whitelabel_available=wl,
    )


@router.post("/logo", response_model=BrandSettingsResponse)
async def upload_logo(
    file: UploadFile = File(...),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    wl = _check_wl(current_user, db)
    if not wl:
        raise HTTPException(status_code=403, detail="White Label недоступен на вашем тарифе")

    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Допустимые форматы: {', '.join(ALLOWED_EXTENSIONS)}")

    content = await file.read()
    if len(content) > MAX_LOGO_SIZE:
        raise HTTPException(status_code=400, detail="Файл слишком большой (макс. 2 МБ)")

    filename = f"{current_user.id}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = BRAND_DIR / filename
    filepath.write_bytes(content)

    current_user.brand_logo_url = f"/uploads/brand/{filename}"
    db.commit()
    db.refresh(current_user)

    return BrandSettingsResponse(
        brand_logo_url=current_user.brand_logo_url,
        brand_color=current_user.brand_color,
        brand_pdf_header=current_user.brand_pdf_header,
        brand_pdf_signature=current_user.brand_pdf_signature,
        brand_custom_domain=current_user.brand_custom_domain,
        brand_domain_status=current_user.brand_domain_status or "none",
        whitelabel_available=wl,
    )


@router.delete("/logo", response_model=BrandSettingsResponse)
def delete_logo(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    wl = _check_wl(current_user, db)
    if not wl:
        raise HTTPException(status_code=403, detail="White Label недоступен на вашем тарифе")

    if current_user.brand_logo_url:
        old_path = UPLOADS_DIR.parent / current_user.brand_logo_url.lstrip("/")
        if old_path.is_file():
            old_path.unlink(missing_ok=True)
    current_user.brand_logo_url = None
    db.commit()
    db.refresh(current_user)

    return BrandSettingsResponse(
        brand_logo_url=None,
        brand_color=current_user.brand_color,
        brand_pdf_header=current_user.brand_pdf_header,
        brand_pdf_signature=current_user.brand_pdf_signature,
        brand_custom_domain=current_user.brand_custom_domain,
        brand_domain_status=current_user.brand_domain_status or "none",
        whitelabel_available=wl,
    )
