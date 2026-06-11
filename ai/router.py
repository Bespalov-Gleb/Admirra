"""
AI API: ассистент, пользовательские промпты и генерация отчётов.
"""
import logging
import calendar
import re
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend_api.access_control import assert_project_access
from backend_api.services.history import log_history_event
from backend_api.services.subscription import SubscriptionService
from core import models, security
from core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI"])


class AIQuotaResponse(BaseModel):
    used: int
    limit: int
    remaining: int
    reset_date: Optional[datetime] = None


class AIDialogResponse(BaseModel):
    id: str
    client_id: str
    title: str
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    created_at: datetime
    updated_at: datetime
    last_message: Optional[str] = None


class AIMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    cost_requests: int = 0
    redirect_target: Optional[str] = None
    created_at: datetime
    meta: dict[str, Any] = Field(default_factory=dict)


class AIDialogDetailResponse(AIDialogResponse):
    messages: list[AIMessageResponse] = Field(default_factory=list)


class AIPromptRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    text: str = Field(..., min_length=1, max_length=4000)


class AIPromptResponse(BaseModel):
    id: str
    title: str
    text: str
    created_at: datetime
    updated_at: datetime


class AIContextResponse(BaseModel):
    quota: AIQuotaResponse
    suggestions: list[str]
    has_data: bool
    has_integrations: bool
    alerts: list[dict[str, Any]] = Field(default_factory=list)


class GenerateReportRequest(BaseModel):
    client_id: Optional[str] = None
    start_date: str
    end_date: str
    report_type: str = "full"


class GenerateReportResponse(BaseModel):
    text: str


class ChatRequest(BaseModel):
    client_id: str
    start_date: str
    end_date: str
    message: str
    dialog_id: Optional[str] = None
    history: Optional[list[dict[str, str]]] = None


class ChatResponse(BaseModel):
    text: str
    dialog_id: str
    user_message: AIMessageResponse
    assistant_message: AIMessageResponse
    redirect: Optional[dict[str, str]] = None
    quota: AIQuotaResponse


def _parse_uuid(value: Optional[str], field_name: str) -> Optional[uuid.UUID]:
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Неверный {field_name}")


def _parse_date(value: str, field_name: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail=f"Неверный {field_name}. Используйте YYYY-MM-DD.")


def _quota_payload(db: Session, user: models.User) -> AIQuotaResponse:
    quota_user = SubscriptionService._resolve_ai_quota_user(db, user)
    plan = SubscriptionService.get_user_plan(db, quota_user)
    SubscriptionService._ensure_ai_period(quota_user, plan)
    used = int(quota_user.ai_requests_used or 0)
    limit = int(plan.max_ai_requests_per_period or 0)
    reset_date = None
    if quota_user.ai_requests_period_started_at:
        from datetime import timedelta

        reset_date = quota_user.ai_requests_period_started_at + timedelta(days=getattr(plan, 'ai_period_days', None) or plan.period_days)
    return AIQuotaResponse(used=used, limit=limit, remaining=max(limit - used, 0), reset_date=reset_date)


def _message_payload(message: models.AIAssistantMessage) -> AIMessageResponse:
    return AIMessageResponse(
        id=str(message.id),
        role=message.role,
        content=message.content,
        cost_requests=int(message.cost_requests or 0),
        redirect_target=message.redirect_target,
        created_at=message.created_at,
        meta=message.meta or {},
    )


def _dialog_payload(dialog: models.AIAssistantDialog) -> AIDialogResponse:
    last = dialog.messages[-1].content if getattr(dialog, "messages", None) else None
    return AIDialogResponse(
        id=str(dialog.id),
        client_id=str(dialog.client_id),
        title=dialog.title,
        period_start=dialog.period_start,
        period_end=dialog.period_end,
        created_at=dialog.created_at,
        updated_at=dialog.updated_at,
        last_message=(last[:120] if last else None),
    )


def _prompt_payload(prompt: models.AIAssistantPrompt) -> AIPromptResponse:
    return AIPromptResponse(
        id=str(prompt.id),
        title=prompt.title,
        text=prompt.text,
        created_at=prompt.created_at,
        updated_at=prompt.updated_at,
    )


def _detect_redirect_intent(message: str) -> Optional[dict[str, str]]:
    text = (message or "").lower()
    if re.search(r"\b(аудит|audit|ai-аудит|ai аудит)\b", text):
        return {
            "target": "audit",
            "label": "Перейти в AI-аудит",
            "path": "/ai-audit",
        }
    if re.search(r"\b(отч[её]т|report|pdf|еженедельн|месячн)\b", text):
        return {
            "target": "reports",
            "label": "Перейти в отчёты",
            "path": "/reports",
        }
    return None


