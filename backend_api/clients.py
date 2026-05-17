import uuid
from io import BytesIO
from pathlib import Path
from os import getenv
from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from core.database import get_db
from core import models, schemas, security
from datetime import datetime, date, timedelta
from typing import List
from PIL import Image, ImageOps, UnidentifiedImageError

from backend_api.stats_service import StatsService
from backend_api.services.subscription import SubscriptionService
from backend_api.access_control import get_accessible_client_ids, assert_project_access, get_team_context
from backend_api.services.history import log_history_event

router = APIRouter(prefix="/clients", tags=["Clients"])

AVATAR_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
AVATAR_MAX_BYTES = 5 * 1024 * 1024
AVATAR_SIZE = (256, 256)
UPLOADS_DIR = Path(getenv("UPLOADS_DIR", "uploads"))
AVATAR_DIR = UPLOADS_DIR / "project-avatars"


def _avatar_public_url(filename: str) -> str:
    return f"/uploads/project-avatars/{filename}"


def _remove_old_avatar(avatar_url: str | None) -> None:
    if not avatar_url or not avatar_url.startswith("/uploads/project-avatars/"):
        return
    filename = avatar_url.rsplit("/", 1)[-1]
    if not filename:
        return
    try:
        (AVATAR_DIR / filename).unlink(missing_ok=True)
    except OSError:
        pass

