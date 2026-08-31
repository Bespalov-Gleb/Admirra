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

from . import llm, skills, tools, wordstat_client
from .models_catalog import ModelSpec
from .tools import ToolContext

logger = logging.getLogger("ai_assistant.agent")
cfg = get_config()


def _system_prompt(ctx: ToolContext) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [skills.PROJECT_PLAYBOOK, "", f"Сегодня: {today}. Отвечай на русском."]
    if wordstat_client.is_configured():
        lines.append("Wordstat доступен (спрос в Яндексе по фразам) — вызывай по прямому запросу о спросе/семантике.")
    if ctx.client_id is not None:
        pl = ctx.platforms()
        connected = [n for n, ok in (("Яндекс", pl["yandex"]), ("VK", pl["vk"]), ("Avito", pl["avito"])) if ok]
        lines.append(f"\nТекущий проект диалога выбран. Подключено: {', '.join(connected) or 'нет платформ'}.")
        if ctx.access is not None:
            if ctx.access.account_name:
                lines.append(f"Рекламный кабинет Яндекса: {ctx.access.account_name}.")
            if ctx.access.counter_ids:
                lines.append(f"Счётчики Метрики проекта: {', '.join(map(str, ctx.access.counter_ids))}.")
            if ctx.access.goal_ids:
                lines.append(f"Отслеживаемые цели проекта (по ним конверсии): {', '.join(map(str, ctx.access.goal_ids))}. "
                             "Имена — через metrika_get_tracked_goals.")
    else:
        lines.append("\nПроект пока не выбран — при вопросе про конкретный проект сначала выбери его через use_project.")
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
    # set_project резолвит каждую платформу независимо и не бросает исключений.
    ctx = ToolContext(db=db, user=user, conversation=conversation)
    if conversation.client_id:
        ctx.set_project(conversation.client_id)

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
    tool_limit_exhausted = False
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

        else:
            # Модель могла корректно собрать несколько источников, но не успеть
            # сформулировать ответ до общего лимита вызовов. Это не ошибка данных
            # и не повод показывать пользователю техническое сообщение.
            tool_limit_exhausted = True

        if tool_limit_exhausted:
            # Последний ход намеренно без tools: Gemini/GPT получают всю историю
            # с результатами и обязаны синтезировать ответ, а не продолжать обход
            # кабинетов. Такой режим также страхует от случайного tool-loop.
            messages.append({
                "role": "system",
                "content": (
                    "Лимит обращений к источникам в этом ответе исчерпан. "
                    "Инструменты больше недоступны. Сформируй финальный ответ только "
                    "по уже полученным данным. Если исходный вопрос подразумевал все "
                    "проекты или кабинеты, а данных собрано не по всем, прямо скажи, "
                    "что вывод относится только к уже загруженным проектам; не выдавай "
                    "частичный анализ за полный."
                ),
            })
            forced_message: Optional[dict] = None
            forced_usage: Optional[dict] = None
            async for ev in llm.stream_completion(
                model=model, effort=effort, messages=messages, tools=None,
            ):
                if ev["type"] == "text":
                    final_text += ev["delta"]
                    yield ev
                elif ev["type"] == "reasoning":
                    yield ev
                elif ev["type"] == "message":
                    forced_message = ev["message"]
                    forced_usage = ev.get("usage")

            if forced_message and (forced_message.get("content") or "").strip():
                _persist(
                    db, conversation.id, "assistant", content=forced_message["content"],
                    tokens_out=(forced_usage or {}).get("completion_tokens"),
                    tokens_in=(forced_usage or {}).get("prompt_tokens"),
                )
                yield {"type": "done", "content": forced_message["content"]}
                return

        if final_text:
            _persist(db, conversation.id, "assistant", content=final_text)
        fallback = (
            "Не удалось завершить анализ после получения данных. "
            "Попробуйте сузить период или выбрать конкретный проект."
            if tool_limit_exhausted else "Не удалось получить ответ модели. Попробуйте ещё раз."
        )
        yield {"type": "done", "content": final_text or fallback}
    except llm.LLMError as exc:
        logger.warning("LLM error: %s", exc)
        yield {"type": "error", "error": f"Ошибка модели: {exc}"}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Assistant agent failure")
        yield {"type": "error", "error": f"Внутренняя ошибка ассистента: {exc}"}
