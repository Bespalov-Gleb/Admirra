from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
import asyncio

import pytest

from backend_api import billing
from backend_api.services.subscription import SubscriptionService
from core import models, pricing


NOW = datetime(2026, 9, 16, 12, tzinfo=timezone.utc)


@pytest.fixture
def setup_slots(monkeypatch):
    sub = SimpleNamespace(
        id='test-sub', status=models.SubscriptionStatus.ACTIVE,
        current_period_end=NOW + timedelta(days=15),
        cloudpayments_subscription_id='test-recurring',
        cancel_at_period_end=False, billing_period='month',
        purchased_project_slots=0, price_book_snapshot={},
    )
    cfg = SimpleNamespace(
        plan_start_price_rub=2900, slot_price_start_rub=1100, price_book_json='',
    )
    spec = pricing.build_price_book(cfg)['start']
    plan = SubscriptionService.get_plan_from_config('start', spec=spec)
    user = SimpleNamespace(id='test-user', email='test@example.invalid')
    monkeypatch.setattr(SubscriptionService, '_now', staticmethod(lambda: NOW))
    monkeypatch.setattr(SubscriptionService, 'get_billing_account_user', lambda *a: user)
    monkeypatch.setattr(SubscriptionService, 'get_user_plan', lambda *a: plan)
    monkeypatch.setattr(SubscriptionService, 'get_user_subscription', lambda *a, **kw: sub)
    monkeypatch.setattr(SubscriptionService, 'ensure_default_subscription', lambda *a: sub)
    monkeypatch.setattr(billing, '_reserved_slot_count', lambda *a: 0)
    monkeypatch.setattr(billing, 'get_config', lambda: SimpleNamespace(
        cloudpayments=SimpleNamespace(public_id='test-only', currency='RUB'),
        billing=SimpleNamespace(ai_period_days=30, trial_days=7)))
    return sub, plan, user


def test_quote_amount_limits_and_renewal(setup_slots):
    sub, plan, user = setup_slots
    q = billing.slots_quote(SimpleNamespace(count=2), user, MagicMock())
    assert q.can_buy
    assert q.amount == 1100
    assert q.effective_limit_after == 5
    assert q.recurring_after == 5100


@pytest.mark.parametrize('field,value,reason', [
    ('current_period_end', NOW, 'active_subscription_required'),
    ('current_period_end', None, 'active_subscription_required'),
    ('current_period_end', NOW-timedelta(days=1), 'active_subscription_required'),
    ('cancel_at_period_end', True, 'active_subscription_required'),
    ('status', models.SubscriptionStatus.TRIAL, 'active_subscription_required'),
    ('cloudpayments_subscription_id', '', 'active_subscription_required'),
    ('pending_plan_code', 'agency', 'pending_subscription_change'),
    ('pending_billing_period', 'year', 'pending_subscription_change'),
    ('pending_purchased_project_slots', 0, 'pending_subscription_change'),
])
def test_quote_and_purchase_reject_ineligible_subscription(setup_slots, field, value, reason):
    sub, plan, user = setup_slots
    setattr(sub, field, value)
    q = billing.slots_quote(SimpleNamespace(count=1), user, MagicMock())
    assert not q.can_buy
    assert q.reason == reason
    with pytest.raises(billing.HTTPException) as error:
        billing.slots_purchase(SimpleNamespace(count=1), user, MagicMock())
    assert error.value.status_code == 409
    assert error.value.detail['reason'] == reason


def test_quote_respects_pending_reservations(setup_slots, monkeypatch):
    sub, plan, user = setup_slots
    monkeypatch.setattr(billing, '_reserved_slot_count', lambda *a: 2)
    q = billing.slots_quote(SimpleNamespace(count=2), user, MagicMock())
    assert not q.can_buy
    assert q.slots_until_parity == 1
    assert q.reason == 'pending_payment'
    with pytest.raises(billing.HTTPException) as error:
        billing.slots_purchase(SimpleNamespace(count=2), user, MagicMock())
    assert error.value.detail['reason'] == 'pending_payment'


def test_year_quote_and_cap(setup_slots):
    sub, plan, user = setup_slots
    sub.billing_period = 'year'
    sub.current_period_end = NOW + timedelta(days=365)
    q = billing.slots_quote(SimpleNamespace(count=1), user, MagicMock())
    assert q.amount == 10956
    assert q.recurring_after == 39956
    sub.current_period_end = NOW + timedelta(days=730)
    assert billing._slot_proration_amount(plan, sub, 1) == 10956


def test_new_catalog_prices():
    book = pricing.build_price_book(SimpleNamespace(price_book_json=''))
    for code, month, year, slot in [
        ('start', 2900, 29000, 1100),
        ('agency', 6900, 69000, 800),
        ('pro', 13900, 139000, 650),
    ]:
        assert book[code].price_month == month
        assert book[code].price_year == year
        assert book[code].extra_project_price_month == slot


@pytest.mark.parametrize('status,expected', [
    (models.SubscriptionStatus.TRIAL, 2900),
    (models.SubscriptionStatus.ACTIVE, 10),
])
def test_trial_uses_catalog_but_paid_subscription_keeps_snapshot(setup_slots, monkeypatch, status, expected):
    sub, plan, user = setup_slots
    sub.status = status
    sub.price_book_snapshot = {'price_month':10, 'price_year':100}
    catalog = pricing.build_price_book(SimpleNamespace(price_book_json=''))
    monkeypatch.setattr(pricing, 'list_plans', lambda **kw: list(catalog.values()))
    plans = billing.get_plans(user, MagicMock())
    start = next(p for p in plans if p.code == 'start')
    assert start.price_rub == expected


@pytest.mark.parametrize('status,expected', [
    (models.SubscriptionStatus.TRIAL, 2900),
    (models.SubscriptionStatus.ACTIVE, 10),
])
def test_checkout_and_intent_match_catalog_or_fixed_price(setup_slots, monkeypatch, status, expected):
    sub, plan, user = setup_slots
    sub.status = status
    plan.price_rub = 10
    sub.price_book_snapshot = {'code':'start', 'price_month':10, 'price_year':100}
    monkeypatch.setattr(SubscriptionService, 'count_project_slots', lambda *a: 3)
    monkeypatch.setattr(billing, '_subscription_receipt', lambda *a: None)
    monkeypatch.setattr(billing, '_recurrent_for_billing_period', lambda *a: None)
    recorded = {}
    def invoice(*a, **kw):
        recorded.update(kw)
        return 'test-invoice'
    monkeypatch.setattr(billing, '_reuse_or_create_invoice', invoice)
    body = SimpleNamespace(plan_code='start', billing_period='month', winback=False, promo_code=None)
    response = asyncio.run(billing.subscribe(body, user, MagicMock()))
    assert response.amount == expected
    assert recorded['amount'] == expected
    assert recorded['intent_payload']['price_book_snapshot']['price_month'] == expected
