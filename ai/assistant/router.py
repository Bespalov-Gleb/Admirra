"""HTTP API AI-ассистента (роут /ai). Префикс /assistant → /api/assistant/*.

Отдельный роутер от ai/router.py (AI-комментарии дашборда)."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Literal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from core import models, security
from core.database import get_db
from backend_api.access_control import get_accessible_client_ids

from . import agent, files, llm, wordstat_client
from .models_catalog import DEFAULT_MODEL_ID, catalog_public, get_model, normalize_effort

router = APIRouter(prefix="/assistant", tags=["AI Assistant"])


# ── Схемы запросов ───────────────────────────────────────────────────────────
class ConversationCreate(BaseModel):
    client_id: Optional[str] = None
    model: Optional[str] = None


class ChatRequest(BaseModel):
    message: str = Field(max_length=20000)
    attachment_ids: list[UUID] = Field(default_factory=list, max_length=files.MAX_FILES)
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
         "created_at": m.created_at.isoformat() if m.created_at else None,
         "attachments": (m.tool_calls or {}).get("attachments", []) if m.role == "user" and isinstance(m.tool_calls, dict) else []}
        for m in conv.messages
        if m.role in ("user", "assistant") and (m.content or "").strip() and not (m.role == "assistant" and m.tool_calls)
    ]
    used = {a["id"] for m in messages for a in m["attachments"]}
    pending = [files.attachment_public(m) for m in conv.messages if m.role == "attachment" and str(m.id) not in used]
    return {**_conv_public(conv), "messages": messages, "pending_attachments": pending}


@router.post("/conversations/{conversation_id}/attachments", status_code=201)
async def upload_attachment(
    conversation_id: str, request: Request, filename: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    conv = _conv_or_404(db, current_user, conversation_id)
    cid, uid = conv.id, current_user.id
    try:
        filename = files.safe_name(filename)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
    db.rollback()  # Do not hold a SQL connection during upload or parsing.
    data = bytearray()
    try:
        async with asyncio.timeout(30):
            async for chunk in request.stream():
                data.extend(chunk)
                if len(data) > files.MAX_BYTES:
                    raise HTTPException(413, "Максимальный размер файла — 8 МБ.")
        text = await files.extract_isolated(bytes(data), filename)
    except TimeoutError:
        raise HTTPException(408, "Загрузка файла заняла слишком много времени.") from None
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    # Serialize quotas across workers, then recheck ownership/deletion after parsing.
    db.query(models.User).filter(models.User.id == uid).with_for_update().one()
    conv = _conv_or_404(db, current_user, conversation_id)
    query = db.query(models.AiMessage).filter(models.AiMessage.conversation_id == cid, models.AiMessage.role == "attachment")
    total_chars = query.with_entities(func.coalesce(func.sum(func.length(models.AiMessage.content)), 0)).scalar()
    user_files = db.query(models.AiMessage).join(models.AiConversation).filter(
        models.AiConversation.user_id == uid, models.AiMessage.role == "attachment")
    recent = user_files.filter(models.AiMessage.created_at >= datetime.now(timezone.utc) - timedelta(days=1)).count()
    if query.count() >= 20 or total_chars + len(text) > files.MAX_CONVERSATION_CHARS:
        db.rollback()
        raise HTTPException(409, "Лимит документов диалога: 20 файлов или 120 000 символов. Создайте новый диалог.")
    if recent >= 100 or user_files.count() >= 1000:
        db.rollback()
        raise HTTPException(429, "Достигнут лимит файлов: 100 за сутки или 1000 сохранённых. Удалите ненужные диалоги.")
    row = models.AiMessage(conversation_id=cid, role="attachment", content=text,
                           tool_calls={"filename": filename, "size": len(data)})
    if not conv.title:
        conv.title = filename[:160]
    db.add(row)
    db.commit()
    db.refresh(row)
    return files.attachment_public(row)


@router.delete("/conversations/{conversation_id}/attachments/{attachment_id}", status_code=204)
def delete_attachment(conversation_id: str, attachment_id: UUID,
                      db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
    conv = _conv_or_404(db, current_user, conversation_id)
    row = db.query(models.AiMessage).filter_by(id=attachment_id, conversation_id=conv.id, role="attachment").first()
    if not row:
        raise HTTPException(404, "Файл не найден")
    for message in conv.messages:
        if message.role == "user" and isinstance(message.tool_calls, dict):
            if any(a.get("id") == str(attachment_id) for a in message.tool_calls.get("attachments", [])):
                raise HTTPException(409, "Файл уже использован. Для удаления данных удалите диалог.")
    db.delete(row)
    db.commit()


@router.get("/conversations/{conversation_id}/messages/{message_id}/download")
def download_answer(conversation_id: str, message_id: UUID, format: Literal["md", "docx"],
                    db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
    conv = _conv_or_404(db, current_user, conversation_id)
    message = db.query(models.AiMessage).filter_by(id=message_id, conversation_id=conv.id, role="assistant").first()
    if not message or not message.content or message.tool_calls:
        raise HTTPException(404, "Готовый ответ не найден")
    text = message.content
    db.rollback()
    if len(text) > 200_000:
        raise HTTPException(413, "Ответ слишком большой для экспорта.")
    content = files.export_docx(text) if format == "docx" else text.encode("utf-8")
    mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document" if format == "docx" else "text/markdown; charset=utf-8"
    return Response(content, media_type=mime, headers={
        "Content-Disposition": f'attachment; filename="admirra-answer-{message_id}.{format}"',
        "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff",
    })


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

    attachments = []
    if req.attachment_ids:
        if not conv:
            raise HTTPException(400, "Сначала загрузите файлы в диалог.")
        ids = set(req.attachment_ids)
        attachments = db.query(models.AiMessage).filter(
            models.AiMessage.conversation_id == conv.id,
            models.AiMessage.role == "attachment", models.AiMessage.id.in_(ids),
        ).all()
        if len(attachments) != len(ids):
            raise HTTPException(404, "Файл не найден в этом диалоге.")

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
                async for ev in agent.run(db, conv, text, model, effort, current_user, attachments=attachments):
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
