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


def _platform_client_ids(db: Session, client_ids: list[UUID], platform, *, token_field="access_token") -> set[str]:
    """Из client_ids — те, у кого есть интеграция платформы с заполненными кредами."""
    if not client_ids:
        return set()
    col = getattr(models.Integration, token_field)
    rows = (
        db.query(models.Integration.client_id)
        .filter(
            models.Integration.client_id.in_(client_ids),
            models.Integration.platform == platform,
            col.isnot(None),
        )
        .all()
    )
    return {str(r[0]) for r in rows}


def list_accessible(db: Session, user: models.User) -> list[dict]:
    """[{id, name, platforms:{yandex,vk,avito}}] по доступным проектам."""
    ids = get_accessible_client_ids(db, user)
    if not ids:
        return []
    clients = db.query(models.Client.id, models.Client.name).filter(models.Client.id.in_(ids)).all()
    yandex = _platform_client_ids(db, ids, models.IntegrationPlatform.YANDEX_DIRECT)
    vk = _platform_client_ids(db, ids, models.IntegrationPlatform.VK_ADS)
    # У Avito токен-креды — platform_client_id (client_credentials), не access_token.
    avito = _platform_client_ids(db, ids, models.IntegrationPlatform.AVITO_ADS, token_field="platform_client_id")
    out = []
    for cid, name in clients:
        sid = str(cid)
        out.append({
            "id": sid,
            "name": name or "Без названия",
            "platforms": {"yandex": sid in yandex, "vk": sid in vk, "avito": sid in avito},
        })
    return out


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
