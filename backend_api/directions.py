import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core import models, schemas, security
from core.database import get_db
from backend_api.access_control import assert_project_access
from backend_api.services import directions as direction_service
from backend_api.services.history import log_history_event


router = APIRouter(prefix="/clients/{client_id}/directions", tags=["Project directions"])


def _client_or_404(db: Session, client_id: uuid.UUID) -> models.Client:
    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Проект не найден")
    return client


def _set_masks(db: Session, direction: models.ProjectDirection, masks: list[str]) -> None:
    direction.masks.clear()
    db.flush()
    for index, mask in enumerate(direction_service.clean_masks(masks)):
        direction.masks.append(models.ProjectDirectionMask(mask=mask, position=index))


@router.get("/", response_model=list[schemas.ProjectDirectionResponse])
def list_directions(
    client_id: uuid.UUID,
    platform: str = Query("all"),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    assert_project_access(db, current_user, client_id, write=False)
    matches = direction_service.build_direction_matches(db, client_id, platform=platform, include_inactive=True)
    return [
        direction_service.serialize_direction(
            direction,
            matches["direction_to_campaigns"].get(str(direction.id), []),
        )
        for direction in matches["directions"]
    ]


@router.post("/", response_model=schemas.ProjectDirectionResponse, status_code=status.HTTP_201_CREATED)
def create_direction(
    client_id: uuid.UUID,
    body: schemas.ProjectDirectionCreate,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    assert_project_access(db, current_user, client_id, write=True)
    client = _client_or_404(db, client_id)
    masks = direction_service.clean_masks(body.masks)
    if not masks:
        raise HTTPException(status_code=400, detail="Добавьте хотя бы одно ключевое слово")

    position = body.position
    if position is None:
        max_position = (
            db.query(models.ProjectDirection.position)
            .filter(models.ProjectDirection.client_id == client_id)
            .order_by(models.ProjectDirection.position.desc())
            .first()
        )
        position = int(max_position[0] + 1) if max_position else 0

    direction = models.ProjectDirection(
        client_id=client_id,
        name=body.name.strip(),
        position=position,
    )
    db.add(direction)
    db.flush()
    _set_masks(db, direction, masks)
    log_history_event(
        db,
        actor=current_user,
        event_type="project",
        action="project_direction_created",
        description=f"Создано направление {direction.name} в проекте {client.name}",
        client_id=client.id,
        target_type="project_direction",
        target_id=str(direction.id),
        meta={"masks": masks},
    )
    db.commit()
    db.refresh(direction)
    matches = direction_service.build_direction_matches(db, client_id, include_inactive=True)
    return direction_service.serialize_direction(direction, matches["direction_to_campaigns"].get(str(direction.id), []))


@router.patch("/{direction_id}", response_model=schemas.ProjectDirectionResponse)
def update_direction(
    client_id: uuid.UUID,
    direction_id: uuid.UUID,
    body: schemas.ProjectDirectionUpdate,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    assert_project_access(db, current_user, client_id, write=True)
    direction = (
        db.query(models.ProjectDirection)
        .filter(models.ProjectDirection.id == direction_id, models.ProjectDirection.client_id == client_id)
        .first()
    )
    if not direction:
        raise HTTPException(status_code=404, detail="Направление не найдено")

    if body.name is not None:
        direction.name = body.name.strip()
    if body.position is not None:
        direction.position = body.position
    if body.is_active is not None:
        direction.is_active = body.is_active
    if body.masks is not None:
        masks = direction_service.clean_masks(body.masks)
        if not masks:
            raise HTTPException(status_code=400, detail="Добавьте хотя бы одно ключевое слово")
        _set_masks(db, direction, masks)
    db.commit()
    db.refresh(direction)
    matches = direction_service.build_direction_matches(db, client_id, include_inactive=True)
    return direction_service.serialize_direction(direction, matches["direction_to_campaigns"].get(str(direction.id), []))


@router.delete("/{direction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_direction(
    client_id: uuid.UUID,
    direction_id: uuid.UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    assert_project_access(db, current_user, client_id, write=True)
    direction = (
        db.query(models.ProjectDirection)
        .filter(models.ProjectDirection.id == direction_id, models.ProjectDirection.client_id == client_id)
        .first()
    )
    if not direction:
        raise HTTPException(status_code=404, detail="Направление не найдено")
    db.delete(direction)
    db.commit()
    return None


@router.post("/reorder", response_model=list[schemas.ProjectDirectionResponse])
def reorder_directions(
    client_id: uuid.UUID,
    body: schemas.DirectionReorderRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    assert_project_access(db, current_user, client_id, write=True)
    directions = (
        db.query(models.ProjectDirection)
        .filter(models.ProjectDirection.client_id == client_id, models.ProjectDirection.id.in_(body.direction_ids))
        .all()
    )
    by_id = {direction.id: direction for direction in directions}
    for index, direction_id in enumerate(body.direction_ids):
        if direction_id in by_id:
            by_id[direction_id].position = index
    db.commit()
    matches = direction_service.build_direction_matches(db, client_id, include_inactive=True)
    return [
        direction_service.serialize_direction(direction, matches["direction_to_campaigns"].get(str(direction.id), []))
        for direction in matches["directions"]
    ]


@router.put("/label", response_model=dict)
def update_direction_label(
    client_id: uuid.UUID,
    body: schemas.DirectionLabelUpdate,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    assert_project_access(db, current_user, client_id, write=True)
    client = _client_or_404(db, client_id)
    client.direction_label = direction_service.normalize_label(body.label)
    db.commit()
    return {
        "label_key": client.direction_label,
        "label": direction_service.LABELS.get(client.direction_label, "Направления"),
    }


@router.post("/preview", response_model=schemas.DirectionPreviewResponse)
def preview_direction(
    client_id: uuid.UUID,
    body: schemas.DirectionPreviewRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    assert_project_access(db, current_user, client_id, write=False)
    return direction_service.preview_masks(
        db,
        client_id,
        body.masks,
        platform=body.platform or "all",
        exclude_direction_id=body.exclude_direction_id,
    )


@router.get("/suggestions", response_model=list[schemas.DirectionSuggestion])
def suggest_directions(
    client_id: uuid.UUID,
    platform: str = Query("all"),
    unassigned_only: bool = Query(False),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    assert_project_access(db, current_user, client_id, write=False)
    return direction_service.suggest_directions(
        db,
        client_id,
        platform=platform,
        only_unassigned=unassigned_only,
    )


@router.get("/stats", response_model=schemas.DirectionStatsResponse)
def get_direction_stats(
    client_id: uuid.UUID,
    start_date: str | None = None,
    end_date: str | None = None,
    platform: str = Query("all"),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    assert_project_access(db, current_user, client_id, write=False)
    client = _client_or_404(db, client_id)
    d_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else datetime.utcnow().date()
    d_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else d_end - timedelta(days=13)
    return direction_service.direction_stats(db, client, d_start, d_end, platform=platform)
