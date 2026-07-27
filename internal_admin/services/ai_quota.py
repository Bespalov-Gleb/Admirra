"""Сброс AI-квоты по биллинговому циклу (30 дней, ТЗ v1.0)."""
from datetime import datetime, timedelta, timezone

from core import models


def _now() -> datetime:
    return datetime.now(timezone.utc)


def schedule_ai_quota_reset(user: models.User, *, anchor: datetime | None = None) -> None:
    """Устанавливает дату следующего сброса через 30 дней от anchor (оплата / старт триала)."""
    base = anchor or _now()
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    user.ai_quota_resets_at = base + timedelta(days=30)
    if user.ai_requests_period_started_at is None:
        user.ai_requests_period_started_at = base


def maybe_reset_ai_quota(user: models.User) -> bool:
    """
    Если наступила дата сброса — обнуляет счётчик и переносит ai_quota_resets_at на +30 дней.
    Возвращает True, если сброс выполнен.
    """
    resets_at = user.ai_quota_resets_at
    if not resets_at:
        return False
    if resets_at.tzinfo is None:
        resets_at = resets_at.replace(tzinfo=timezone.utc)
    now = _now()
    if now < resets_at:
        return False
    user.ai_requests_used = 0
    user.ai_requests_period_started_at = now
    user.ai_quota_resets_at = now + timedelta(days=30)
    return True
