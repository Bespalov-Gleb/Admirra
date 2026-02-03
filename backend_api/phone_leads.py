import uuid
from datetime import date, datetime, time
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
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
        )
        for lead in leads
    ]

