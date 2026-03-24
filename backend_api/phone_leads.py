import uuid
import json
from datetime import date, datetime, time
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core import models, security
from core.database import get_db

router = APIRouter(prefix="/phone-leads", tags=["Phone Leads"])


class PhoneLeadListItem(BaseModel):
    id: uuid.UUID
    phone: str
    email: Optional[str] = None
    name: Optional[str] = None
    created_at: Optional[datetime] = None
    is_accepted: bool
    rejection_reason: Optional[str] = None
    phone_project_id: uuid.UUID
    lead_score: Optional[int] = None
    qualification_tier: Optional[str] = None
    has_viber: Optional[bool] = None

    class Config:
        from_attributes = True


class PhoneLeadDetail(BaseModel):
    id: uuid.UUID
    phone_project_id: uuid.UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    status: Optional[str] = None
    is_accepted: bool
    rejection_reason: Optional[str] = None

    phone: str
    email: Optional[str] = None
    name: Optional[str] = None
    surname: Optional[str] = None

    lead_score: Optional[int] = None
    qualification_tier: Optional[str] = None
    phone_type: Optional[str] = None
    phone_provider: Optional[str] = None
    phone_region: Optional[str] = None
    phone_city: Optional[str] = None
    dadata_qc: Optional[int] = None

    has_telegram: Optional[bool] = None
    has_whatsapp: Optional[bool] = None
    has_viber: Optional[bool] = None
    has_tiktok: Optional[bool] = None
    has_vk: Optional[bool] = None
    social_accounts_data: Optional[dict] = None

    has_gosuslugi: Optional[bool] = None
    gosuslugi_name: Optional[str] = None
    gosuslugi_surname: Optional[str] = None

    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_content: Optional[str] = None
    utm_term: Optional[str] = None

    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    referer: Optional[str] = None
    ym_uid: Optional[str] = None
    geo_country: Optional[str] = None
    browser_timezone: Optional[str] = None
    fingerprint: Optional[str] = None

    form_data: Optional[dict] = None
    main_operator: Optional[str] = None
    registrant_info: Optional[str] = None

    exported_to_crm: Optional[bool] = None
    exported_to_email: Optional[bool] = None
    exported_to_telegram: Optional[bool] = None
    exported_to_metrica: Optional[bool] = None
    export_timestamp: Optional[datetime] = None

    class Config:
        from_attributes = True


@router.get("/", response_model=List[PhoneLeadListItem])
def list_phone_leads(
    project_id: Optional[uuid.UUID] = Query(None),
    is_accepted: Optional[bool] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Получить список заявок телефонии с фильтрами.
    """
    query = (
        db.query(models.Lead)
        .join(models.PhoneProject, models.Lead.project_id == models.PhoneProject.id)
        .filter(models.PhoneProject.owner_id == current_user.id)
    )

    if project_id:
        query = query.filter(models.Lead.project_id == project_id)
    if is_accepted is not None:
        query = query.filter(models.Lead.is_valid == is_accepted)
    if start_date:
        start_dt = datetime.combine(start_date, time.min)
        query = query.filter(models.Lead.created_at >= start_dt)
    if end_date:
        end_dt = datetime.combine(end_date, time.max)
        query = query.filter(models.Lead.created_at <= end_dt)

    leads = query.order_by(models.Lead.created_at.desc()).all()

    return [
        PhoneLeadListItem(
            id=lead.id,
            phone=lead.phone,
            email=lead.email,
            name=lead.name,
            created_at=lead.created_at,
            is_accepted=bool(lead.is_valid),
            rejection_reason=lead.validation_reason,
            phone_project_id=lead.project_id,
            lead_score=getattr(lead, "lead_score", None),
            qualification_tier=getattr(lead, "qualification_tier", None),
            has_viber=getattr(lead, "has_viber", None),
        )
        for lead in leads
    ]


@router.get("/{lead_id}", response_model=PhoneLeadDetail)
def get_phone_lead_detail(
    lead_id: uuid.UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Получить полную информацию по одной заявке телефонии.
    Доступ только к лидам проектов текущего пользователя.
    """
    lead = (
        db.query(models.Lead)
        .join(models.PhoneProject, models.Lead.project_id == models.PhoneProject.id)
        .filter(
            models.Lead.id == lead_id,
            models.PhoneProject.owner_id == current_user.id,
        )
        .first()
    )
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    def _parse_json_field(raw_value):
        if raw_value is None:
            return None
        if isinstance(raw_value, dict):
            return raw_value
        if isinstance(raw_value, str):
            s = raw_value.strip()
            if not s:
                return None
            try:
                parsed = json.loads(s)
                return parsed if isinstance(parsed, dict) else {"value": parsed}
            except Exception:
                return {"raw": raw_value}
        return {"value": raw_value}

    return PhoneLeadDetail(
        id=lead.id,
        phone_project_id=lead.project_id,
        created_at=lead.created_at,
        updated_at=lead.updated_at,
        status=str(lead.status.value if getattr(lead.status, "value", None) else lead.status) if lead.status is not None else None,
        is_accepted=bool(lead.is_valid),
        rejection_reason=lead.validation_reason,
        phone=lead.phone,
        email=lead.email,
        name=lead.name,
        surname=lead.surname,
        lead_score=lead.lead_score,
        qualification_tier=lead.qualification_tier,
        phone_type=lead.phone_type,
        phone_provider=lead.phone_provider,
        phone_region=lead.phone_region,
        phone_city=lead.phone_city,
        dadata_qc=lead.dadata_qc,
        has_telegram=lead.has_telegram,
        has_whatsapp=lead.has_whatsapp,
        has_viber=lead.has_viber,
        has_tiktok=lead.has_tiktok,
        has_vk=lead.has_vk,
        social_accounts_data=_parse_json_field(lead.social_accounts_data),
        has_gosuslugi=lead.has_gosuslugi,
        gosuslugi_name=lead.gosuslugi_name,
        gosuslugi_surname=lead.gosuslugi_surname,
        utm_source=lead.utm_source,
        utm_medium=lead.utm_medium,
        utm_campaign=lead.utm_campaign,
        utm_content=lead.utm_content,
        utm_term=lead.utm_term,
        client_ip=lead.client_ip,
        user_agent=lead.user_agent,
        referer=lead.referer,
        ym_uid=lead.ym_uid,
        geo_country=lead.geo_country,
        browser_timezone=lead.browser_timezone,
        fingerprint=lead.fingerprint,
        form_data=_parse_json_field(lead.form_data),
        main_operator=lead.main_operator,
        registrant_info=lead.registrant_info,
        exported_to_crm=lead.exported_to_crm,
        exported_to_email=lead.exported_to_email,
        exported_to_telegram=lead.exported_to_telegram,
        exported_to_metrica=lead.exported_to_metrica,
        export_timestamp=lead.export_timestamp,
    )

