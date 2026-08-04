"""Папки проектов: группировка проектов (филиалов одного заказчика) со сводной
статистикой. Папка — контейнер на чтение: синк, детектор и цели остаются на уровне
проекта/кабинета, сводка считается как агрегат по вложенным проектам.

Правило лимита: папка занимает 1 слот проекта (пока в ней есть активный проект),
вложенные проекты слоты не занимают. Реальный ограничитель — глобальный лимит кабинетов.
"""
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend_api.access_control import get_accessible_client_ids, get_team_context
from backend_api.services.history import log_history_event
from backend_api.services.subscription import SubscriptionService
from backend_api.stats_service import StatsService
from core import models, schemas, security
from core.database import get_db

router = APIRouter(prefix="/folders", tags=["Folders"])


def _assert_can_manage(ctx) -> None:
    if not ctx.is_owner and ctx.team_role == models.TeamMemberRole.CLIENT.value:
        raise HTTPException(status_code=403, detail="Недостаточно прав для управления папками")


def _get_folder(db: Session, ctx, folder_id: uuid.UUID) -> models.Folder:
    folder = db.query(models.Folder).filter(
        models.Folder.id == folder_id,
        models.Folder.account_id == ctx.account_id,
    ).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Папка не найдена")
    return folder


def _folder_counts(db: Session, folder_ids: List[uuid.UUID]) -> dict:
    out = {fid: {"total": 0, "active": 0} for fid in folder_ids}
    if not folder_ids:
        return out
    rows = db.query(models.Client.folder_id, models.Client.status).filter(
        models.Client.folder_id.in_(folder_ids)
    ).all()
    for fid, st in rows:
        if fid in out:
            out[fid]["total"] += 1
            if st == models.ClientStatus.ACTIVE:
                out[fid]["active"] += 1
    return out


def _folder_to_schema(folder: models.Folder, counts: dict) -> schemas.FolderResponse:
    c = counts.get(folder.id, {"total": 0, "active": 0})
    return schemas.FolderResponse(
        id=folder.id,
        account_id=folder.account_id,
        name=folder.name,
        color=folder.color,
        avatar_url=folder.avatar_url,
        sort_order=folder.sort_order or 0,
        projects_count=c["total"],
        active_projects_count=c["active"],
        created_at=folder.created_at,
    )


def _accessible_clients(db: Session, current_user: models.User) -> List[models.Client]:
    ids = get_accessible_client_ids(db, current_user)
    if not ids:
        return []
    return db.query(models.Client).filter(models.Client.id.in_(ids)).all()


def _assign_projects(db: Session, ctx, current_user, folder: models.Folder, project_ids: List[uuid.UUID]) -> int:
    """Назначает доступные проекты в папку. Возвращает число перемещённых."""
    if not project_ids:
        return 0
    accessible = set(get_accessible_client_ids(db, current_user))
    moved = 0
    for pid in project_ids:
        if pid not in accessible:
            continue
        client = db.query(models.Client).filter(models.Client.id == pid).first()
        if client:
            client.folder_id = folder.id
            moved += 1
    return moved


