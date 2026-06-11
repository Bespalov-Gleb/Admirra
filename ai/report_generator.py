"""
Генерация AI-отчётов на основе агрегированных данных дашборда.
Использует OpenAI API с поддержкой прокси.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
import uuid

from sqlalchemy.orm import Session

from core import models, settings
from backend_api.stats_service import StatsService
logger = logging.getLogger(__name__)


def _date_label(value) -> str:
    return value.isoformat() if value else "—"


def _num(value, digits: int = 2) -> float:
    try:
        return round(float(value or 0), digits)
    except (TypeError, ValueError):
        return 0.0


def _create_anthropic_client():
    from anthropic import AsyncAnthropic
    base_url = (getattr(settings, "OPENAI_BASE_URL", "") or "").strip().rstrip("/") or None
    kwargs = {"api_key": settings.OPENAI_API_KEY}
    if base_url:
        kwargs["base_url"] = base_url
    return AsyncAnthropic(**kwargs)


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
        logger.error("generate_report: OPENAI_API_KEY не настроен")
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

    client = _create_anthropic_client()

    system_prompt = """Ты — профессиональный аналитик рекламных кампаний с экспертизой в Яндекс Директ и ВК Реклама.

Твоя задача — анализировать данные и формировать чёткие, структурированные отчёты на русском языке.

## Правила работы с данными

- Всегда опирайся только на предоставленные данные
- Если данных недостаточно для вывода — укажи это явно
- Числа округляй до 2 знаков после запятой, крупные суммы — до целых
- Сравнивай показатели внутри периода (топ/аутсайдеры) и с предыдущим периодом, если он есть

## Ключевые метрики для анализа

Эффективность: CTR, CPC, CPA, CPL, ROAS
Объём: расходы, показы, клики, лиды/конверсии
Качество: процент отказов, глубина просмотра, время на сайте (если доступны)

## Форматирование

- Используй заголовки и короткие абзацы
- Выделяй конкретные цифры: не «высокий CPA», а «CPA 2 340 ₽ (+18% к норме)»
- Топ кампаний оформляй списком с метриками
- Итог — не более 2–3 конкретных выводов"""

    if report_type == "recommendations":
        system_prompt += """

Сфокусируйся исключительно на действиях:
1. Что отключить или снизить бюджет (с обоснованием по метрикам)
2. Что масштабировать (с обоснованием)
3. Что протестировать (конкретные гипотезы)
Каждый пункт — не более 2 предложений. Без общих слов."""
    else:
        system_prompt += """