@router.get("/stats", response_model=List[schemas.ClientResponse])
def get_clients_with_stats(
    start_date: str = None,
    end_date: str = None,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all clients with aggregated statistics for a specified period.
    """
    d_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else datetime.utcnow().date()
    # Default to 7 days if no start_date provided
    d_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else d_end - timedelta(days=6)
    
    accessible_ids = get_accessible_client_ids(db, current_user)
    user_clients = db.query(models.Client).filter(models.Client.id.in_(accessible_ids)).all() if accessible_ids else []
    
    results = []
    for client in user_clients:
        # Get dynamic summary with trends for each client
        summary_data = StatsService.aggregate_summary(db, [client.id], d_start, d_end)
        client.summary = summary_data
        results.append(client)
        
    return results

@router.get("/", response_model=List[schemas.ClientResponse])
def get_clients(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all clients owned by the current user.
    """
    accessible_ids = get_accessible_client_ids(db, current_user)
    if not accessible_ids:
        return []
    return db.query(models.Client).filter(models.Client.id.in_(accessible_ids)).all()

@router.post("/", response_model=schemas.ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    client_in: schemas.ClientCreate,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new client.
    """
    ctx = get_team_context(db, current_user)
    if not ctx.is_owner and ctx.team_role == models.TeamMemberRole.CLIENT.value:
        raise HTTPException(status_code=403, detail="Клиент не может создавать проекты")
    SubscriptionService.ensure_can_create_project(db, current_user)
    new_client = models.Client(
        owner_id=current_user.id,
        **client_in.dict()
    )
    db.add(new_client)
    log_history_event(
        db,
        actor=current_user,
        event_type="project",
        action="project_created",
        description=f"Создан проект {new_client.name}",
        client_id=new_client.id,
        target_type="client",
        target_id=str(new_client.id),
    )
    db.commit()
    db.refresh(new_client)
    return new_client

@router.get("/{client_id}", response_model=schemas.ClientResponse)
def get_client(
    client_id: uuid.UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get specific client details.
    """
    assert_project_access(db, current_user, client_id, write=False)
    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    return client

@router.put("/{client_id}", response_model=schemas.ClientResponse)
def update_client(
    client_id: uuid.UUID,
    client_in: schemas.ClientUpdate,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    assert_project_access(db, current_user, client_id, write=True)
    client = db.query(models.Client).filter(models.Client.id == client_id).first()

    update_data = client_in.dict(exclude_unset=True)

    if "status" in update_data:
        new_status = update_data["status"]
        if new_status not in ("active", "paused"):
            raise HTTPException(status_code=400, detail="Статус должен быть 'active' или 'paused'")
        old_status = client.status.value if hasattr(client.status, "value") else client.status
        if old_status == "paused" and new_status == "active":
            _check_can_resume_project(db, current_user, client)
        update_data["status"] = models.ClientStatus(new_status)

    for key, value in update_data.items():
        setattr(client, key, value)
    if update_data:
        log_history_event(
            db,
            actor=current_user,
            event_type="project",
            action="project_updated",
            description=f"Обновлен проект {client.name}",
            client_id=client.id,
            target_type="client",
            target_id=str(client.id),
            meta={"fields": sorted(str(k) for k in update_data.keys())},
        )
        log_history_event(
            db,
            actor=current_user,
            event_type="project",
            action="project_settings_changed",
            description=f"Изменены настройки проекта {client.name}",
            client_id=client.id,
            target_type="client",
            target_id=str(client.id),
            meta={"fields": sorted(str(k) for k in update_data.keys())},
        )
    db.commit()
    db.refresh(client)
    return client


def _check_can_resume_project(db: Session, user: models.User, excluded_client: models.Client):
    if SubscriptionService.is_admin_bypass(user):
        return
    plan = SubscriptionService.get_user_plan(db, user)
    active_count = db.query(models.Client).filter(
        models.Client.owner_id == user.id,
        models.Client.status == models.ClientStatus.ACTIVE,
    ).count()
    phone_count = db.query(models.PhoneProject).filter(models.PhoneProject.owner_id == user.id).count()
    total = active_count + phone_count
    if total < plan.max_projects:
        return
    if not SubscriptionService.billing_enforced():
        return
    raise HTTPException(
        status_code=403,
        detail=f"Достигнут лимит активных проектов для тарифа '{plan.name}' ({plan.max_projects}). Повысьте тариф или приостановите другой проект.",
    )


@router.post("/{client_id}/avatar", response_model=schemas.ClientResponse)
async def upload_client_avatar(
    client_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a project avatar. Projects are stored as Client entities in the backend.
    """
    assert_project_access(db, current_user, client_id, write=True)
    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Проект не найден")

    if file.content_type not in AVATAR_ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Поддерживаются только JPG, PNG и WebP")

    content = await file.read(AVATAR_MAX_BYTES + 1)
    if len(content) > AVATAR_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Размер файла не должен превышать 5 МБ")
    if not content:
        raise HTTPException(status_code=400, detail="Файл пустой")

    try:
        image = Image.open(BytesIO(content))
        image.verify()
        image = Image.open(BytesIO(content))
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=400, detail="Не удалось прочитать изображение")

    image = ImageOps.exif_transpose(image)
    image = ImageOps.fit(image, AVATAR_SIZE, method=Image.Resampling.LANCZOS)
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA")

    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{client_id}-{uuid.uuid4().hex[:12]}.webp"
    avatar_path = AVATAR_DIR / filename
    image.save(avatar_path, format="WEBP", quality=88, method=6)

    old_avatar_url = client.avatar_url
    client.avatar_url = _avatar_public_url(filename)
    log_history_event(
        db,
        actor=current_user,
        event_type="project",
        action="project_avatar_updated",
        description=f"Обновлена аватарка проекта {client.name}",
        client_id=client.id,
        target_type="client",
        target_id=str(client.id),
    )
    db.commit()
    db.refresh(client)
    _remove_old_avatar(old_avatar_url)
    return client

@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: uuid.UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    assert_project_access(db, current_user, client_id, write=True)
    client = db.query(models.Client).filter(models.Client.id == client_id).first()

    log_history_event(
        db,
        actor=current_user,
        event_type="project",
        action="project_deleted",
        description=f"Удален проект {client.name}",
        client_id=client.id,
        target_type="client",
        target_id=str(client.id),
    )
    db.delete(client)
    db.commit()
    return None


# ── Budgets ──────────────────────────────────────────────────────────

def _default_period() -> tuple[date, date]:
    today = date.today()
    period_start = today.replace(day=1)
    if today.month == 12:
        period_end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        period_end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    return period_start, period_end


def _resolve_channel(db: Session, client_id: uuid.UUID, item) -> models.IntegrationPlatform:
    if getattr(item, "channel", None):
        return _parse_platform(item.channel)
    integration_id = getattr(item, "integration_id", None)
    if integration_id:
        integration = db.query(models.Integration).filter(
            models.Integration.id == uuid.UUID(str(integration_id)),
            models.Integration.client_id == client_id,
        ).first()
        if integration:
            return integration.platform
    raise HTTPException(status_code=400, detail="Не указан канал или integration_id")


@router.get("/{client_id}/budgets", response_model=List[schemas.ProjectBudgetResponse])
def get_budgets(
    client_id: uuid.UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    assert_project_access(db, current_user, client_id, write=False)
    rows = (
        db.query(models.ProjectBudget)
        .filter(models.ProjectBudget.client_id == client_id)
        .order_by(models.ProjectBudget.period_start.desc(), models.ProjectBudget.channel)
        .all()
    )
    return rows


@router.put("/{client_id}/budgets", response_model=List[schemas.ProjectBudgetResponse])
def set_budgets(
    client_id: uuid.UUID,
    items: List[schemas.ProjectBudgetItem] = Body(...),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    assert_project_access(db, current_user, client_id, write=True)
    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Проект не найден")

    db.query(models.ProjectBudget).filter(models.ProjectBudget.client_id == client_id).delete()

    default_start, default_end = _default_period()
    created = []
    for item in items:
        channel_enum = _resolve_channel(db, client_id, item)
        p_start = datetime.strptime(item.period_start, "%Y-%m-%d").date() if item.period_start else default_start
        p_end = datetime.strptime(item.period_end, "%Y-%m-%d").date() if item.period_end else default_end
        row = models.ProjectBudget(
            client_id=client_id,
            channel=channel_enum,
            amount=item.amount,
            period_start=p_start,
            period_end=p_end,
        )
        db.add(row)
        created.append(row)

    log_history_event(
        db,
        actor=current_user,
        event_type="project",
        action="project_budgets_updated",
        description=f"Обновлены бюджеты проекта {client.name}",
        client_id=client.id,
        target_type="client",
        target_id=str(client.id),
        meta={"count": len(created)},
    )
    db.commit()
    for row in created:
        db.refresh(row)
    return created


# ── Target CPA ───────────────────────────────────────────────────────

@router.get("/{client_id}/target-cpa", response_model=List[schemas.ProjectTargetCPAResponse])
def get_target_cpa(
    client_id: uuid.UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    assert_project_access(db, current_user, client_id, write=False)
    rows = (
        db.query(models.ProjectTargetCPA)
        .filter(models.ProjectTargetCPA.client_id == client_id)
        .order_by(models.ProjectTargetCPA.period_start.desc(), models.ProjectTargetCPA.channel)
        .all()
    )
    return rows


@router.put("/{client_id}/target-cpa", response_model=List[schemas.ProjectTargetCPAResponse])
def set_target_cpa(
    client_id: uuid.UUID,
    items: List[schemas.ProjectTargetCPAItem] = Body(...),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    assert_project_access(db, current_user, client_id, write=True)
    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Проект не найден")

    db.query(models.ProjectTargetCPA).filter(models.ProjectTargetCPA.client_id == client_id).delete()

    default_start, default_end = _default_period()
    created = []
    for item in items:
        channel_enum = None
        if item.channel:
            channel_enum = _parse_platform(item.channel)
        elif item.integration_id:
            integration = db.query(models.Integration).filter(
                models.Integration.id == uuid.UUID(str(item.integration_id)),
                models.Integration.client_id == client_id,
            ).first()
            if integration:
                channel_enum = integration.platform

        p_start = datetime.strptime(item.period_start, "%Y-%m-%d").date() if item.period_start else default_start
        p_end = datetime.strptime(item.period_end, "%Y-%m-%d").date() if item.period_end else default_end

        row = models.ProjectTargetCPA(
            client_id=client_id,
            channel=channel_enum,
            goal_id=item.goal_id,
            goal_name=item.goal_name,
            is_summary=item.is_summary,
            target_cpa=item.target_cpa,
            control_enabled=item.control_enabled,
            period_start=p_start,
            period_end=p_end,
        )
        db.add(row)
        created.append(row)

    log_history_event(
        db,
        actor=current_user,
        event_type="project",
        action="project_target_cpa_updated",
        description=f"Обновлены целевые CPA проекта {client.name}",
        client_id=client.id,
        target_type="client",
        target_id=str(client.id),
        meta={"count": len(created)},
    )
    db.commit()
    for row in created:
        db.refresh(row)
    return created


def _parse_platform(value: str) -> models.IntegrationPlatform:
    normalized = value.upper().replace(" ", "_").replace("-", "_")
    try:
        return models.IntegrationPlatform(normalized)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Неизвестная платформа: {value}")
