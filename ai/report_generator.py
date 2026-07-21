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
    folder_id=None,
    platform: str = "all",
) -> str:
    """
    Генерирует текстовый отчёт на основе данных дашборда.
    report_type: "full" — полный отчёт, "recommendations" — только рекомендации,
    "comment" — короткий клиентский вывод для доставки отчёта.
    """
    if not settings.OPENAI_API_KEY:
        logger.error("generate_report: OPENAI_API_KEY не настроен")
        raise ValueError("OPENAI_API_KEY не настроен")

    if folder_id and not client_id:
        effective_client_ids = StatsService.resolve_folder_client_ids(db, user_id, folder_id)
    else:
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
        db, effective_client_ids, d_start, d_end, platform or "all", None, None
    )
    campaigns = StatsService.get_campaign_stats(
        db, effective_client_ids, d_start, d_end, platform or "all", None, None
    )

    # Топ-5 кампаний по конверсиям
    top_campaigns = sorted(
        [c for c in campaigns if c.get("conversions", 0) > 0],
        key=lambda x: x.get("conversions", 0),
        reverse=True,
    )[:5]

    # §6/§7: для короткого дашборд-комментария добавляем факты о подключениях и
    # агрегаты по направлениям — то, что AI иначе домысливает или чего не видит.
    ctx_integrations = None
    ctx_directions = None
    if report_type == "dashboard_comment":
        from core import models as _models
        _plat_ru = {"YANDEX_DIRECT": "Яндекс Директ", "VK_ADS": "VK Реклама", "AVITO_ADS": "Avito Ads", "YANDEX_METRIKA": "Яндекс Метрика"}
        integ_rows = db.query(_models.Integration).filter(_models.Integration.client_id.in_(effective_client_ids)).all()
        ctx_integrations = [
            {
                "name": _plat_ru.get(getattr(i.platform, "value", str(i.platform)), str(i.platform)),
                "status": "подключена" if getattr(i, "connection_status", "active") == "active" else "подключение не завершено",
            }
            for i in integ_rows
        ]
        if len(effective_client_ids) == 1:
            try:
                from backend_api.services import directions as _dir_svc
                client_obj = db.query(_models.Client).filter(_models.Client.id == effective_client_ids[0]).first()
                if client_obj is not None:
                    dstats = _dir_svc.direction_stats(db, client_obj, d_start, d_end, platform or "all")
                    ctx_directions = [
                        {
                            "name": it.get("name"),
                            "expenses": float(it.get("expenses") or 0),
                            "budget_share": float(it.get("budget_share") or 0),
                            "leads": int(it.get("leads") or 0),
                            "cpl": float(it.get("cpl") or 0),
                        }
                        for it in (dstats.get("items") or [])
                    ]
            except Exception as _dir_err:
                logger.warning("dashboard_comment: directions context skipped: %s", _dir_err)

    context = _build_context(summary, top_campaigns, start_date, end_date, ctx_integrations, ctx_directions)

    client = _create_anthropic_client()

    if report_type == "dashboard_comment":
        system_prompt = """Ты — аналитик рекламы. Напиши КОРОТКИЙ комментарий за период к дашборду проекта. Это не отчёт, а выжимка.

Формат — строго четыре элемента, обычным связным текстом на русском:
1) Первая строка — суть периода одним предложением (её мы сами выделим жирным, звёзды не ставь).
2) 1–2 коротких абзаца «что произошло»: синтез и причинно-следственные связи, а не перечисление метрик.
3) Один абзац — вероятная причина.
4) Одна конкретная рекомендация; начни её ровно со слова «Рекомендация:».

Объём 600–900 знаков, жёсткий максимум 1200. Без заголовков, секций, таблиц, списков, эмодзи и любой Markdown-разметки.

Запреты:
- Не переписывай KPI, которые уже видны в карточках дашборда. Ценность — синтез (например: «лиды упали сильнее бюджета — просела эффективность, а не активность»).
- НЕ считай сам. Все дельты, сравнения и производные метрики уже даны в контексте предрасчитанными. Если числа в контексте нет — не пиши про него. Никаких «оценочно», «порядка», «ориентировочно», «~» рядом с цифрами.
- Про интеграции пиши строго по блоку «Подключения»: если канала там нет или он не подключён — так и утверждай, не строй версий «отключена / данные не переданы / требует уточнения».
- Если данных мало — честно скажи это одним предложением, не выдумывай тренды."""
    elif report_type == "comment":
        system_prompt = """Ты — аналитик рекламных кампаний. Сформируй короткий комментарий для клиента к уже готовому отчёту.

Строгие правила:
- ровно 3–5 обычных связных предложений на русском языке;
- без заголовков, таблиц, списков, Markdown и приветствий;
- не переписывай подряд KPI, которые клиент уже видит в карточках;
- назови только существенное изменение или риск, его вероятную причину по данным и одно понятное действие;
- если данных недостаточно, честно скажи это в одном из предложений и не выдумывай причины.
"""
    else:
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
    elif report_type not in ("comment", "dashboard_comment"):
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
        if report_type == "dashboard_comment":
            result = _sanitize_dashboard_comment(text)
        elif report_type == "comment":
            result = _normalise_delivery_comment(text)
        else:
            result = text.strip()
        if report_type in ("comment", "dashboard_comment") and not result:
            raise ValueError("AI-комментарий пуст")
        logger.info("generate_report: Anthropic returned %d chars", len(result))
        return result
    except Exception as e:
        logger.exception("Anthropic API error: %s", e)
        raise


