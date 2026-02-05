import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from core import models, security
from core.database import get_db

router = APIRouter(prefix="/phone-stats", tags=["Phone Stats"])


class PhoneStatsResponse(BaseModel):
    total: int
    accepted: int
    rejected: int
    rejection_rate: float


class PhoneProjectStats(BaseModel):
    project_id: uuid.UUID
    project_name: str
    total: int
    accepted: int
    rejected: int
    acceptance_rate: float


class PhoneStatsPayload(BaseModel):
    stats: PhoneStatsResponse
    project_stats: List[PhoneProjectStats]


@router.get("/", response_model=PhoneStatsPayload)
def get_phone_stats(
    days: int = Query(7, ge=1, le=365),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Статистика заявок телефонии за период.
    """
    since = datetime.utcnow() - timedelta(days=days)

    base_query = (
        db.query(models.Lead)
        .join(models.PhoneProject, models.Lead.project_id == models.PhoneProject.id)
        .filter(
            models.PhoneProject.owner_id == current_user.id,
            models.Lead.created_at >= since,
        )
    )

    total = base_query.count()
    accepted = base_query.filter(models.Lead.is_valid == True).count()
    rejected = base_query.filter(models.Lead.is_valid == False).count()
    rejection_rate = (rejected / total * 100) if total else 0.0

    project_rows = (
        db.query(
            models.PhoneProject.id.label("project_id"),
            models.PhoneProject.name.label("project_name"),
            func.count(models.Lead.id).label("total"),
            func.sum(case((models.Lead.is_valid == True, 1), else_=0)).label("accepted"),
            func.sum(case((models.Lead.is_valid == False, 1), else_=0)).label("rejected"),
        )
        .join(models.Lead, models.Lead.project_id == models.PhoneProject.id)
        .filter(
            models.PhoneProject.owner_id == current_user.id,
            models.Lead.created_at >= since,
        )
        .group_by(models.PhoneProject.id, models.PhoneProject.name)
        .order_by(func.count(models.Lead.id).desc())
        .all()
    )

    project_stats = []
    for row in project_rows:
        total_p = int(row.total or 0)
        accepted_p = int(row.accepted or 0)
        rejected_p = int(row.rejected or 0)
        acceptance_rate = (accepted_p / total_p * 100) if total_p else 0.0
        project_stats.append(
            PhoneProjectStats(
                project_id=row.project_id,
                project_name=row.project_name,
                total=total_p,
                accepted=accepted_p,
                rejected=rejected_p,
                acceptance_rate=round(acceptance_rate, 2),
            )
        )

    return PhoneStatsPayload(
        stats=PhoneStatsResponse(
            total=total,
            accepted=accepted,
            rejected=rejected,
            rejection_rate=round(rejection_rate, 2),
        ),
        project_stats=project_stats,
    )

