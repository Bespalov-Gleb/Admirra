"""Проекты, доступные пользователю ассистента, и резолв проекта по названию.

Даёт агенту возможность «написать название — найду сам»: инструменты
list_projects/use_project работают только в пределах accessible_client_ids
(изоляция сохраняется)."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from core import models
from backend_api.access_control import get_accessible_client_ids


def _yandex_client_ids(db: Session, client_ids: list[UUID]) -> set[str]:
    """Из client_ids — те, у кого есть Yandex Direct интеграция с токеном."""
    if not client_ids:
        return set()
    rows = (
        db.query(models.Integration.client_id)
        .filter(
            models.Integration.client_id.in_(client_ids),
            models.Integration.platform == models.IntegrationPlatform.YANDEX_DIRECT,
            models.Integration.access_token.isnot(None),
        )
        .all()
    )
    return {str(r[0]) for r in rows}


def list_accessible(db: Session, user: models.User) -> list[dict]:
    """[{id, name, yandex}] по проектам, к которым у пользователя есть доступ."""
    ids = get_accessible_client_ids(db, user)
    if not ids:
        return []
    clients = db.query(models.Client.id, models.Client.name).filter(models.Client.id.in_(ids)).all()
    yandex = _yandex_client_ids(db, ids)
    return [{"id": str(cid), "name": name or "Без названия", "yandex": str(cid) in yandex} for cid, name in clients]


def resolve(db: Session, user: models.User, query: str) -> dict:
    """Ищет проект по id или названию среди доступных.

    Возвращает {"project": {...}} при однозначном совпадении, либо
    {"error": ...} / {"candidates": [...]} для агента."""
    q = (query or "").strip()
    if not q:
        return {"error": "Укажите название или id проекта"}
    projects = list_accessible(db, user)
    if not projects:
        return {"error": "У вас нет доступных проектов"}

    # Точное совпадение по id.
    for p in projects:
        if p["id"] == q:
            return {"project": p}

    ql = q.lower()
    exact = [p for p in projects if p["name"].lower() == ql]
    if len(exact) == 1:
        return {"project": exact[0]}

    partial = [p for p in projects if ql in p["name"].lower()]
    if len(partial) == 1:
        return {"project": partial[0]}
    if len(partial) > 1:
        return {"candidates": [{"id": p["id"], "name": p["name"]} for p in partial[:10]],
                "error": "Несколько проектов подходят — уточните название"}
    return {"error": f"Проект «{query}» не найден среди доступных"}