Развёрнутый отчёт. Структура:
1. Общие итоги периода (таблица или список метрик)
2. Динамика vs предыдущий период (если данные есть)
3. Анализ по кампаниям / каналам (Директ vs ВК)
4. Топ-3 лучших и топ-3 худших кампаний
5. Выводы и приоритеты на следующий период"""

    user_message = f"Данные за период {start_date} — {end_date}:\n\n{context}"

    try:
        logger.info("generate_report: calling Anthropic API (model=%s)", settings.OPENAI_MODEL)
        response = await client.messages.create(
            model=settings.OPENAI_MODEL,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            temperature=1.0,
        )
        text = response.content[0].text if response.content else ""
        result = text.strip()
        logger.info("generate_report: Anthropic returned %d chars", len(result))
        return result
    except Exception as e:
        logger.exception("Anthropic API error: %s", e)
        raise


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


def build_assistant_context(
    db: Session,
    user_id: uuid.UUID,
    client_id: uuid.UUID,
    start_date: str,
    end_date: str,
) -> dict:
    effective_client_ids = StatsService.get_effective_client_ids(db, user_id, client_id)
    if not effective_client_ids:
        raise ValueError("Нет доступа к данным проекта.")

    try:
        d_end = datetime.strptime(end_date, "%Y-%m-%d").date()
        d_start = datetime.strptime(start_date, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Неверный формат дат. Используйте YYYY-MM-DD.")

    summary = StatsService.aggregate_summary(db, effective_client_ids, d_start, d_end, "all", None, None)
    campaigns = StatsService.get_campaign_stats(db, effective_client_ids, d_start, d_end, "all", None, None)

    budgets = (
        db.query(models.ProjectBudget)
        .filter(
            models.ProjectBudget.client_id == client_id,
            models.ProjectBudget.period_start <= d_end,
            models.ProjectBudget.period_end >= d_start,
        )
        .order_by(models.ProjectBudget.channel, models.ProjectBudget.period_start.desc())
        .all()
    )
    targets = (
        db.query(models.ProjectTargetCPA)
        .filter(
            models.ProjectTargetCPA.client_id == client_id,
            models.ProjectTargetCPA.period_start <= d_end,
            models.ProjectTargetCPA.period_end >= d_start,
        )
        .order_by(models.ProjectTargetCPA.channel, models.ProjectTargetCPA.goal_name)
        .all()
    )
    alerts = (
        db.query(models.DetectorAlert)
        .filter(
            models.DetectorAlert.client_id == client_id,
            models.DetectorAlert.status == "open",
        )
        .order_by(models.DetectorAlert.opened_at.desc())
        .limit(10)
        .all()
    )
    integrations = (
        db.query(models.Integration)
        .filter(models.Integration.client_id == client_id)
        .all()
    )

    has_data = any(
        _num(summary.get(key)) > 0
        for key in ("expenses", "impressions", "clicks", "leads", "conversions")
    )
    return {
        "period": {"start": start_date, "end": end_date},
        "summary": summary,
        "campaigns": campaigns,
        "budgets": budgets,
        "targets": targets,
        "alerts": alerts,
        "integrations": integrations,
        "has_data": has_data,
    }


def assistant_context_to_text(context: dict) -> str:
    summary = context.get("summary") or {}
    campaigns = context.get("campaigns") or []
    budgets = context.get("budgets") or []
    targets = context.get("targets") or []
    alerts = context.get("alerts") or []
    integrations = context.get("integrations") or []

    lines = []
    period = context.get("period") or {}
    lines.append(f"Период: {period.get('start')} — {period.get('end')}")
    lines.append(f"Подключенные каналы: {', '.join(str(i.platform.value if hasattr(i.platform, 'value') else i.platform) for i in integrations) or 'нет'}")
    lines.append("\n## KPI проекта")
    lines.append(f"Расходы: {_num(summary.get('expenses')):,.2f} ₽")
    lines.append(f"Показы: {int(summary.get('impressions') or 0):,}")
    lines.append(f"Клики: {int(summary.get('clicks') or 0):,}")
    lines.append(f"Конверсии/лиды: {int((summary.get('leads') or summary.get('conversions') or 0) or 0):,}")
    lines.append(f"CPC: {_num(summary.get('cpc')):,.2f} ₽")
    lines.append(f"CPA/CPL: {_num(summary.get('cpa')):,.2f} ₽")
    lines.append(f"CTR: {_num(summary.get('ctr')):.2f}%")
    lines.append(f"CR: {_num(summary.get('cr')):.2f}%")

    trends = summary.get("trends") or {}
    if trends:
        lines.append("\n## Динамика к предыдущему периоду")
        for key, label in (
            ("expenses", "Расходы"),
            ("impressions", "Показы"),
            ("clicks", "Клики"),
            ("leads", "Лиды"),
            ("cpc", "CPC"),
            ("cpa", "CPA/CPL"),
        ):
            if key in trends:
                lines.append(f"{label}: {_num(trends.get(key), 1):+.1f}%")

    if campaigns:
        lines.append("\n## Кампании")
        for c in sorted(campaigns, key=lambda item: (item.get("conversions") or 0, item.get("cost") or 0), reverse=True)[:10]:
            lines.append(
                f"- {c.get('name') or 'Без названия'}: расходы {_num(c.get('cost')):,.2f} ₽, "
                f"клики {int(c.get('clicks') or 0)}, лиды {int(c.get('conversions') or 0)}, "
                f"CPC {_num(c.get('cpc')):,.2f} ₽, CPA/CPL {_num(c.get('cpa')):,.2f} ₽"
            )

    if budgets:
        lines.append("\n## Бюджеты план-факт")
        spent_by_channel = {}
        for c in campaigns:
            name = (c.get("name") or "").lower()
            if "[яд]" in name:
                key = "YANDEX_DIRECT"
            elif "[vk]" in name:
                key = "VK_ADS"
            else:
                key = "OTHER"
            spent_by_channel[key] = spent_by_channel.get(key, 0.0) + _num(c.get("cost"))
        for b in budgets:
            channel = b.channel.value if hasattr(b.channel, "value") else str(b.channel)
            plan = _num(b.amount)
            fact = _num(spent_by_channel.get(channel, 0))
            pct = round((fact / plan) * 100, 1) if plan > 0 else 0
            lines.append(f"- {channel}: план {plan:,.2f} ₽, факт {fact:,.2f} ₽ ({pct:.1f}%), период {_date_label(b.period_start)} — {_date_label(b.period_end)}")

    if targets:
        lines.append("\n## Целевые CPA/CPL")
        for t in targets[:20]:
            channel = t.channel.value if getattr(t, "channel", None) and hasattr(t.channel, "value") else "сводно"
            name = t.goal_name or ("Сводный CPL" if t.is_summary else "Цель без названия")
            enabled = "контроль включен" if t.control_enabled else "контроль выключен"
            lines.append(f"- {channel}: {name}, цель {_num(t.target_cpa):,.2f} ₽, {enabled}")

    if alerts:
        lines.append("\n## Открытые алерты детектора")
        for a in alerts:
            channel = a.channel.value if getattr(a, "channel", None) and hasattr(a.channel, "value") else "проект"
            lines.append(
                f"- {a.severity}, {channel}, {a.metric}: отклонение {_num(a.deviation_pct, 1):+.1f}%, "
                f"факт {_num(a.actual_value)}, база {_num(a.baseline_value)}. "
                f"Гипотеза: {a.hypothesis_text or 'не указана'}"
            )

    if not context.get("has_data"):
        lines.append("\nВажно: по выбранному периоду нет достаточных данных статистики. Не делай выводы о причинах без явного указания на нехватку данных.")

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

    context = assistant_context_to_text(build_assistant_context(db, user_id, client_id, start_date, end_date))
    client = _create_anthropic_client()

    system_prompt = f"""Ты — аналитик рекламных кампаний. Отвечай на вопросы пользователя на основе данных дашборда.
Данные за период {start_date} — {end_date}:

{context}

Правила:
- Отвечай только по данным из контекста.
- Если данных недостаточно, прямо скажи, каких данных не хватает.
- Не придумывай кампании, цели, бюджеты и причины.
- Не генерируй отчёты и аудиты в чате: для таких запросов скажи, что это отдельный раздел.
- Отвечай кратко, на русском языке, с конкретными числами."""

    messages = []
    for h in (history or []):
        role = h.get("role")
        content = h.get("content") or ""
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})

    try:
        response = await client.messages.create(
            model=settings.OPENAI_MODEL,
            max_tokens=2048,
            system=system_prompt,
            messages=messages,
            temperature=1.0,
        )
        text = response.content[0].text if response.content else ""
        return text.strip()
    except Exception as e:
        logger.exception("Anthropic API error: %s", e)
        raise
