"""
API для управления проектами телефонии (валидация телефонов).
Проекты независимы - разные node, аналогично Client для интеграций.
"""

import logging
import secrets
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from core.database import get_db
from core import models, security
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/phone-projects", tags=["Phone Projects"])


# ============================================================================
# Schemas
# ============================================================================

class PhoneProjectCreate(BaseModel):
    """Создание проекта телефонии"""
    name: str = Field(..., description="Название проекта")
    description: Optional[str] = None
    client_id: Optional[uuid.UUID] = None  # Связь с клиентом (опционально)
    
    # Настройки выгрузки
    crm_webhook_url: Optional[str] = None
    email_recipients: Optional[List[str]] = None  # Список email адресов
    telegram_chat_id: Optional[str] = None
    
    # Настройки валидации
    enable_social_check: bool = False
    enable_gosuslugi_check: bool = False
    enable_metrica_export: bool = True


class PhoneProjectUpdate(BaseModel):
    """Обновление проекта телефонии"""
    name: Optional[str] = None
    description: Optional[str] = None
    client_id: Optional[uuid.UUID] = None
    
    # Настройки выгрузки
    crm_webhook_url: Optional[str] = None
    email_recipients: Optional[List[str]] = None
    telegram_chat_id: Optional[str] = None
    
    # Настройки валидации
    enable_social_check: Optional[bool] = None
    enable_gosuslugi_check: Optional[bool] = None
    enable_metrica_export: Optional[bool] = None
    is_active: Optional[bool] = None


class PhoneProjectResponse(BaseModel):
    """Ответ с данными проекта"""
    id: uuid.UUID
    name: str
    description: Optional[str]
    client_id: Optional[uuid.UUID]
    webhook_url: Optional[str]
    webhook_secret: Optional[str]
    
    # Настройки выгрузки
    crm_webhook_url: Optional[str]
    email_recipients: Optional[List[str]]
    telegram_chat_id: Optional[str]
    
    # Настройки валидации
    enable_social_check: bool
    enable_gosuslugi_check: bool
    enable_metrica_export: bool
    
    # Метаданные
    created_at: datetime
    updated_at: Optional[datetime]
    is_active: bool
    
    class Config:
        from_attributes = True


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/", response_model=List[PhoneProjectResponse])
def get_phone_projects(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """Получить список всех проектов телефонии пользователя"""
    projects = db.query(models.PhoneProject).filter(
        models.PhoneProject.owner_id == current_user.id
    ).all()
    
    return projects


@router.post("/", response_model=PhoneProjectResponse)
def create_phone_project(
    project_data: PhoneProjectCreate,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """Создать новый проект телефонии"""
    import json
    
    # Генерируем уникальный webhook URL и секрет
    webhook_secret = secrets.token_urlsafe(32)
    webhook_path = f"/webhook/phone/{uuid.uuid4().hex[:16]}"
    
    # Преобразуем email_recipients в JSON строку
    email_recipients_json = None
    if project_data.email_recipients:
        email_recipients_json = json.dumps(project_data.email_recipients)
    
    # Проверяем client_id если указан
    if project_data.client_id:
        client = db.query(models.Client).filter_by(id=project_data.client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        if client.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied to this client")
    
    project = models.PhoneProject(
        owner_id=current_user.id,
        client_id=project_data.client_id,
        name=project_data.name,
        description=project_data.description,
        webhook_url=webhook_path,
        webhook_secret=webhook_secret,
        crm_webhook_url=project_data.crm_webhook_url,
        email_recipients=email_recipients_json,
        telegram_chat_id=project_data.telegram_chat_id,
        enable_social_check=project_data.enable_social_check,
        enable_gosuslugi_check=project_data.enable_gosuslugi_check,
        enable_metrica_export=project_data.enable_metrica_export
    )
    
    db.add(project)
    db.commit()
    db.refresh(project)
    
    logger.info(f"Created phone project: {project.id} ({project.name})")
    
    # Преобразуем email_recipients обратно в список для ответа
    response_data = PhoneProjectResponse.from_orm(project)
    if project.email_recipients:
        response_data.email_recipients = json.loads(project.email_recipients)
    
    return response_data


@router.get("/{project_id}", response_model=PhoneProjectResponse)
def get_phone_project(
    project_id: uuid.UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """Получить проект телефонии по ID"""
    project = db.query(models.PhoneProject).filter(
        models.PhoneProject.id == project_id,
        models.PhoneProject.owner_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Phone project not found")
    
    import json
    response_data = PhoneProjectResponse.from_orm(project)
    if project.email_recipients:
        response_data.email_recipients = json.loads(project.email_recipients)
    
    return response_data


@router.put("/{project_id}", response_model=PhoneProjectResponse)
def update_phone_project(
    project_id: uuid.UUID,
    project_data: PhoneProjectUpdate,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """Обновить проект телефонии"""
    import json
    
    project = db.query(models.PhoneProject).filter(
        models.PhoneProject.id == project_id,
        models.PhoneProject.owner_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Phone project not found")
    
    # Обновляем поля
    if project_data.name is not None:
        project.name = project_data.name
    if project_data.description is not None:
        project.description = project_data.description
    if project_data.client_id is not None:
        # Проверяем доступ к клиенту
        if project_data.client_id:
            client = db.query(models.Client).filter_by(id=project_data.client_id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
            if client.owner_id != current_user.id:
                raise HTTPException(status_code=403, detail="Access denied to this client")
        project.client_id = project_data.client_id
    
    # Настройки выгрузки
    if project_data.crm_webhook_url is not None:
        project.crm_webhook_url = project_data.crm_webhook_url
    if project_data.email_recipients is not None:
        project.email_recipients = json.dumps(project_data.email_recipients) if project_data.email_recipients else None
    if project_data.telegram_chat_id is not None:
        project.telegram_chat_id = project_data.telegram_chat_id
    
    # Настройки валидации
    if project_data.enable_social_check is not None:
        project.enable_social_check = project_data.enable_social_check
    if project_data.enable_gosuslugi_check is not None:
        project.enable_gosuslugi_check = project_data.enable_gosuslugi_check
    if project_data.enable_metrica_export is not None:
        project.enable_metrica_export = project_data.enable_metrica_export
    if project_data.is_active is not None:
        project.is_active = project_data.is_active
    
    db.commit()
    db.refresh(project)
    
    logger.info(f"Updated phone project: {project.id} ({project.name})")
    
    response_data = PhoneProjectResponse.from_orm(project)
    if project.email_recipients:
        response_data.email_recipients = json.loads(project.email_recipients)
    
    return response_data


@router.delete("/{project_id}")
def delete_phone_project(
    project_id: uuid.UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """Удалить проект телефонии"""
    project = db.query(models.PhoneProject).filter(
        models.PhoneProject.id == project_id,
        models.PhoneProject.owner_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Phone project not found")
    
    db.delete(project)
    db.commit()
    
    logger.info(f"Deleted phone project: {project_id}")
    
    return {"status": "deleted", "project_id": str(project_id)}