def _dialog_title(message: str) -> str:
    title = re.sub(r"\s+", " ", (message or "").strip())
    return (title[:70] + "…") if len(title) > 70 else (title or "Новый диалог")


def _month_period(year: int, month: int) -> tuple[date, date]:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def _previous_month(today: date) -> tuple[int, int]:
    if today.month == 1:
        return today.year - 1, 12
    return today.year, today.month - 1


def _detect_period_override(message: str, fallback_start: date, fallback_end: date) -> tuple[date, date, Optional[str]]:
    text = (message or "").lower().replace("ё", "е")
    today = datetime.utcnow().date()

    if "сравн" in text and "прошл" in text and ("месяц" in text or "недел" in text):
        return fallback_start, fallback_end, None
    if "сегодня" in text:
        return today, today, "сегодня"
    if "вчера" in text:
        day = today - timedelta(days=1)
        return day, day, "вчера"
    if "прошл" in text and "месяц" in text:
        year, month = _previous_month(today)
        start, end = _month_period(year, month)
        return start, end, "прошлый месяц"
    if ("этот месяц" in text) or ("текущий месяц" in text):
        start, end = _month_period(today.year, today.month)
        return start, min(end, today), "текущий месяц"
    if "прошл" in text and "недел" in text:
        this_monday = today - timedelta(days=today.weekday())
        start = this_monday - timedelta(days=7)
        return start, start + timedelta(days=6), "прошлая неделя"
    if ("эта недел" in text) or ("текущ" in text and "недел" in text):
        start = today - timedelta(days=today.weekday())
        return start, today, "текущая неделя"

    months = {
        "январ": 1,
        "феврал": 2,
        "март": 3,
        "апрел": 4,
        "ма": 5,
        "июн": 6,
        "июл": 7,
        "август": 8,
        "сентябр": 9,
        "октябр": 10,
        "ноябр": 11,
        "декабр": 12,
    }
    year_match = re.search(r"\b(20\d{2})\b", text)
    year = int(year_match.group(1)) if year_match else today.year
    for stem, month in months.items():
        if re.search(rf"\b{stem}[а-я]*\b", text):
            start, end = _month_period(year, month)
            return start, end, f"{start.strftime('%m.%Y')}"

    return fallback_start, fallback_end, None


def _client_or_404(db: Session, current_user: models.User, client_id: uuid.UUID) -> models.Client:
    return assert_project_access(db, current_user, client_id, write=False, allow_client_ai=True)


def _alert_to_dict(alert: models.DetectorAlert) -> dict[str, Any]:
    channel = alert.channel.value if getattr(alert, "channel", None) and hasattr(alert.channel, "value") else None
    return {
        "id": str(alert.id),
        "metric": alert.metric,
        "severity": alert.severity,
        "channel": channel,
        "deviation_pct": float(alert.deviation_pct or 0),
        "hypothesis_text": alert.hypothesis_text,
        "opened_at": alert.opened_at.isoformat() if alert.opened_at else None,
    }


