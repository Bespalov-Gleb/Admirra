from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from core import models


@dataclass
class TeamContext:
    is_owner: bool
    account_id: UUID
    team_role: Optional[str] = None
    team_member_id: Optional[UUID] = None


def get_team_context(db: Session, user: models.User) -> TeamContext:
    membership = (
        db.query(models.TeamMember)
        .filter(
            models.TeamMember.user_id == user.id,
            models.TeamMember.status == models.TeamMemberStatus.ACTIVE,
        )
        .first()
    )
    if membership:
        return TeamContext(
            is_owner=False,
            account_id=membership.account_id,
            team_role=membership.role.value,
            team_member_id=membership.id,
        )

    owner_client_exists = (
        db.query(models.Client.id)
        .filter(models.Client.owner_id == user.id)
        .first()
    )
    if owner_client_exists:
        return TeamContext(is_owner=True, account_id=user.id)
    return TeamContext(is_owner=True, account_id=user.id)


def get_accessible_client_ids(db: Session, user: models.User) -> list[UUID]:
    ctx = get_team_context(db, user)
    if ctx.is_owner:
        own = db.query(models.Client.id).filter(models.Client.owner_id == ctx.account_id).all()
        member_user_ids = (
            db.query(models.TeamMember.user_id)
            .filter(
                models.TeamMember.account_id == ctx.account_id,
                models.TeamMember.role == models.TeamMemberRole.MEMBER,
                models.TeamMember.status == models.TeamMemberStatus.ACTIVE,
                models.TeamMember.user_id.isnot(None),
            )
            .all()
        )
        member_user_ids = [r[0] for r in member_user_ids]
        from_members = []
        if member_user_ids:
            from_members = db.query(models.Client.id).filter(models.Client.owner_id.in_(member_user_ids)).all()
        return [r[0] for r in own] + [r[0] for r in from_members]

    # Member sees own projects + explicitly shared projects.
    if ctx.team_role == models.TeamMemberRole.MEMBER.value:
        own = db.query(models.Client.id).filter(models.Client.owner_id == user.id).all()
        shared = (
            db.query(models.TeamMemberProject.project_id)
            .join(models.TeamMember, models.TeamMember.id == models.TeamMemberProject.team_member_id)
            .join(models.Client, models.Client.id == models.TeamMemberProject.project_id)
            .filter(
                models.TeamMember.id == ctx.team_member_id,
                models.TeamMember.status == models.TeamMemberStatus.ACTIVE,
                models.Client.owner_id != user.id,
            )
            .all()
        )
        return [r[0] for r in own] + [r[0] for r in shared]

    # Client sees only explicitly shared projects.
    rows = (
        db.query(models.TeamMemberProject.project_id)
        .join(models.TeamMember, models.TeamMember.id == models.TeamMemberProject.team_member_id)
        .join(models.Client, models.Client.id == models.TeamMemberProject.project_id)
        .filter(
            models.TeamMember.id == ctx.team_member_id,
            models.TeamMember.status == models.TeamMemberStatus.ACTIVE,
            models.Client.owner_id == ctx.account_id,
        )
        .all()
    )
    return [r[0] for r in rows]


def can_write_project(db: Session, user: models.User, project_id: UUID) -> bool:
    ctx = get_team_context(db, user)
    if ctx.is_owner:
        return db.query(models.Client.id).filter(models.Client.id == project_id, models.Client.owner_id == ctx.account_id).first() is not None
    if ctx.team_role == models.TeamMemberRole.MEMBER.value:
        own = db.query(models.Client.id).filter(models.Client.id == project_id, models.Client.owner_id == user.id).first()
        if own:
            return True
        return (
            db.query(models.TeamMemberProject.id)
            .join(models.Client, models.Client.id == models.TeamMemberProject.project_id)
            .filter(
                models.TeamMemberProject.team_member_id == ctx.team_member_id,
                models.TeamMemberProject.project_id == project_id,
                models.Client.owner_id == ctx.account_id,
            )
            .first()
            is not None
        )
    return False


def assert_project_access(db: Session, user: models.User, project_id: UUID, write: bool = False, allow_client_ai: bool = False) -> TeamContext:
    ctx = get_team_context(db, user)
    if ctx.is_owner:
        exists = db.query(models.Client.id).filter(models.Client.id == project_id, models.Client.owner_id == ctx.account_id).first()
        if exists:
            return ctx
        raise HTTPException(status_code=404, detail="Client not found")

    own_member_project = (
        db.query(models.Client.id)
        .filter(models.Client.id == project_id, models.Client.owner_id == user.id)
        .first()
    )
    if own_member_project and ctx.team_role == models.TeamMemberRole.MEMBER.value:
        return ctx

    link_exists = (
        db.query(models.TeamMemberProject.id)
        .join(models.Client, models.Client.id == models.TeamMemberProject.project_id)
        .filter(
            models.TeamMemberProject.team_member_id == ctx.team_member_id,
            models.TeamMemberProject.project_id == project_id,
            models.Client.owner_id == ctx.account_id,
        )
        .first()
    )
    if not link_exists:
        raise HTTPException(status_code=403, detail="Нет доступа к проекту")

    if write and ctx.team_role == models.TeamMemberRole.CLIENT.value and not allow_client_ai:
        raise HTTPException(status_code=403, detail="Клиенту недоступно изменение проекта")
    return ctx
