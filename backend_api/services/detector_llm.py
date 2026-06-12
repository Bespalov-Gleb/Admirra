"""
Async LLM post-processor for detector alerts.

After deterministic detection runs, this module calls Claude to produce a
human-readable one-sentence hypothesis for each open alert.
Cached once per day per alert (meta['llm_hypothesis_at']).
"""
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from core import models

logger = logging.getLogger("detector_llm")

_SYSTEM_PROMPT = (
    "Ты — аналитик рекламного агентства. "
    "Отвечай строго одним предложением на русском языке. "
    "Включай конкретные числа из контекста. "
    "Без вводных слов, без markdown, без эмодзи."
)

_METRIC_RU = {
    "expenses": "расходы",
    "clicks": "клики",
    "impressions": "показы",
    "cpc": "CPC",
    "conversions": "конверсии",
    "cpa": "CPA",
}

_CHANNEL_RU = {
    "yandex_direct": "Яндекс Директ",
    "vk_ads": "VK Реклама",
    "avito": "Авито",
}

_PATTERN_RU = {
    "budget_exhausted": "детектор видит паттерн «закончился бюджет или остановилась кампания»",
    "auction_up": "детектор видит паттерн «подорожал аукцион или выросла конкуренция»",
    "reach_down": "детектор видит паттерн «сужение охвата или падение трафика»",
    "conversion_drop": "детектор видит паттерн «просела конверсия сайта или посадочной»",
    "tracking_issue": "детектор видит паттерн «проблема с целями Метрики или трекингом»",
    "empty_spend": "детектор видит паттерн «открут в пустоту»",
}


def _build_prompt(alert: models.DetectorAlert) -> str:
    metric_ru = _METRIC_RU.get(alert.metric, alert.metric)
    channel_val = alert.channel.value if alert.channel else ""
    channel_ru = _CHANNEL_RU.get(channel_val, channel_val or "все каналы")
    sign = "+" if float(alert.deviation_pct or 0) > 0 else ""
    days = alert.consecutive_days or 1
    base = float(alert.baseline_value or 0)
    actual = float(alert.actual_value or 0)

    level_map = {"project": "проекта", "goal": "цели", "campaign": "кампании"}
    level_ru = level_map.get(alert.detection_level or "project", alert.detection_level or "")

    pattern_line = ""
    if alert.pattern_key and alert.pattern_key in _PATTERN_RU:
        pattern_line = f"\nПаттерн: {_PATTERN_RU[alert.pattern_key]}."

    return (
        f"Аномалия на уровне {level_ru}.\n"
        f"Метрика: {metric_ru} | Канал: {channel_ru}\n"
        f"Отклонение: {sign}{float(alert.deviation_pct or 0):.0f}% за {days} дн. подряд\n"
        f"База: {base:,.0f} → факт: {actual:,.0f}{pattern_line}\n\n"
        "Напиши одно предложение о вероятной причине. Включи числа."
    )


async def refresh_hypothesis_texts_for_client(db: Session, client_id: uuid.UUID) -> None:
    """Generate/refresh LLM hypothesis text for open alerts lacking fresh text (TZ 3.6)."""
    from core.config import get_config
    cfg = get_config()
    api_key = cfg.openai.api_key
    if not api_key:
        return

    # Don't spend tokens on projects with detector toggled off (deterministic
    # hypothesis_text is already stored as fallback; regenerated on re-enable)
    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not client or not getattr(client, "detector_enabled", False):
        return
    owner = db.query(models.User).filter(models.User.id == client.owner_id).first()
    if owner and not getattr(owner, "global_detector_enabled", True):
        return

    now = datetime.now(timezone.utc)
    cache_seconds = 23 * 3600

    alerts = (
        db.query(models.DetectorAlert)
        .filter(
            models.DetectorAlert.client_id == client_id,
            models.DetectorAlert.status == "open",
        )
        .all()
    )

    to_refresh = []
    for alert in alerts:
        meta = alert.meta or {}
        last_str = meta.get("llm_hypothesis_at")
        if last_str:
            try:
                last_at = datetime.fromisoformat(last_str)
                if (now - last_at).total_seconds() < cache_seconds:
                    continue
            except Exception:
                pass
        to_refresh.append(alert)

    if not to_refresh:
        return

    try:
        from anthropic import AsyncAnthropic
        base_url = (cfg.openai.base_url or "").strip().rstrip("/") or None
        kwargs: dict = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        client = AsyncAnthropic(**kwargs)
    except Exception:
        logger.exception("Failed to create Anthropic client for hypothesis generation")
        return

    updated = False
    for alert in to_refresh:
        try:
            prompt = _build_prompt(alert)
            response = await client.messages.create(
                model=cfg.openai.model,
                max_tokens=150,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
                temperature=1.0,
            )
            text = (response.content[0].text if response.content else "").strip()
            if text:
                alert.hypothesis_text = text
                alert.meta = {**(alert.meta or {}), "llm_hypothesis_at": now.isoformat()}
                updated = True
                logger.debug("LLM hypothesis generated for alert %s", alert.id)
        except Exception:
            logger.exception("LLM hypothesis failed for alert %s", alert.id)

    if updated:
        try:
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Failed to commit LLM hypotheses for client %s", client_id)