@router.get("/", response_model=List[schemas.FolderResponse])
def list_folders(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    ctx = get_team_context(db, current_user)
    folders = (
        db.query(models.Folder)
        .filter(models.Folder.account_id == ctx.account_id)
        .order_by(models.Folder.sort_order, models.Folder.created_at)
        .all()
    )
    # Сотрудник/клиент видит только папки, где есть хотя бы один доступный ему
    # проект — иначе папки владельца «протекали» в чужой аккаунт.
    if not ctx.is_owner:
        accessible = set(get_accessible_client_ids(db, current_user))
        folder_ids_with_access = set()
        if accessible:
            folder_ids_with_access = {
                row[0]
                for row in db.query(models.Client.folder_id)
                .filter(
                    models.Client.folder_id.isnot(None),
                    models.Client.id.in_(accessible),
                )
                .distinct()
                .all()
            }
        folders = [f for f in folders if f.id in folder_ids_with_access]
    counts = _folder_counts(db, [f.id for f in folders])
    return [_folder_to_schema(f, counts) for f in folders]


@router.post("/", response_model=schemas.FolderResponse, status_code=status.HTTP_201_CREATED)
def create_folder(
    body: schemas.FolderCreate,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    ctx = get_team_context(db, current_user)
    _assert_can_manage(ctx)
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="Укажите название папки")
    max_order = (
        db.query(models.Folder.sort_order)
        .filter(models.Folder.account_id == ctx.account_id)
        .order_by(models.Folder.sort_order.desc())
        .first()
    )
    folder = models.Folder(
        account_id=ctx.account_id,
        name=name,
        color=body.color,
        avatar_url=body.avatar_url,
        sort_order=(max_order[0] + 1) if max_order else 0,
    )
    db.add(folder)
    db.flush()
    _assign_projects(db, ctx, current_user, folder, body.project_ids)
    log_history_event(
        db,
        actor=current_user,
        event_type="project",
        action="folder_created",
        description=f"Создана папка «{folder.name}»",
        target_type="folder",
        target_id=str(folder.id),
        meta={"projects": len(body.project_ids or [])},
    )
    db.commit()
    db.refresh(folder)
    counts = _folder_counts(db, [folder.id])
    return _folder_to_schema(folder, counts)


@router.put("/{folder_id}", response_model=schemas.FolderResponse)
def update_folder(
    folder_id: uuid.UUID,
    body: schemas.FolderUpdate,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    ctx = get_team_context(db, current_user)
    _assert_can_manage(ctx)
    folder = _get_folder(db, ctx, folder_id)
    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise HTTPException(status_code=422, detail="Название папки не может быть пустым")
        folder.name = name
    if body.color is not None:
        folder.color = body.color or None
    if body.avatar_url is not None:
        folder.avatar_url = body.avatar_url or None
    if body.sort_order is not None:
        folder.sort_order = int(body.sort_order)
    db.commit()
    db.refresh(folder)
    counts = _folder_counts(db, [folder.id])
    return _folder_to_schema(folder, counts)


@router.delete("/{folder_id}")
def delete_folder(
    folder_id: uuid.UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """Удаление папки = разгруппировка: проекты сохраняются и возвращаются в корень."""
    ctx = get_team_context(db, current_user)
    _assert_can_manage(ctx)
    folder = _get_folder(db, ctx, folder_id)
    ungrouped = (
        db.query(models.Client)
        .filter(models.Client.folder_id == folder.id)
        .update({models.Client.folder_id: None}, synchronize_session=False)
    )
    log_history_event(
        db,
        actor=current_user,
        event_type="project",
        action="folder_deleted",
        description=f"Удалена папка «{folder.name}» (проекты разгруппированы: {ungrouped})",
        target_type="folder",
        target_id=str(folder.id),
    )
    db.delete(folder)
    db.commit()
    return {"ok": True, "ungrouped_projects": int(ungrouped or 0)}


@router.post("/{folder_id}/assign", response_model=schemas.FolderResponse)
def assign_projects(
    folder_id: uuid.UUID,
    body: schemas.FolderAssignRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    ctx = get_team_context(db, current_user)
    _assert_can_manage(ctx)
    folder = _get_folder(db, ctx, folder_id)
    moved = _assign_projects(db, ctx, current_user, folder, body.project_ids)
    log_history_event(
        db,
        actor=current_user,
        event_type="project",
        action="folder_projects_assigned",
        description=f"В папку «{folder.name}» перемещено проектов: {moved}",
        target_type="folder",
        target_id=str(folder.id),
    )
    db.commit()
    counts = _folder_counts(db, [folder.id])
    return _folder_to_schema(folder, counts)


@router.post("/unassign")
def unassign_projects(
    body: schemas.FolderAssignRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """Вынос проектов из папки в корень. Вынос занимает слот проекта —
    проверяем лимит тарифа ДО фиксации (иначе папкой можно было бы обойти лимит)."""
    ctx = get_team_context(db, current_user)
    _assert_can_manage(ctx)
    accessible = set(get_accessible_client_ids(db, current_user))
    moved = 0
    for pid in body.project_ids or []:
        if pid not in accessible:
            continue
        client = db.query(models.Client).filter(models.Client.id == pid).first()
        if client and client.folder_id:
            client.folder_id = None
            moved += 1
    if moved:
        db.flush()
        # Считаем слоты уже с учётом выноса; при превышении — откат
        plan = SubscriptionService.get_user_plan(db, current_user)
        slots = SubscriptionService.count_project_slots(db, current_user.id)
        if (
            slots > int(plan.max_projects or 0)
            and SubscriptionService.billing_enforced()
            and not SubscriptionService.is_admin_bypass(current_user)
        ):
            db.rollback()
            raise HTTPException(
                status_code=403,
                detail=f"Вынос из папки занимает слот проекта: лимит тарифа «{plan.name}» ({plan.max_projects}) будет превышен",
            )
    db.commit()
    return {"ok": True, "moved": moved}


@router.get("/tree", response_model=schemas.ProjectsTreeResponse)
def projects_tree(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    with_stats: bool = Query(True),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """Дерево списка проектов: корень = папки + проекты вне папок.
    Сводка папки — сумма по вложенным ДОСТУПНЫМ проектам (member видит только свою часть).
    """
    ctx = get_team_context(db, current_user)
    d_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else datetime.utcnow().date()
    d_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else d_end - timedelta(days=6)

    folders = (
        db.query(models.Folder)
        .filter(models.Folder.account_id == ctx.account_id)
        .order_by(models.Folder.sort_order, models.Folder.created_at)
        .all()
    )
    folder_ids = {f.id for f in folders}
    counts = _folder_counts(db, list(folder_ids))
    clients = _accessible_clients(db, current_user)

    def client_resp(c: models.Client) -> schemas.ClientResponse:
        if with_stats:
            c.summary = StatsService.aggregate_summary(db, [c.id], d_start, d_end)
        return schemas.ClientResponse.model_validate(c)

    root_projects = []
    by_folder: dict = {fid: [] for fid in folder_ids}
    for c in clients:
        if c.folder_id and c.folder_id in folder_ids:
            by_folder[c.folder_id].append(c)
        else:
            root_projects.append(c)

    tree_folders: List[schemas.FolderTreeItem] = []
    for f in folders:
        members = by_folder.get(f.id, [])
        # Member без доступных проектов в папке не видит её вовсе
        if not ctx.is_owner and not members:
            continue
        summary = None
        if with_stats and members:
            summary = StatsService.aggregate_summary(db, [c.id for c in members], d_start, d_end)
        base = _folder_to_schema(f, counts)
        tree_folders.append(
            schemas.FolderTreeItem(
                **base.model_dump(),
                summary=summary,
                projects=[client_resp(c) for c in members],
            )
        )

    return schemas.ProjectsTreeResponse(
        folders=tree_folders,
        root_projects=[client_resp(c) for c in root_projects],
    )


@router.get("/{folder_id}/breakdown")
def folder_breakdown(
    folder_id: uuid.UUID,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """Разбивка сводки папки по филиалам (для аналитики папки: уровень «по филиалам»)."""
    ctx = get_team_context(db, current_user)
    folder = _get_folder(db, ctx, folder_id)
    d_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else datetime.utcnow().date()
    d_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else d_end - timedelta(days=6)
    accessible = set(get_accessible_client_ids(db, current_user))
    members = [
        c for c in db.query(models.Client).filter(models.Client.folder_id == folder.id).all()
        if c.id in accessible
    ]
    def _with_combined_leads_cpl(client_ids):
        """Лиды/CPL филиала — по той же формуле, что и KPI сводки (ТЗ единого
        дашборда п.13): лиды = сумма по каналам (Яндекс — выбранные цели, VK —
        лидовые действия, Авито — по UTM); CPL = сумма лидовых расходов ÷ лиды.
        Базовый aggregate_summary(all) для смешанных Яндекс+VK отдаёт лиды только
        Яндекса и CPL от всего расхода, поэтому пересобираем по каналам."""
        summary = StatsService.aggregate_summary(db, client_ids, d_start, d_end)
        total_leads = 0
        lead_cost = 0.0
        for plat in ("yandex", "vk", "avito"):
            s = StatsService.aggregate_summary(db, client_ids, d_start, d_end, plat)
            total_leads += int(s.get("leads") or 0)
            lead_cost += float((s.get("lead_cost_by_platform") or {}).get(plat) or 0)
        summary["leads"] = total_leads
        summary["cpa"] = round(lead_cost / total_leads, 2) if total_leads > 0 else 0
        summary["leads_available"] = True
        summary["cpa_available"] = True
        return summary

    items = []
    for c in members:
        # summary уже содержит balance филиала (Integration.balance активных
        # интеграций) — отдельный запрос не нужен.
        items.append({
            "client_id": str(c.id),
            "name": c.name,
            "status": c.status.value.lower() if hasattr(c.status, "value") else str(c.status).lower(),
            "avatar_url": c.avatar_url,
            "summary": _with_combined_leads_cpl([c.id]),
        })
    total = _with_combined_leads_cpl([c.id for c in members]) if members else None
    return {
        "folder": _folder_to_schema(folder, _folder_counts(db, [folder.id])).model_dump(mode="json"),
        "total": total,
        "items": items,
    }