@router.get("/context", response_model=AIContextResponse)
async def get_context(
    client_id: str = Query(...),
    start_date: str = Query(...),
    end_date: str = Query(...),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    project_id = _parse_uuid(client_id, "client_id")
    assert project_id is not None
    _client_or_404(db, current_user, project_id)
    _parse_date(start_date, "start_date")
    _parse_date(end_date, "end_date")

    from ai.report_generator import build_assistant_context

    context = build_assistant_context(db, current_user.id, project_id, start_date, end_date)
    alerts = [_alert_to_dict(alert) for alert in context.get("alerts", [])]
    suggestions = []
    if alerts:
        first = alerts[0]
        metric = (first.get("metric") or "метрики").upper()
        deviation = first.get("deviation_pct") or 0
        suggestions.append(f"Разобрать отклонение {metric} {deviation:+.0f}%")
    suggestions.extend([
        "Почему вырос CPA звонка?",
        "Какая кампания самая невыгодная?",
        "Сравни с прошлым месяцем",
    ])
    return AIContextResponse(
        quota=_quota_payload(db, current_user),
        suggestions=suggestions[:4],
        has_data=bool(context.get("has_data")),
        has_integrations=bool(context.get("integrations")),
        alerts=alerts,
    )


@router.get("/dialogs", response_model=list[AIDialogResponse])
async def list_dialogs(
    client_id: str = Query(...),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    project_id = _parse_uuid(client_id, "client_id")
    assert project_id is not None
    _client_or_404(db, current_user, project_id)
    dialogs = (
        db.query(models.AIAssistantDialog)
        .filter(
            models.AIAssistantDialog.user_id == current_user.id,
            models.AIAssistantDialog.client_id == project_id,
        )
        .order_by(models.AIAssistantDialog.updated_at.desc())
        .limit(50)
        .all()
    )
    return [_dialog_payload(dialog) for dialog in dialogs]


@router.get("/dialogs/{dialog_id}", response_model=AIDialogDetailResponse)
async def get_dialog(
    dialog_id: str,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    did = _parse_uuid(dialog_id, "dialog_id")
    dialog = (
        db.query(models.AIAssistantDialog)
        .filter(models.AIAssistantDialog.id == did, models.AIAssistantDialog.user_id == current_user.id)
        .first()
    )
    if not dialog:
        raise HTTPException(status_code=404, detail="Диалог не найден")
    _client_or_404(db, current_user, dialog.client_id)
    base = _dialog_payload(dialog).dict()
    return AIDialogDetailResponse(**base, messages=[_message_payload(message) for message in dialog.messages])


@router.delete("/dialogs/{dialog_id}")
async def delete_dialog(
    dialog_id: str,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    did = _parse_uuid(dialog_id, "dialog_id")
    dialog = (
        db.query(models.AIAssistantDialog)
        .filter(models.AIAssistantDialog.id == did, models.AIAssistantDialog.user_id == current_user.id)
        .first()
    )
    if not dialog:
        raise HTTPException(status_code=404, detail="Диалог не найден")
    db.delete(dialog)
    db.commit()
    return {"ok": True}


@router.get("/prompts", response_model=list[AIPromptResponse])
async def list_prompts(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    prompts = (
        db.query(models.AIAssistantPrompt)
        .filter(models.AIAssistantPrompt.user_id == current_user.id)
        .order_by(models.AIAssistantPrompt.updated_at.desc())
        .all()
    )
    return [_prompt_payload(prompt) for prompt in prompts]


@router.post("/prompts", response_model=AIPromptResponse)
async def create_prompt(
    body: AIPromptRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    prompt = models.AIAssistantPrompt(
        user_id=current_user.id,
        title=body.title.strip(),
        text=body.text.strip(),
    )
    db.add(prompt)
    db.commit()
    db.refresh(prompt)
    return _prompt_payload(prompt)


@router.put("/prompts/{prompt_id}", response_model=AIPromptResponse)
async def update_prompt(
    prompt_id: str,
    body: AIPromptRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    pid = _parse_uuid(prompt_id, "prompt_id")
    prompt = (
        db.query(models.AIAssistantPrompt)
        .filter(models.AIAssistantPrompt.id == pid, models.AIAssistantPrompt.user_id == current_user.id)
        .first()
    )
    if not prompt:
        raise HTTPException(status_code=404, detail="Промпт не найден")
    prompt.title = body.title.strip()
    prompt.text = body.text.strip()
    db.commit()
    db.refresh(prompt)
    return _prompt_payload(prompt)


@router.delete("/prompts/{prompt_id}")
async def delete_prompt(
    prompt_id: str,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    pid = _parse_uuid(prompt_id, "prompt_id")
    prompt = (
        db.query(models.AIAssistantPrompt)
        .filter(models.AIAssistantPrompt.id == pid, models.AIAssistantPrompt.user_id == current_user.id)
        .first()
    )
    if not prompt:
        raise HTTPException(status_code=404, detail="Промпт не найден")
    db.delete(prompt)
    db.commit()
    return {"ok": True}


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    try:
        from ai.report_generator import chat as do_chat
    except ImportError as e:
        logger.warning("AI module not available: %s", e)
        raise HTTPException(status_code=503, detail="Модуль AI недоступен. Проверьте настройки OPENAI_API_KEY.")

    project_id = _parse_uuid(body.client_id, "client_id")
    assert project_id is not None
    _client_or_404(db, current_user, project_id)
    d_start = _parse_date(body.start_date, "start_date")
    d_end = _parse_date(body.end_date, "end_date")
    if d_start > d_end:
        raise HTTPException(status_code=400, detail="Дата начала не может быть позже даты окончания.")

    message_text = (body.message or "").strip()
    if not message_text:
        raise HTTPException(status_code=400, detail="Сообщение не может быть пустым")
    d_start, d_end, period_override = _detect_period_override(message_text, d_start, d_end)
    effective_start = d_start.isoformat()
    effective_end = d_end.isoformat()

    try:
        SubscriptionService.ensure_can_use_ai(db, current_user, requested=1)
    except ValueError as e:
        raise HTTPException(status_code=402, detail=str(e))

    dialog = None
    if body.dialog_id:
        did = _parse_uuid(body.dialog_id, "dialog_id")
        dialog = (
            db.query(models.AIAssistantDialog)
            .filter(
                models.AIAssistantDialog.id == did,
                models.AIAssistantDialog.user_id == current_user.id,
                models.AIAssistantDialog.client_id == project_id,
            )
            .first()
        )
        if not dialog:
            raise HTTPException(status_code=404, detail="Диалог не найден")

    if not dialog:
        dialog = models.AIAssistantDialog(
            user_id=current_user.id,
            client_id=project_id,
            title=_dialog_title(message_text),
            period_start=d_start,
            period_end=d_end,
        )
        db.add(dialog)
        db.flush()
    else:
        dialog.period_start = d_start
        dialog.period_end = d_end

    user_message = models.AIAssistantMessage(
        dialog_id=dialog.id,
        role="user",
        content=message_text,
        cost_requests=1,
        meta={
            "period_start": effective_start,
            "period_end": effective_end,
            "period_override": period_override,
        },
    )
    db.add(user_message)
    db.flush()

    redirect = _detect_redirect_intent(message_text)
    if redirect:
        answer = (
            "Это лучше сделать в отдельном разделе, где есть нужная структура и экспорт. "
            "Я могу помочь разобрать данные вопросом в чате, а для полного действия перейдите по кнопке ниже."
        )
        assistant_message = models.AIAssistantMessage(
            dialog_id=dialog.id,
            role="assistant",
            content=answer,
            redirect_target=redirect["target"],
            meta={"redirect": redirect},
        )
        db.add(assistant_message)
    else:
        previous_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in dialog.messages[-12:]
            if msg.id != user_message.id and msg.role in {"user", "assistant"}
        ]
        try:
            answer = await do_chat(
                db=db,
                user_id=current_user.id,
                client_id=project_id,
                start_date=effective_start,
                end_date=effective_end,
                user_message=message_text,
                history=previous_messages,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.exception("Chat failed: %s", e)
            raise HTTPException(status_code=503, detail="Не удалось получить ответ AI. Проверьте настройки модели.")

        assistant_message = models.AIAssistantMessage(
            dialog_id=dialog.id,
            role="assistant",
            content=answer or "Не удалось сформировать ответ.",
            meta={
                "period_start": effective_start,
                "period_end": effective_end,
                "period_override": period_override,
            },
        )
        db.add(assistant_message)

    dialog.updated_at = datetime.utcnow()
    SubscriptionService.increment_ai_usage(db, current_user, requested=1)
    log_history_event(
        db,
        actor=current_user,
        event_type="ai",
        action="ai_assistant_message",
        description="Запрос в AI-ассистент",
        client_id=project_id,
        target_type="ai_assistant",
        target_id=str(dialog.id),
        meta={"message_length": len(message_text), "redirect": redirect["target"] if redirect else None},
    )
    db.commit()
    db.refresh(user_message)
    db.refresh(assistant_message)
    db.refresh(dialog)
    return ChatResponse(
        text=assistant_message.content,
        dialog_id=str(dialog.id),
        user_message=_message_payload(user_message),
        assistant_message=_message_payload(assistant_message),
        redirect=redirect,
        quota=_quota_payload(db, current_user),
    )


@router.post("/generate-report", response_model=GenerateReportResponse)
async def generate_report(
    body: GenerateReportRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    try:
        from ai.report_generator import generate_report as do_generate
    except ImportError as e:
        logger.warning("AI module not available: %s", e)
        raise HTTPException(status_code=503, detail="Модуль AI недоступен. Проверьте настройки OPENAI_API_KEY.")

    client_id = _parse_uuid(body.client_id, "client_id") if body.client_id else None
    if client_id:
        _client_or_404(db, current_user, client_id)

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
        raise HTTPException(status_code=500, detail="Не удалось сгенерировать отчёт. Проверьте логи.")


@router.get("/comment")
async def get_ai_comment(
    client_id: Optional[str] = None,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """Return last saved AI comment for a client."""
    if not client_id:
        return {"text": None}
    cid = _parse_uuid(client_id, "client_id")
    _client_or_404(db, current_user, cid)
    client = db.query(models.Client).filter(models.Client.id == cid).first()
    if not client:
        return {"text": None}
    return {"text": client.last_ai_comment, "generated_at": client.last_ai_comment_at}


@router.post("/comment")
async def save_ai_comment(
    body: dict,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """Save AI comment to client record."""
    from datetime import datetime
    client_id = body.get("client_id")
    text = body.get("text", "")
    if not client_id:
        raise HTTPException(status_code=400, detail="client_id required")
    cid = _parse_uuid(client_id, "client_id")
    _client_or_404(db, current_user, cid)
    client = db.query(models.Client).filter(models.Client.id == cid).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    client.last_ai_comment = text
    client.last_ai_comment_at = datetime.utcnow()
    db.commit()
    return {"ok": True}
