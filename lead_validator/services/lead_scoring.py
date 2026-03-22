"""
Расчёт lead_score (0–100) и qualification_tier (low / medium / high) для квалификации лидов.

Веса задаются в lead_validator.config.settings (переменные окружения LEAD_SCORE_*).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger("lead_validator.lead_scoring")


@dataclass
class LeadScoreResult:
    score: int
    tier: str  # low | medium | high


def _clamp(score: int, cap: int = 100) -> int:
    return max(0, min(cap, score))


def _normalize_name(s: Optional[str]) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", str(s).strip()).lower()


def compute_lead_score(
    *,
    dadata: Optional[Any],
    has_telegram: Optional[bool],
    has_whatsapp: Optional[bool],
    has_vk: Optional[bool],
    has_viber: Optional[bool],
    has_tiktok: Optional[bool],
    has_gosuslugi: Optional[bool],
    lead_name: Optional[str],
    gosuslugi_name: Optional[str],
    gosuslugi_surname: Optional[str],
    weights,
) -> LeadScoreResult:
    """
    Суммирует баллы по доступным сигналам. Не требует обязательного совпадения имён для базового скоринга.
    Опционально: бонус за совпадение части имени из заявки с Госуслугами.
    """
    score = 0

    if dadata is not None:
        t = (dadata.type or "").lower()
        if "мобильн" in t or "mobile" in t:
            score += weights.LEAD_SCORE_WEIGHT_MOBILE
        qc = getattr(dadata, "qc", None)
        if qc is not None and int(qc) <= 1:
            score += weights.LEAD_SCORE_WEIGHT_DADATA_QC_GOOD

    if has_telegram:
        score += weights.LEAD_SCORE_WEIGHT_TELEGRAM
    if has_whatsapp:
        score += weights.LEAD_SCORE_WEIGHT_WHATSAPP
    if has_vk:
        score += weights.LEAD_SCORE_WEIGHT_VK
    if has_viber:
        score += weights.LEAD_SCORE_WEIGHT_VIBER
    if has_tiktok:
        score += weights.LEAD_SCORE_WEIGHT_TIKTOK

    if has_gosuslugi:
        score += weights.LEAD_SCORE_WEIGHT_GOSUSLUGI

    # Слабый бонус за согласованность ФИО: заявка vs Госуслуги
    ln = _normalize_name(lead_name)
    gn = _normalize_name(gosuslugi_name)
    gs = _normalize_name(gosuslugi_surname)
    if ln and (gn or gs):
        parts = ln.split()
        matched = False
        for p in parts:
            if len(p) > 2 and (p == gn or p == gs):
                matched = True
                break
        if matched:
            score += weights.LEAD_SCORE_WEIGHT_NAME_MATCH_GOSUSLUGI

    score = _clamp(score)

    if score >= weights.LEAD_SCORE_TIER_HIGH_MIN:
        tier = "high"
    elif score >= weights.LEAD_SCORE_TIER_MEDIUM_MIN:
        tier = "medium"
    else:
        tier = "low"

    return LeadScoreResult(score=score, tier=tier)
