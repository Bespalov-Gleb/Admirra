from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from core import models, schemas, security
from backend_api.services.subscription import SubscriptionService, EffectivePlan
from backend_api.services.team_mail import send_team_invite_email
from backend_api.access_control import get_team_context
from backend_api.services.history import log_history_event

router = APIRouter(prefix="/team", tags=["Team"])


def _ensure_owner(current_user: models.User, db: Session) -> UUID:
    ctx = get_team_context(db, current_user)
    if not ctx.is_owner:
        raise HTTPException(status_code=403, detail="Только владелец может управлять командой")
    return ctx.account_id


def _member_to_response(member: models.TeamMember) -> schemas.TeamMemberResponse:
    full_name = None
    if member.user:
        full_name = " ".join(x for x in [member.user.first_name or "", member.user.last_name or ""] if x).strip() or member.user.username or member.user.email
    projects = [schemas.TeamProjectRef(id=p.project.id, name=p.project.name) for p in member.projects if p.project]
    return schemas.TeamMemberResponse(
        id=member.id,
        user_id=member.user_id,
        email=member.email,
        role=member.role.value,
        status=member.status.value,
        invited_at=member.invited_at,
        accepted_at=member.accepted_at,
        full_name=full_name,
        projects=projects,
    )


def _limit_for_role(plan: EffectivePlan, role: models.TeamMemberRole) -> int:
    if role == models.TeamMemberRole.MEMBER:
        return plan.max_staff
    return plan.max_clients


