"""
Генерация AI-отчётов на основе агрегированных данных дашборда.
Использует OpenAI API с поддержкой прокси.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
import uuid

from sqlalchemy.orm import Session

from core import settings
from backend_api.stats_service import StatsService

logger = logging.getLogger(__name__)


async def generate_report(
    db: Session,
    user_id: uuid.UUID,
    client_id: Optional[uuid.UUID],
    start_date: str,
    end_date: str,
    report_type: str = "full",
) -> str:
    """
    Генерирует текстовый отчёт на основе данных дашборда.
    report_type: "full" — полный отчёт, "recommendations" — только рекомендации.
    """
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY не настроен")

    effective_client_ids = StatsService.get_effective_client_ids(db, user_id, client_id)
    if not effective_client_ids:
        return "Нет доступа к данным проектов."

    try:
        d_end = datetime.strptime(end_date, "%Y-%m-%d").date()
        d_start = datetime.strptime(start_date, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Неверный формат дат. Используйте YYYY-MM-DD.")

    # Собираем контекст
    summary = StatsService.aggregate_summary(
        db, effective_client_ids, d_start, d_end, "all", None, None
    )
    campaigns = StatsService.get_campaign_stats(
        db, effective_client_ids, d_start, d_end, "all", None, None
    )

    # Топ-5 кампаний по конверсиям
    top_campaigns = sorted(
        [c for c in campaigns if c.get("conversions", 0) > 0],
        key=lambda x: x.get("conversions", 0),
        reverse=True,
    )[:5]

    context = _build_context(summary, top_campaigns, start_date, end_date)

    try:
        from openai import AsyncOpenAI
        import httpx
    except ImportError:
        raise ImportError("Установите openai: pip install openai")

    proxy = (settings.AI_PROXY_URL or "").strip() or None
    http_client = httpx.AsyncClient(
        proxy=proxy,
        timeout=60.0,
    )

    client = AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        http_client=http_client,
    )

    system_prompt = """Ты — аналитик рекламных кампаний. На основе предоставленных данных сформируй краткий профессиональный отчёт на русском языке.
Формат: 2–4 абзаца. Упомяни ключевые метрики (расходы, показы, клики, лиды, CPC, CPA), тренды и топ кампаний.
Пиши по делу, без воды."""

    if report_type == "recommendations":
        system_prompt += "\n\nСфокусируйся на рекомендациях по оптимизации: что улучшить, на что обратить внимание."
    else:
        system_prompt += "\n\nВключи краткий анализ динамики и выводы."

    user_message = f"Данные за период {start_date} — {end_date}:\n\n{context}"

    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.7,
        )
        text = response.choices[0].message.content or ""
        return text.strip()
    except Exception as e:
        logger.exception("OpenAI API error: %s", e)
        raise
    finally:
        await http_client.aclose()


def _build_context(
    summary: dict,
    top_campaigns: list,
    start_date: str,
    end_date: str,
) -> str:
    lines = []

    # KPI
    lines.append("## Сводка KPI")
    lines.append(f"Расходы: {summary.get('expenses', 0):,.0f} ₽")
    lines.append(f"Показы: {summary.get('impressions', 0):,}")
    lines.append(f"Клики: {summary.get('clicks', 0):,}")
    lines.append(f"Лиды: {summary.get('leads', 0):,}")
    lines.append(f"CPC: {summary.get('cpc', 0):.2f} ₽")
    lines.append(f"CPA: {summary.get('cpa', 0):.2f} ₽")
    lines.append(f"CTR: {summary.get('ctr', 0):.2f}%")
    lines.append(f"CR: {summary.get('cr', 0):.2f}%")

    trends = summary.get("trends")
    if trends:
        lines.append("\n## Тренды (к прошлому периоду)")
        lines.append(f"Расходы: {trends.get('expenses', 0):+.1f}%")
        lines.append(f"Показы: {trends.get('impressions', 0):+.1f}%")
        lines.append(f"Клики: {trends.get('clicks', 0):+.1f}%")
        lines.append(f"Лиды: {trends.get('leads', 0):+.1f}%")

    if top_campaigns:
        lines.append("\n## Топ кампаний по конверсиям")
        for i, c in enumerate(top_campaigns[:5], 1):
            name = c.get("name", c.get("campaign_name", "—"))
            conv = c.get("conversions", 0)
            cost = c.get("cost", 0)
            lines.append(f"{i}. {name}: {conv} лидов, {cost:,.0f} ₽")

    return "\n".join(lines)


async def chat(
    db: Session,
    user_id: uuid.UUID,
    client_id: Optional[uuid.UUID],
    start_date: str,
    end_date: str,
    user_message: str,
    history: list[dict],
) -> str:
    """
    Отвечает на вопрос пользователя в контексте данных дашборда.
    history: список {role: "user"|"assistant", content: str}
    """
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY не настроен")

    effective_client_ids = StatsService.get_effective_client_ids(db, user_id, client_id)
    if not effective_client_ids:
        return "Нет доступа к данным проектов."

    try:
        d_end = datetime.strptime(end_date, "%Y-%m-%d").date()
        d_start = datetime.strptime(start_date, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Неверный формат дат. Используйте YYYY-MM-DD.")

    summary = StatsService.aggregate_summary(
        db, effective_client_ids, d_start, d_end, "all", None, None
    )
    campaigns = StatsService.get_campaign_stats(
        db, effective_client_ids, d_start, d_end, "all", None, None
    )
    top_campaigns = sorted(
        [c for c in campaigns if c.get("conversions", 0) > 0],
        key=lambda x: x.get("conversions", 0),
        reverse=True,
    )[:5]

    context = _build_context(summary, top_campaigns, start_date, end_date)

    try:
        from openai import AsyncOpenAI
        import httpx
    except ImportError:
        raise ImportError("Установите openai: pip install openai")

    proxy = (settings.AI_PROXY_URL or "").strip() or None
    http_client = httpx.AsyncClient(proxy=proxy, timeout=60.0)

    client = AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        http_client=http_client,
    )

    system_prompt = f"""Ты — аналитик рекламных кампаний. Отвечай на вопросы пользователя на основе данных дашборда.
Данные за период {start_date} — {end_date}:

{context}

Отвечай кратко и по делу на русском языке."""

    messages = [{"role": "system", "content": system_prompt}]
    for h in (history or []):
        role = h.get("role")
        content = h.get("content") or ""
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})

    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            temperature=0.7,
        )
        text = response.choices[0].message.content or ""
        return text.strip()
    except Exception as e:
        logger.exception("OpenAI API error: %s", e)
        raise
    finally:
        await http_client.aclose()
