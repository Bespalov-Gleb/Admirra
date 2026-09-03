"""HTTP API AI-ассистента (роут /ai). Префикс /assistant → /api/assistant/*.

Отдельный роутер от ai/router.py (AI-комментарии дашборда)."""
from __future__ import annotations

import asyncio
import json
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core import models, security
from core.database import get_db
from backend_api.access_control import get_accessible_client_ids

from . import agent, llm, wordstat_client
from .models_catalog import DEFAULT_MODEL_ID, catalog_public, get_model, normalize_effort

router = APIRouter(prefix="/assistant", tags=["AI Assistant"])


# ── Схемы запросов ───────────────────────────────────────────────────────────
class ConversationCreate(BaseModel):
    client_id: Optional[str] = None
    model: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    client_id: Optional[str] = None
    model: Optional[str] = None
    effort: Optional[str] = None


# ── Вспомогательное ──────────────────────────────────────────────────────────
def _assert_client_access(db: Session, user: models.User, client_id) -> None:
    if not client_id:
        return
    accessible = {str(c) for c in get_accessible_client_ids(db, user)}
    if str(client_id) not in accessible:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Нет доступа к этому проекту")


def _conv_or_404(db: Session, user: models.User, conversation_id: str) -> models.AiConversation:
    try:
        cid = UUID(str(conversation_id))
    except (ValueError, TypeError):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Диалог не найден")
    conv = (
        db.query(models.AiConversation)
        .filter(models.AiConversation.id == cid, models.AiConversation.user_id == user.id)
        .first()
    )
    if not conv:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Диалог не найден")
    return conv


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _conv_public(conv: models.AiConversation) -> dict:
    return {
        "id": str(conv.id),
        "title": conv.title,
        "client_id": str(conv.client_id) if conv.client_id else None,
        "model": conv.model,
        "effort": conv.effort,
        "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
    }


# ── Эндпоинты ────────────────────────────────────────────────────────────────
@router.get("/models")
def list_models(current_user: models.User = Depends(security.get_current_user)):
    """Каталог моделей + доступность (задан ли ключ активного LLM-провайдера)."""
    from core.config import get_config
    return {
        "configured": llm.is_configured(),
        "provider": get_config().openrouter.provider,
        "default_model": DEFAULT_MODEL_ID,
        "models": catalog_public(),
        # Фронт не предполагает доступность Wordstat: API сообщает фактическое
        # состояние конфигурации, не раскрывая ни ключ, ни ID каталога.
        "wordstat_configured": wordstat_client.is_configured(),
    }


@router.get("/conversations")
def list_conversations(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    rows = (
        db.query(models.AiConversation)
        .filter(models.AiConversation.user_id == current_user.id)
        .order_by(models.AiConversation.updated_at.desc().nullslast())
        .limit(100)
        .all()
    )
    return [_conv_public(r) for r in rows]


@router.post("/conversations", status_code=status.HTTP_201_CREATED)
def create_conversation(
    body: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    _assert_client_access(db, current_user, body.client_id)
    conv = models.AiConversation(
        user_id=current_user.id,
        client_id=UUID(body.client_id) if body.client_id else None,
        model=get_model(body.model).id,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return _conv_public(conv)


@router.get("/conversations/{conversation_id}")
def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    conv = _conv_or_404(db, current_user, conversation_id)
    # Для отображения — реплики пользователя и финальные ответы ассистента.
    messages = [
        {"id": str(m.id), "role": m.role, "content": m.content,
         "created_at": m.created_at.isoformat() if m.created_at else None}
        for m in conv.messages
        if m.role in ("user", "assistant") and (m.content or "").strip()
    ]
    return {**_conv_public(conv), "messages": messages}


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    conv = _conv_or_404(db, current_user, conversation_id)
    db.delete(conv)
    db.commit()


@router.post("/chat")
async def chat(
    req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """Стриминговый ответ ассистента (Server-Sent Events).

    Тело: message (+ conversation_id | client_id, model, effort). Если
    conversation_id не задан — создаётся новый диалог."""
    text = (req.message or "").strip()
    if not text:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Пустой запрос")

    conv = _conv_or_404(db, current_user, req.conversation_id) if req.conversation_id else None
    client_id = req.client_id or (str(conv.client_id) if conv and conv.client_id else None)
    _assert_client_access(db, current_user, client_id)

    if conv is None:
        conv = models.AiConversation(
            user_id=current_user.id,
            client_id=UUID(client_id) if client_id else None,
            model=get_model(req.model).id,
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

    # Ассистент работает только на Gemini: модель зафиксирована на дефолте,
    # выбор во фронте убран. Реверт — вернуть get_model(req.model or conv.model).
    model = get_model(DEFAULT_MODEL_ID)
    effort = normalize_effort(model, req.effort)
    conversation_id = str(conv.id)

    async def event_stream():
        yield _sse({"type": "meta", "conversation_id": conversation_id, "model": model.id})
        # Мультиплексируем поток агента с heartbeat: при долгом думании/медленных
        # инструментах агент какое-то время молчит, и без периодических байтов
        # прокси (nginx) рвёт соединение по таймауту — казалось, что «завис».
        queue: asyncio.Queue = asyncio.Queue()
        _DONE = object()

        async def _producer():
            try:
                async for ev in agent.run(db, conv, text, model, effort, current_user):
                    await queue.put(ev)
            except Exception as exc:  # noqa: BLE001
                await queue.put({"type": "error", "error": f"Сбой стрима: {exc}"})
            finally:
                await queue.put(_DONE)

        task = asyncio.create_task(_producer())
        try:
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=12.0)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"   # SSE-комментарий — клиент игнорирует, соединение живёт
                    continue
                if item is _DONE:
                    break
                yield _sse(item)
        finally:
            if not task.done():
                task.cancel()
            yield _sse({"type": "end"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # nginx: не буферизировать SSE
        },
    )
