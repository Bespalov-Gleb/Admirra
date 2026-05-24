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
from backend_api.services.subscription import SubscriptionService
from backend_api.services.history import log_history_event
from backend_api.access_control import assert_project_access

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

    if client_id:
        assert_project_access(db, current_user, client_id, write=False, allow_client_ai=True)

    try:
        SubscriptionService.ensure_can_use_ai(db, current_user, requested=1)
        text = await do_chat(
            db=db,
            user_id=current_user.id,
            client_id=client_id,
            start_date=body.start_date,
            end_date=body.end_date,
            user_message=body.message.strip(),
            history=body.history or [],
        )
        SubscriptionService.increment_ai_usage(db, current_user, requested=1)
        from internal_admin.usage import record_ai_call

        record_ai_call(
            db,
            user_id=current_user.id,
            action="ai_chat",
            prompt_text=body.message.strip(),
            response_text=text,
            meta={"client_id": str(client_id) if client_id else None},
        )
        log_history_event(
            db,
            actor=current_user,
            event_type="ai",
            action="ai_chat_requested",
            description="Запрос в AI-чат",
            client_id=client_id,
            target_type="ai_chat",
            meta={"message_length": len(body.message.strip())},
        )
        db.commit()
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

    if client_id:
        assert_project_access(db, current_user, client_id, write=False, allow_client_ai=True)

    try:
        SubscriptionService.ensure_can_use_ai(db, current_user, requested=1)
        text = await do_generate(
            db=db,
            user_id=current_user.id,
            client_id=client_id,
            start_date=body.start_date,
            end_date=body.end_date,
            report_type=body.report_type or "full",
        )
        SubscriptionService.increment_ai_usage(db, current_user, requested=1)
        from internal_admin.usage import record_ai_call

        record_ai_call(
            db,
            user_id=current_user.id,
            action="ai_report",
            prompt_text=f"{body.report_type or 'full'} {body.start_date}-{body.end_date}",
            response_text=text,
            meta={"client_id": str(client_id) if client_id else None, "report_type": body.report_type or "full"},
        )
        log_history_event(
            db,
            actor=current_user,
            event_type="ai",
            action="ai_report_requested",
            description="Сгенерирован AI-отчет",
            client_id=client_id,
            target_type="ai_report",
            meta={"report_type": body.report_type or "full"},
        )
        db.commit()
        return GenerateReportResponse(text=text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Report generation failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Не удалось сгенерировать отчёт. Проверьте логи.",
        )