@router.get("/me-context", response_model=schemas.TeamContextResponse)
def get_me_context(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    ctx = get_team_context(db, current_user)
    return schemas.TeamContextResponse(is_owner=ctx.is_owner, team_role=ctx.team_role, account_id=ctx.account_id)


@router.get("/staff", response_model=list[schemas.TeamMemberResponse])
def get_staff(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    account_id = _ensure_owner(current_user, db)
    members = (
        db.query(models.TeamMember)
        .filter(
            models.TeamMember.account_id == account_id,
            models.TeamMember.role == models.TeamMemberRole.MEMBER,
        )
        .order_by(models.TeamMember.invited_at.desc())
        .all()
    )
    return [_member_to_response(m) for m in members]


@router.get("/members", response_model=list[schemas.TeamMemberResponse])
def get_members(
    role: str | None = None,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    account_id = _ensure_owner(current_user, db)
    query = db.query(models.TeamMember).filter(models.TeamMember.account_id == account_id)
    if role in {models.TeamMemberRole.MEMBER.value, models.TeamMemberRole.CLIENT.value}:
        query = query.filter(models.TeamMember.role == models.TeamMemberRole(role))
    members = query.order_by(models.TeamMember.invited_at.desc()).all()
    return [_member_to_response(m) for m in members]


@router.get("/clients", response_model=list[schemas.TeamMemberResponse])
def get_clients(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    account_id = _ensure_owner(current_user, db)
    members = (
        db.query(models.TeamMember)
        .filter(
            models.TeamMember.account_id == account_id,
            models.TeamMember.role == models.TeamMemberRole.CLIENT,
        )
        .order_by(models.TeamMember.invited_at.desc())
        .all()
    )
    return [_member_to_response(m) for m in members]


async def _invite_member(
    role: models.TeamMemberRole,
    payload: schemas.TeamInviteRequest,
    current_user: models.User,
    db: Session,
) -> schemas.TeamMemberResponse:
    account_id = _ensure_owner(current_user, db)
    plan = SubscriptionService.get_user_plan(db, current_user)
    role_limit = _limit_for_role(plan, role)

    current_count = (
        db.query(models.TeamMember)
        .filter(
            models.TeamMember.account_id == account_id,
            models.TeamMember.role == role,
        )
        .count()
    )
    if role_limit >= 0 and current_count >= role_limit and SubscriptionService.billing_enforced():
        log_history_event(
            db,
            actor=current_user,
            event_type="limit",
            action="team_role_limit_reached",
            description=f"Достигнут лимит приглашений для роли {role.value}",
            target_type="team_member",
            meta={"role": role.value, "limit": role_limit},
        )
        raise HTTPException(status_code=403, detail=f"Достигнут лимит {role.value} для тарифа. Обновите тариф.")

    existing = (
        db.query(models.TeamMember)
        .filter(models.TeamMember.account_id == account_id, models.TeamMember.email == payload.email.lower())
        .first()
    )
    if existing:
        if payload.role in {models.TeamMemberRole.MEMBER.value, models.TeamMemberRole.CLIENT.value}:
            new_role = models.TeamMemberRole(payload.role)
            if existing.role != new_role:
                old_role = existing.role.value
                existing.role = new_role
                db.add(existing)
                log_history_event(
                    db,
                    actor=current_user,
                    event_type="team",
                    action="member_role_changed",
                    description=f"Изменена роль участника {existing.email}: {old_role} -> {new_role.value}",
                    target_type="team_member",
                    target_id=str(existing.id),
                    meta={"old_role": old_role, "new_role": new_role.value},
                )
                db.commit()
                db.refresh(existing)
        return _member_to_response(existing)

    linked_user = db.query(models.User).filter(models.User.email == payload.email.lower()).first()
    status_value = models.TeamMemberStatus.ACTIVE if linked_user else models.TeamMemberStatus.PENDING
    now = datetime.now(timezone.utc)

    member = models.TeamMember(
        account_id=account_id,
        user_id=linked_user.id if linked_user else None,
        email=payload.email.lower(),
        role=role,
        status=status_value,
        invited_at=now,
        accepted_at=now if linked_user else None,
    )
    db.add(member)
    log_history_event(
        db,
        actor=current_user,
        event_type="team",
        action="member_invited",
        description=f"Приглашен {role.value}: {member.email}",
        target_type="team_member",
        target_id=str(member.id),
        meta={"role": role.value, "status": status_value.value},
    )
    db.commit()
    db.refresh(member)

    if not linked_user:
        await send_team_invite_email(member.email, current_user.email, "сотрудник" if role == models.TeamMemberRole.MEMBER else "клиент")
    return _member_to_response(member)


@router.post("/staff/invite", response_model=schemas.TeamMemberResponse, status_code=status.HTTP_201_CREATED)
async def invite_staff(
    payload: schemas.TeamInviteRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    return await _invite_member(models.TeamMemberRole.MEMBER, payload, current_user, db)


@router.post("/members/invite", response_model=schemas.TeamMemberResponse, status_code=status.HTTP_201_CREATED)
async def invite_member(
    payload: schemas.TeamInviteRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    role = models.TeamMemberRole.MEMBER
    if payload.role in {models.TeamMemberRole.MEMBER.value, models.TeamMemberRole.CLIENT.value}:
        role = models.TeamMemberRole(payload.role)
    return await _invite_member(role, payload, current_user, db)


@router.post("/clients/invite", response_model=schemas.TeamMemberResponse, status_code=status.HTTP_201_CREATED)
async def invite_client(
    payload: schemas.TeamInviteRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    return await _invite_member(models.TeamMemberRole.CLIENT, payload, current_user, db)


def _delete_member(user_id: UUID, role: models.TeamMemberRole, current_user: models.User, db: Session):
    account_id = _ensure_owner(current_user, db)
    member = (
        db.query(models.TeamMember)
        .filter(
            models.TeamMember.account_id == account_id,
            models.TeamMember.role == role,
            (models.TeamMember.user_id == user_id) | (models.TeamMember.id == user_id),
        )
        .first()
    )
    if not member:
        raise HTTPException(status_code=404, detail="Участник не найден")
    log_history_event(
        db,
        actor=current_user,
        event_type="team",
        action="member_removed",
        description=f"Удален участник {member.email}",
        target_type="team_member",
        target_id=str(member.id),
        meta={"role": member.role.value},
    )
    db.delete(member)
    db.commit()
    return {"ok": True}


@router.delete("/staff/{user_id}")
def delete_staff(
    user_id: UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    return _delete_member(user_id, models.TeamMemberRole.MEMBER, current_user, db)


@router.delete("/members/{member_id}")
def delete_member(
    member_id: UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    return _delete_member(member_id, models.TeamMemberRole.MEMBER, current_user, db)


@router.patch("/members/{member_id}", response_model=schemas.TeamMemberResponse)
def update_member(
    member_id: UUID,
    payload: schemas.TeamMemberUpdateRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    account_id = _ensure_owner(current_user, db)
    member = db.query(models.TeamMember).filter(
        models.TeamMember.id == member_id,
        models.TeamMember.account_id == account_id,
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Участник не найден")
    if payload.role not in {r.value for r in models.TeamMemberRole}:
        raise HTTPException(status_code=422, detail=f"Допустимые роли: member, client")
    old_role = member.role.value
    member.role = models.TeamMemberRole(payload.role)
    log_history_event(
        db, actor=current_user, event_type="team", action="member_role_changed",
        description=f"Роль {member.email} изменена: {old_role} → {payload.role}",
    )
    db.commit()
    db.refresh(member)
    return _member_to_response(member)


@router.delete("/clients/{user_id}")
def delete_client_member(
    user_id: UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    return _delete_member(user_id, models.TeamMemberRole.CLIENT, current_user, db)


def _find_member_by_user(account_id: UUID, user_id: UUID, role: models.TeamMemberRole, db: Session) -> models.TeamMember:
    member = (
        db.query(models.TeamMember)
        .filter(
            models.TeamMember.account_id == account_id,
            (models.TeamMember.user_id == user_id) | (models.TeamMember.id == user_id),
            models.TeamMember.role == role,
        )
        .first()
    )
    if not member:
        raise HTTPException(status_code=404, detail="Участник не найден")
    return member


@router.get("/staff/{user_id}/projects", response_model=list[schemas.TeamProjectRef])
def staff_projects(
    user_id: UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    account_id = _ensure_owner(current_user, db)
    member = _find_member_by_user(account_id, user_id, models.TeamMemberRole.MEMBER, db)
    return [schemas.TeamProjectRef(id=p.project.id, name=p.project.name) for p in member.projects if p.project]


@router.get("/members/{member_id}/projects", response_model=list[schemas.TeamProjectRef])
def member_projects(
    member_id: UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    account_id = _ensure_owner(current_user, db)
    member = _find_member_by_user(account_id, member_id, models.TeamMemberRole.MEMBER, db)
    return [schemas.TeamProjectRef(id=p.project.id, name=p.project.name) for p in member.projects if p.project]


@router.get("/clients/{user_id}/projects", response_model=list[schemas.TeamProjectRef])
def client_projects(
    user_id: UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    account_id = _ensure_owner(current_user, db)
    member = _find_member_by_user(account_id, user_id, models.TeamMemberRole.CLIENT, db)
    return [schemas.TeamProjectRef(id=p.project.id, name=p.project.name) for p in member.projects if p.project]


def _grant_project(
    role: models.TeamMemberRole,
    user_id: UUID,
    payload: schemas.TeamGrantProjectRequest,
    current_user: models.User,
    db: Session,
):
    account_id = _ensure_owner(current_user, db)
    member = _find_member_by_user(account_id, user_id, role, db)
    allowed_owner_ids = [account_id]
    member_user_ids = [
        row[0]
        for row in db.query(models.TeamMember.user_id).filter(
            models.TeamMember.account_id == account_id,
            models.TeamMember.role == models.TeamMemberRole.MEMBER,
            models.TeamMember.status == models.TeamMemberStatus.ACTIVE,
            models.TeamMember.user_id.isnot(None),
        ).all()
    ]
    allowed_owner_ids.extend(member_user_ids)
    project = db.query(models.Client).filter(
        models.Client.id == payload.project_id,
        models.Client.owner_id.in_(allowed_owner_ids),
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")

    existing = (
        db.query(models.TeamMemberProject)
        .filter(
            models.TeamMemberProject.team_member_id == member.id,
            models.TeamMemberProject.project_id == project.id,
        )
        .first()
    )
    if existing:
        return {"ok": True}

    link = models.TeamMemberProject(team_member_id=member.id, project_id=project.id, granted_by=current_user.id)
    db.add(link)
    log_history_event(
        db,
        actor=current_user,
        event_type="team",
        action="project_access_granted",
        description=f"Выдан доступ к проекту {project.name} для {member.email}",
        client_id=project.id,
        target_type="team_member_project",
        target_id=str(link.id),
        meta={"role": role.value, "member_id": str(member.id)},
    )
    db.commit()
    return {"ok": True}


@router.post("/staff/{user_id}/projects")
def grant_staff_project(
    user_id: UUID,
    payload: schemas.TeamGrantProjectRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    return _grant_project(models.TeamMemberRole.MEMBER, user_id, payload, current_user, db)


@router.post("/members/{member_id}/projects")
def grant_member_project(
    member_id: UUID,
    payload: schemas.TeamGrantProjectRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    return _grant_project(models.TeamMemberRole.MEMBER, member_id, payload, current_user, db)


@router.post("/clients/{user_id}/projects")
def grant_client_project(
    user_id: UUID,
    payload: schemas.TeamGrantProjectRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    return _grant_project(models.TeamMemberRole.CLIENT, user_id, payload, current_user, db)


def _revoke_project(
    role: models.TeamMemberRole,
    user_id: UUID,
    project_id: UUID,
    current_user: models.User,
    db: Session,
):
    account_id = _ensure_owner(current_user, db)
    member = _find_member_by_user(account_id, user_id, role, db)
    link = (
        db.query(models.TeamMemberProject)
        .filter(
            models.TeamMemberProject.team_member_id == member.id,
            models.TeamMemberProject.project_id == project_id,
        )
        .first()
    )
    if not link:
        raise HTTPException(status_code=404, detail="Доступ не найден")
    log_history_event(
        db,
        actor=current_user,
        event_type="team",
        action="project_access_revoked",
        description=f"Отозван доступ к проекту у {member.email}",
        client_id=project_id,
        target_type="team_member_project",
        target_id=str(link.id),
        meta={"role": role.value, "member_id": str(member.id)},
    )
    db.delete(link)
    db.commit()
    return {"ok": True}


@router.delete("/staff/{user_id}/projects/{project_id}")
def revoke_staff_project(
    user_id: UUID,
    project_id: UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    return _revoke_project(models.TeamMemberRole.MEMBER, user_id, project_id, current_user, db)


@router.delete("/members/{member_id}/projects/{project_id}")
def revoke_member_project(
    member_id: UUID,
    project_id: UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    return _revoke_project(models.TeamMemberRole.MEMBER, member_id, project_id, current_user, db)


@router.get("/projects", response_model=list[schemas.TeamProjectRef])
def get_team_projects(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    account_id = _ensure_owner(current_user, db)
    owner_projects = db.query(models.Client.id, models.Client.name).filter(models.Client.owner_id == account_id).all()
    member_user_ids = [
        r[0]
        for r in (
            db.query(models.TeamMember.user_id)
            .filter(
                models.TeamMember.account_id == account_id,
                models.TeamMember.role == models.TeamMemberRole.MEMBER,
                models.TeamMember.status == models.TeamMemberStatus.ACTIVE,
                models.TeamMember.user_id.isnot(None),
            )
            .all()
        )
    ]
    member_projects = []
    if member_user_ids:
        member_projects = db.query(models.Client.id, models.Client.name).filter(models.Client.owner_id.in_(member_user_ids)).all()
    uniq = {}
    for pid, name in list(owner_projects) + list(member_projects):
        uniq[str(pid)] = schemas.TeamProjectRef(id=pid, name=name)
    return list(uniq.values())


@router.delete("/clients/{user_id}/projects/{project_id}")
def revoke_client_project(
    user_id: UUID,
    project_id: UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    return _revoke_project(models.TeamMemberRole.CLIENT, user_id, project_id, current_user, db)