def _sanitize_dashboard_comment(text: str, hard_limit: int = 1200) -> str:
    """§1/§3: короткий дашборд-комментарий без разметки. Вырезаем markdown,
    оставляем только связный текст (жирный лид фронт делает сам из 1-й строки),
    жёстко ограничиваем длину."""
    import re
    t = (text or "").replace("\r", "")
    t = re.sub(r"(?m)^\s*\|.*\|\s*$", "", t)          # таблицы
    t = re.sub(r"(?m)^\s*-{3,}\s*$", "", t)            # горизонтальные линии ---
    t = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", t)        # заголовки
    t = re.sub(r"(?m)^\s*[-*•]\s+", "", t)             # маркеры списка
    t = re.sub(r"(?m)^\s*\d+[.)]\s+", "", t)           # нумерация
    t = t.replace("**", "").replace("`", "")           # bold/code
    t = re.sub(r"(?<!\w)\*(?!\s)(.+?)(?<!\s)\*(?!\w)", r"\1", t)  # *italic*
    t = re.sub(r"\n{3,}", "\n\n", t).strip()
    if len(t) > hard_limit:
        cut = t.rfind(". ", 0, hard_limit)
        t = (t[: cut + 1] if cut > hard_limit // 2 else t[:hard_limit]).strip()
    return t


def _normalise_delivery_comment(text: str) -> str:
    """Keep a short client comment free from Markdown and table formatting."""
    import re
    clean_lines = []
    for line in str(text or "").splitlines():
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip()
        line = re.sub(r"^#{1,6}\s*", "", line)
        line = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", line)
        line = re.sub(r"(`{1,3}|\*{1,3}|_{1,3}|~~)", "", line)
        line = line.replace("|", " ")
        if line:
            clean_lines.append(line)
    clean = re.sub(r"\s+", " ", " ".join(clean_lines)).strip()
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", clean) if part.strip()]
    if not 3 <= len(sentences) <= 5:
        return ""
    return " ".join(sentences).strip()


def _build_context(
    summary: dict,
    top_campaigns: list,
    start_date: str,
    end_date: str,
    integrations: list | None = None,
    directions: list | None = None,
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
        lines.append("\n## Тренды (к прошлому периоду, уже посчитаны — не пересчитывай)")
        lines.append(f"Расходы: {trends.get('expenses', 0):+.1f}%")
        lines.append(f"Показы: {trends.get('impressions', 0):+.1f}%")
        lines.append(f"Клики: {trends.get('clicks', 0):+.1f}%")
        lines.append(f"Лиды: {trends.get('leads', 0):+.1f}%")

    # §6/§7: факты о подключениях — чтобы AI утверждал, а не гадал.
    if integrations is not None:
        lines.append("\n## Подключения (факт, не догадки)")
        if integrations:
            for it in integrations:
                lines.append(f"- {it['name']}: {it['status']}")
        else:
            lines.append("- Нет подключённых рекламных кабинетов")

    # §7: агрегаты по направлениям — синтез, которого нет в отдельных карточках.
    if directions:
        lines.append("\n## Направления за период")
        for d in directions:
            lines.append(
                f"- {d['name']}: расход {d['expenses']:,.0f} ₽ ({d['budget_share']:.0f}% бюджета), "
                f"{d['leads']} лидов, CPL {d['cpl']:,.0f} ₽"
            )

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

    # Чат ассистента всегда привязан к конкретному проекту (роутер требует
    # client_id). Ветки по folder_id в chat() нет — из-за неё падал NameError
    # (folder_id не определён) → все запросы к ассистенту отдавали 503.
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
