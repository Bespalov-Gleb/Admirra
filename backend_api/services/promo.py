"""Промокоды: валидация и расчёт скидки при оплате тарифа.

Скидка только процентная и только на первый платёж. Вся логика — на сервере:
цену со скидкой считает /billing/subscribe и фиксирует в серверном intent, а
вебхук сверяет с ним фактически списанную сумму. Фронт повлиять на сумму не может.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from core import models, pricing

# CloudPayments не принимает платёж ≤ 0 — итог после скидки клампим к этому минимуму.
MIN_CHARGE_RUB = 1


class PromoError(Exception):
    """Промокод неприменим. reason — машинный код, message — текст пользователю."""
    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason
        self.message = message


@dataclass
class PromoQuote:
    promo: "models.PromoCode"
    discount_percent: int
    original_amount: int
    discount_amount: int
    final_amount: int


def normalize_code(code: Optional[str]) -> str:
    return (code or "").strip().upper()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def compute_amounts(discount_percent: int, original_amount: int) -> tuple[int, int]:
    """(discount, final) для процентной скидки. final не опускается ниже минимума."""
    original = max(0, int(original_amount))
    pct = max(0, min(100, int(discount_percent)))
    final = int(round(original * (100 - pct) / 100))
    if original > 0:
        final = max(MIN_CHARGE_RUB, final)
    final = min(final, original)  # скидка не увеличивает сумму
    return original - final, final


def get_promo(db: Session, code: str) -> Optional["models.PromoCode"]:
    norm = normalize_code(code)
    if not norm:
        return None
    return db.query(models.PromoCode).filter(models.PromoCode.code == norm).first()


def _global_redemptions(db: Session, promo_id) -> int:
    return db.query(func.count(models.PromoRedemption.id)).filter(
        models.PromoRedemption.promo_code_id == promo_id
    ).scalar() or 0


def _user_redemptions(db: Session, promo_id, user_id) -> int:
    return db.query(func.count(models.PromoRedemption.id)).filter(
        models.PromoRedemption.promo_code_id == promo_id,
        models.PromoRedemption.user_id == user_id,
    ).scalar() or 0


def validate(
    db: Session,
    *,
    code: str,
    plan_code: str,
    billing_period: str,
    user: "models.User",
    original_amount: int,
) -> PromoQuote:
    """Проверяет код и возвращает расчёт скидки либо бросает PromoError.

    Проверки: существование, активность, окно дат, помесячность, привязка к
    тарифам, глобальный лимит, лимит на пользователя."""
    promo = get_promo(db, code)
    # hidden — системный код (win-back и т.п.): для вводимого пути его как бы нет.
    if promo is None or not promo.active or getattr(promo, "hidden", False):
        raise PromoError("not_found", "Промокод не найден или неактивен")

    now = _now()
    if promo.valid_from and now < _aware(promo.valid_from):
        raise PromoError("not_started", "Промокод ещё не действует")
    if promo.valid_until and now > _aware(promo.valid_until):
        raise PromoError("expired", "Срок действия промокода истёк")

    period = (billing_period or "month").lower()
    if promo.monthly_only and period != "month":
        raise PromoError("monthly_only", "Промокод действует только при помесячной оплате")

    allowed_plans = promo.applies_to_plans or None
    if allowed_plans:
        norm_allowed = {pricing.normalize_code(p) for p in allowed_plans}
        if pricing.normalize_code(plan_code) not in norm_allowed:
            raise PromoError("plan_mismatch", "Промокод не применим к выбранному тарифу")

    if promo.max_redemptions is not None and _global_redemptions(db, promo.id) >= promo.max_redemptions:
        raise PromoError("exhausted", "Лимит применений промокода исчерпан")

    per_user = promo.per_user_limit if promo.per_user_limit is not None else 1
    if per_user and _user_redemptions(db, promo.id, user.id) >= per_user:
        raise PromoError("user_limit", "Вы уже использовали этот промокод")

    discount_amount, final_amount = compute_amounts(promo.discount_percent, original_amount)
    return PromoQuote(
        promo=promo,
        discount_percent=int(promo.discount_percent),
        original_amount=int(original_amount),
        discount_amount=discount_amount,
        final_amount=final_amount,
    )


def record_redemption(
    db: Session,
    *,
    promo_id,
    user_id,
    invoice_id: Optional[str],
    transaction_id: Optional[str],
    plan_code: Optional[str],
    billing_period: Optional[str],
    original_amount,
    discount_amount,
    final_amount,
) -> Optional["models.PromoRedemption"]:
    """Идемпотентно фиксирует погашение. Повтор с тем же transaction_id/invoice
    не задваивает. Возвращает созданную запись или None (если уже было)."""
    if transaction_id:
        exists = db.query(models.PromoRedemption.id).filter(
            models.PromoRedemption.transaction_id == transaction_id
        ).first()
        if exists:
            return None
    if invoice_id:
        exists = db.query(models.PromoRedemption.id).filter(
            models.PromoRedemption.promo_code_id == promo_id,
            models.PromoRedemption.invoice_id == invoice_id,
        ).first()
        if exists:
            return None
    redemption = models.PromoRedemption(
        promo_code_id=promo_id,
        user_id=user_id,
        invoice_id=invoice_id,
        transaction_id=transaction_id,
        plan_code=plan_code,
        billing_period=billing_period,
        original_amount=original_amount,
        discount_amount=discount_amount,
        final_amount=final_amount,
    )
    db.add(redemption)
    return redemption


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


# ── Win-back: персональная одноразовая скидка при отказе от оплаты ────────────
# Реализована ПОВЕРХ промо-движка, но НЕВИДИМО для пользователя: отдельный
# скрытый код (нельзя ввести руками), применяется только серверным путём по
# гранту (флаг users.winback_offered_at). Сумму, как и у промо, считает и
# фиксирует сервер — фронт на неё не влияет. Погашения текут в ту же аналитику.
WINBACK_CODE = "WINBACK25"
WINBACK_DISCOUNT_PERCENT = 25
WINBACK_WINDOW_HOURS = 24        # грант живёт с момента показа баннера


def ensure_winback_promo(db: Session) -> "models.PromoCode":
    """Возвращает системный win-back промокод, создавая его при первом обращении."""
    promo = get_promo(db, WINBACK_CODE)
    if promo is None:
        promo = models.PromoCode(
            code=WINBACK_CODE,
            description="Персональная win-back скидка (системный код, не для ручного ввода)",
            discount_percent=WINBACK_DISCOUNT_PERCENT,
            active=True,
            hidden=True,
            per_user_limit=1,
            max_redemptions=None,
            monthly_only=False,
            applies_to_plans=None,
        )
        db.add(promo)
        db.commit()
        db.refresh(promo)
    return promo


def winback_eligible(db: Session, user: "models.User") -> bool:
    """Можно ли ПОКАЗАТЬ баннер: скидку ещё ни разу не предлагали и не гасили."""
    promo = ensure_winback_promo(db)
    if not promo.active:
        return False
    if getattr(user, "winback_offered_at", None) is not None:
        return False
    return _user_redemptions(db, promo.id, user.id) < 1


def validate_winback(db: Session, *, user: "models.User", original_amount: int) -> PromoQuote:
    """Авторитетная проверка при оплате: оффер был показан, в окне 24 ч, не погашен.
    Бросает PromoError, если грант неприменим. Расчёт — тем же compute_amounts."""
    promo = ensure_winback_promo(db)
    if not promo.active:
        raise PromoError("winback_inactive", "Персональная скидка недоступна")
    offered = getattr(user, "winback_offered_at", None)
    if offered is None:
        raise PromoError("winback_not_offered", "Персональная скидка недоступна")
    if _now() > _aware(offered) + timedelta(hours=WINBACK_WINDOW_HOURS):
        raise PromoError("winback_expired", "Срок персональной скидки истёк")
    if _user_redemptions(db, promo.id, user.id) >= 1:
        raise PromoError("winback_used", "Персональная скидка уже использована")
    discount_amount, final_amount = compute_amounts(promo.discount_percent, original_amount)
    return PromoQuote(
        promo=promo,
        discount_percent=int(promo.discount_percent),
        original_amount=int(original_amount),
        discount_amount=discount_amount,
        final_amount=final_amount,
    )
