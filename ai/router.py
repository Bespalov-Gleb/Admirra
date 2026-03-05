"""
Роутер AI API: генерация отчётов.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.database import get_db
from core import models, security

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI"])


class GenerateReportRequest(BaseModel):
    client_id: Optional[str] = None
    start_date: str
    end_date: str
    report_type: str = "full"  # full | recommendations


class GenerateReportResponse(BaseModel):
    text: str


class ChatRequest(BaseModel):
    client_id: Optional[str] = None
    start_date: str
    end_date: str
    message: str
    history: Optional[list[dict]] = None


class ChatResponse(BaseModel):
    text: str


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Чат с AI: вопрос пользователя в контексте данных дашборда.
    """
    try:
        from ai.report_generator import chat as do_chat
    except ImportError as e:
        logger.warning("AI module not available: %s", e)
        raise HTTPException(
            status_code=503,
            detail="Модуль AI недоступен. Проверьте настройки OPENAI_API_KEY.",
        )

    client_id = None
    if body.client_id:
        try:
            import uuid
            client_id = uuid.UUID(body.client_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный client_id")

    if not (body.message or "").strip():
        raise HTTPException(status_code=400, detail="Сообщение не может быть пустым")

    try:
        text = await do_chat(
            db=db,
            user_id=current_user.id,
            client_id=client_id,
            start_date=body.start_date,
            end_date=body.end_date,
            user_message=body.message.strip(),
            history=body.history or [],
        )
        return ChatResponse(text=text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Chat failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Не удалось получить ответ. Проверьте логи.",
        )


@router.post("/generate-report", response_model=GenerateReportResponse)
async def generate_report(
    body: GenerateReportRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Генерирует AI-отчёт на основе данных дашборда за указанный период.
    """
    try:
        from ai.report_generator import generate_report as do_generate
    except ImportError as e:
        logger.warning("AI module not available: %s", e)
        raise HTTPException(
            status_code=503,
            detail="Модуль AI недоступен. Проверьте настройки OPENAI_API_KEY.",
        )

    client_id = None
    if body.client_id:
        try:
            import uuid
            client_id = uuid.UUID(body.client_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный client_id")

    try:
        text = await do_generate(
            db=db,
            user_id=current_user.id,
            client_id=client_id,
            start_date=body.start_date,
            end_date=body.end_date,
            report_type=body.report_type or "full",
        )
        return GenerateReportResponse(text=text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Report generation failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Не удалось сгенерировать отчёт. Проверьте логи.",
        )
