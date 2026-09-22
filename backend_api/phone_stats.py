import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core import models, security
from core.database import get_db
from lead_validator.services.scoped_stats import project_statistics, StatsLimitExceeded

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
    try:
        return PhoneStatsPayload(**project_statistics(db, current_user.id, days=days))
    except StatsLimitExceeded as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
