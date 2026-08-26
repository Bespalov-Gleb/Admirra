"""Агент-луп ассистента: OpenRouter (tool-calling) + инструменты.

Аккаунт-широкий: агент видит проекты пользователя и может выбрать нужный по
названию (list_projects/use_project), либо работает по проекту из шапки. Wordstat
доступен без проекта. Поток: system+история+вопрос → модель (стрим) → tool_calls
→ исполнение → повтор; guard по числу витков. Сообщения пишутся в ai_messages."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional

from sqlalchemy.orm import Session

from core import models
from core.config import get_config

from . import llm, tools, wordstat_client
from .models_catalog import ModelSpec
from .token_provider import YandexAccessError
from .tools import ToolContext

logger = logging.getLogger("ai_assistant.agent")
cfg = get_config()


def _system_prompt(ctx: ToolContext) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [
        "Ты — аналитик рекламы AdMirra. Помогаешь по данным рекламных проектов пользователя.",
        f"Сегодня: {today}. Отвечай на русском, конкретными числами.",
        "Инструменты: чтение Яндекс.Директа и Яндекс.Метрики по проекту" +
        (", а также Wordstat (спрос в Яндексе по фразам)." if wordstat_client.is_configured() else "."),
        "Если нужного проекта нет в текущем контексте — вызови list_projects и use_project, выбрав проект по названию.",
        "Всегда бери числа из инструментов, ничего не выдумывай. Если данных нет — так и скажи.",
        "Wordstat вызывай только по прямому запросу пользователя о спросе, семантике или частотности; не делай повторные одинаковые вызовы.",
        "Формат периодов — YYYY-MM-DD. Конверсия по цели Метрики — метрика ym:s:goal<ID>reaches.",
        "Расходы Директа возвращаются с учётом НДС по умолчанию. Wordstat не требует выбора проекта.",
    ]
    if ctx.access is not None:
        cab = ctx.access.account_name or "—"
        lines.append(f"Текущий проект диалога уже выбран. Рекламный кабинет: {cab}.")
        if ctx.access.counter_ids:
            lines.append(f"Счётчики Метрики проекта: {', '.join(map(str, ctx.access.counter_ids))}.")
    else:
        lines.append("Проект не выбран. Спроси у пользователя или вызови list_projects, затем use_project по названию.")
    return "\n".join(lines)


def _history_to_messages(conversation: models.AiConversation) -> list[dict]:
    """Прошлые витки → компактный контекст: только user и финальные ответы
    ассистента (старые tool-вызовы/результаты не повторяем)."""
    out: list[dict] = []
    for m in conversation.messages:
        if m.role == "user" and m.content:
            out.append({"role": "user", "content": m.content})
        elif m.role == "assistant" and m.content and not m.tool_calls:
            out.append({"role": "assistant", "content": m.content})
    return out


def _persist(db: Session, conversation_id, role: str, *, content: Optional[str] = None,
             tool_calls=None, tool_call_id: Optional[str] = None, name: Optional[str] = None,
             tokens_in: Optional[int] = None, tokens_out: Optional[int] = None) -> models.AiMessage:
    msg = models.AiMessage(
        conversation_id=conversation_id, role=role, content=content,
        tool_calls=tool_calls, tool_call_id=tool_call_id, name=name,
        tokens_in=tokens_in, tokens_out=tokens_out,
    )
    db.add(msg)
    db.commit()
    return msg


async def run(
    db: Session,
    conversation: models.AiConversation,
    user_text: str,
    model: ModelSpec,
    effort: Optional[str],
    user: models.User,
) -> AsyncGenerator[dict, None]:
    """Асинхронный генератор SSE-событий одного обмена. Пишет сообщения в БД.

    События: text / reasoning / tool / done / error (см. router)."""
    if not llm.is_configured():
        yield {"type": "error", "error": "AI-ассистент ещё не подключён (нет ключа провайдера)."}
        return

    # Контекст инструментов. Проект НЕ берётся из шапки: предвыбираем только тот,
    # что агент сам выбрал ранее в этом диалоге (сохранён в conversation.client_id).
    ctx = ToolContext(db=db, user=user, conversation=conversation)
    if conversation.client_id:
        try:
            ctx.set_project(conversation.client_id)
        except YandexAccessError:
            ctx.access = None

    tool_schemas = tools.tool_schemas()

    history = _history_to_messages(conversation)
    _persist(db, conversation.id, "user", content=user_text)
    if not conversation.title:
        conversation.title = (user_text[:60] + "…") if len(user_text) > 60 else user_text
    conversation.model = model.id
    conversation.effort = effort
    db.commit()

    messages: list[dict] = [{"role": "system", "content": _system_prompt(ctx)}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_text})

    final_text = ""
    try:
        for _iteration in range(max(1, cfg.openrouter.max_tool_iterations)):
            assistant_msg: Optional[dict] = None
            usage: Optional[dict] = None
            async for ev in llm.stream_completion(
                model=model, effort=effort, messages=messages, tools=tool_schemas,
            ):
                if ev["type"] == "text":
                    final_text += ev["delta"]
                    yield ev
                elif ev["type"] == "reasoning":
                    yield ev
                elif ev["type"] == "message":
                    assistant_msg = ev["message"]
                    usage = ev.get("usage")

            if assistant_msg is None:
                break

            tool_calls = assistant_msg.get("tool_calls")
            if not tool_calls:
                _persist(db, conversation.id, "assistant", content=assistant_msg.get("content", ""),
                         tokens_out=(usage or {}).get("completion_tokens"),
                         tokens_in=(usage or {}).get("prompt_tokens"))
                yield {"type": "done", "content": assistant_msg.get("content", "")}
                return

            messages.append(assistant_msg)
            _persist(db, conversation.id, "assistant",
                     content=assistant_msg.get("content") or "", tool_calls=tool_calls)

            for call in tool_calls:
                fn = call.get("function", {})
                name = fn.get("name", "")
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                yield {"type": "tool", "name": name, "status": "start"}
                result = await tools.execute_tool(name, args, ctx)
                yield {"type": "tool", "name": name, "status": "done"}
                messages.append({"role": "tool", "tool_call_id": call.get("id"), "name": name, "content": result})
                _persist(db, conversation.id, "tool", content=result, tool_call_id=call.get("id"), name=name)

        if final_text:
            _persist(db, conversation.id, "assistant", content=final_text)
        yield {"type": "done", "content": final_text or "Достигнут лимит шагов анализа. Уточните запрос."}
    except llm.LLMError as exc:
        logger.warning("LLM error: %s", exc)
        yield {"type": "error", "error": f"Ошибка модели: {exc}"}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Assistant agent failure")
        yield {"type": "error", "error": f"Внутренняя ошибка ассистента: {exc}"}
