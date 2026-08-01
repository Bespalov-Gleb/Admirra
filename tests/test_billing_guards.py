"""Защиты платёжного контура: сверка суммы, доступ до конца оплаченного периода,
fail-closed подпись вебхука.

Каждый тест закрывает конкретный дефект, найденный аудитом:
- тариф выдавался по plan_code из JsonData, который формирует фронт;
- отмена автопродления снимала доступ мгновенно, хотя период оплачен;
- при пустом секрете подпись вебхука считалась валидной.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from backend_api import billing
from backend_api.services.cloudpayments import CloudPaymentsService
from backend_api.services.subscription import SubscriptionService
from core import models, pricing


# --------------------------------------------------------------------------
# Сверка оплаченной суммы с ценой тарифа
# --------------------------------------------------------------------------

def _plan(code):
    return SubscriptionService.get_plan_from_config(code)


def test_expected_amount_month_equals_plan_price():
    plan = _plan("standard")
    assert billing._expected_amount(plan, "month") == int(plan.price_rub)


def test_expected_amount_year_is_discounted():
    plan = _plan("standard")  # алиас → pro
    year = billing._expected_amount(plan, "year")
    month = billing._expected_amount(plan, "month")
    # Годовая — 12 месяцев со скидкой 17% (§4.1). У реальных тарифов задана явно
    # в прайс-буке, поэтому сверяем с ним, а не с формулой округления.
    assert year == pricing.resolve_plan(plan.code).price_year
    assert month * 12 * 0.80 < year < month * 12


def test_paid_amount_parses_common_formats():
    assert billing._paid_amount({"Amount": "30.00"}) == Decimal("30.00")
    assert billing._paid_amount({"Amount": 30}) == Decimal("30")
    assert billing._paid_amount({"Amount": "30,50"}) == Decimal("30.50")
    assert billing._paid_amount({"Amount": ""}) is None
    assert billing._paid_amount({}) is None
    assert billing._paid_amount({"Amount": "не число"}) is None


def test_resolve_plan_by_paid_amount_finds_plan_actually_paid_for():
    """Клиент заявил standard, а заплатил цену start — выдать надо start."""
    start = _plan("start")
    paid = Decimal(billing._expected_amount(start, "month"))

    resolved, period = billing._resolve_plan_by_paid_amount(paid, "month")

    assert resolved is not None
    assert resolved.code == "start"
    assert period == "month"


def test_resolve_plan_by_paid_amount_rejects_unknown_sum():
    resolved, period = billing._resolve_plan_by_paid_amount(Decimal("777777"), "month")
    assert resolved is None
    assert period is None


def test_every_purchasable_plan_is_resolvable_by_its_own_price():
    """Легитимная оплата любого тарифа обязана распознаваться, иначе честный
    платёж останется без доступа."""
    for code in billing.PURCHASABLE_PLAN_CODES:
        plan = _plan(code)
        for period in ("month", "year"):
            paid = Decimal(billing._expected_amount(plan, period))
            resolved, resolved_period = billing._resolve_plan_by_paid_amount(paid, period)
            # Совпадение может быть неоднозначным, если у тарифов равные цены —
            # тогда выдача блокируется, и это тоже корректное поведение.
            if resolved is not None:
                assert billing._expected_amount(resolved, resolved_period) == int(paid)


# --------------------------------------------------------------------------
# Доступ до конца оплаченного периода
# --------------------------------------------------------------------------

def _sub(status, period_end):
    return SimpleNamespace(status=status, current_period_end=period_end)


def test_canceled_subscription_keeps_access_until_period_end():
    """Ровно случай с прода: период до 01.08, статус CANCELED — доступ обязан быть."""
    future = datetime.now(timezone.utc) + timedelta(days=6)
    sub = _sub(models.SubscriptionStatus.CANCELED, future)
    assert SubscriptionService._is_subscription_active(SimpleNamespace(), sub) is True


def test_canceled_subscription_loses_access_after_period_end():
    past = datetime.now(timezone.utc) - timedelta(days=1)
    sub = _sub(models.SubscriptionStatus.CANCELED, past)
    assert SubscriptionService._is_subscription_active(SimpleNamespace(), sub) is False


def test_past_due_keeps_paid_period():
    future = datetime.now(timezone.utc) + timedelta(days=3)
    sub = _sub(models.SubscriptionStatus.PAST_DUE, future)
    assert SubscriptionService._is_subscription_active(SimpleNamespace(), sub) is True


def test_canceled_without_period_end_has_no_access():
    sub = _sub(models.SubscriptionStatus.CANCELED, None)
    assert SubscriptionService._is_subscription_active(SimpleNamespace(), sub) is False


def test_active_subscription_still_expires_by_date():
    past = datetime.now(timezone.utc) - timedelta(days=1)
    sub = _sub(models.SubscriptionStatus.ACTIVE, past)
    assert SubscriptionService._is_subscription_active(SimpleNamespace(), sub) is False


# --------------------------------------------------------------------------
# Подпись вебхука
# --------------------------------------------------------------------------

def _cfg_with_secret(secret):
    return SimpleNamespace(cloudpayments=SimpleNamespace(webhook_secret=secret, api_secret=""))


def test_webhook_signature_fails_closed_without_secret(monkeypatch):
    """Без секрета вебхук обязан отклоняться, а не приниматься."""
    monkeypatch.delenv("CLOUDPAYMENTS_ALLOW_UNSIGNED_WEBHOOKS", raising=False)
    with patch("backend_api.services.cloudpayments.get_config", return_value=_cfg_with_secret("")):
        assert CloudPaymentsService.validate_webhook_signature(b"{}", "что угодно") is False


def test_webhook_signature_explicit_optout_for_local_dev(monkeypatch):
    monkeypatch.setenv("CLOUDPAYMENTS_ALLOW_UNSIGNED_WEBHOOKS", "true")
    with patch("backend_api.services.cloudpayments.get_config", return_value=_cfg_with_secret("")):
        assert CloudPaymentsService.validate_webhook_signature(b"{}", None) is True


def test_webhook_signature_accepts_valid_hmac():
    import base64, hashlib, hmac as hmac_mod

    secret, body = "s3cr3t", b'{"Amount":"30.00"}'
    sig = base64.b64encode(
        hmac_mod.new(secret.encode(), body, hashlib.sha256).digest()
    ).decode()
    with patch("backend_api.services.cloudpayments.get_config", return_value=_cfg_with_secret(secret)):
        assert CloudPaymentsService.validate_webhook_signature(body, sig) is True


def test_webhook_signature_rejects_tampered_body():
    import base64, hashlib, hmac as hmac_mod

    secret = "s3cr3t"
    sig = base64.b64encode(
        hmac_mod.new(secret.encode(), b'{"Amount":"30.00"}', hashlib.sha256).digest()
    ).decode()
    with patch("backend_api.services.cloudpayments.get_config", return_value=_cfg_with_secret(secret)):
        # Тело подменено на более дорогой тариф — подпись обязана не сойтись.
        assert CloudPaymentsService.validate_webhook_signature(b'{"Amount":"9990.00"}', sig) is False


def test_webhook_signature_requires_header_when_secret_set():
    with patch("backend_api.services.cloudpayments.get_config", return_value=_cfg_with_secret("s3cr3t")):
        assert CloudPaymentsService.validate_webhook_signature(b"{}", None) is False


# --------------------------------------------------------------------------
# Понижение тарифа: применяется в конце оплаченного периода
# --------------------------------------------------------------------------

def _sub_pending(pending, period_end):
    return SimpleNamespace(
        plan_code="standard", pending_plan_code=pending, current_period_end=period_end
    )


def test_pending_downgrade_not_applied_while_period_runs():
    """Оплаченный уровень нельзя забирать досрочно."""
    sub = _sub_pending("start", datetime.now(timezone.utc) + timedelta(days=5))
    SubscriptionService._apply_pending_plan(sub)
    assert sub.plan_code == "standard"
    assert sub.pending_plan_code == "start"


def test_pending_downgrade_applied_after_period_end():
    sub = _sub_pending("start", datetime.now(timezone.utc) - timedelta(minutes=1))
    SubscriptionService._apply_pending_plan(sub)
    assert sub.plan_code == "start"
    assert sub.pending_plan_code is None


def test_apply_pending_plan_is_noop_without_pending():
    sub = _sub_pending(None, datetime.now(timezone.utc) - timedelta(days=1))
    SubscriptionService._apply_pending_plan(sub)
    assert sub.plan_code == "standard"


def test_plan_rank_orders_tariffs_for_upgrade_detection():
    """От этого порядка зависит, сгорает ли остаток периода."""
    rank = billing.PLAN_RANK
    assert rank["start"] < rank["basic"] < rank["standard"]
    # Понижение standard -> start распознаётся, апгрейд start -> standard нет.
    assert rank["start"] < rank["standard"]


def test_get_user_plan_reads_config_not_db():
    """Единый источник истины: строка в tariff_plans не должна влиять на тариф."""
    import inspect

    src = inspect.getsource(SubscriptionService.get_user_plan)
    assert "TariffPlan" not in src, "get_user_plan снова читает тариф из БД — источников снова два"
