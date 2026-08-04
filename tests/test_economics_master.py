"""Регрессионные проверки мастер-ТЗ по экономике.

Тесты намеренно не обращаются к CloudPayments и production БД: они фиксируют
ценовую матрицу, серверные расчёты и обязательные защитные условия платёжного
контура, которые должны оставаться истинными при последующих правках.
"""
from types import SimpleNamespace
import inspect

from backend_api import billing
from backend_api.services.subscription import SubscriptionService
from core import pricing


def _billing_cfg(**overrides):
    values = {
        # Тестовые checkout-цены допустимы и должны оставаться настраиваемыми.
        "plan_start_price_rub": 10,
        "plan_basic_price_rub": 20,
        "plan_standard_price_rub": 30,
        "slot_price_start_rub": 1,
        "slot_price_agency_rub": 1,
        "slot_price_pro_rub": 1,
        "price_book_json": "",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_plan_matrix_limits_and_white_label_sales_mode():
    book = pricing.build_price_book(_billing_cfg())
    assert (book["start"].projects_limit, book["start"].cabinets_limit, book["start"].users_limit) == (3, 9, 2)
    assert (book["agency"].projects_limit, book["agency"].cabinets_limit, book["agency"].users_limit) == (10, 30, 6)
    assert (book["pro"].projects_limit, book["pro"].cabinets_limit, book["pro"].users_limit) == (25, 75, 15)
    assert book["white_label"].white_label is True
    assert "white_label" not in billing.PURCHASABLE_PLAN_CODES


def test_test_prices_remain_configurable_without_changing_product_limits():
    book = pricing.build_price_book(_billing_cfg())
    assert [book[c].price_month for c in ("start", "agency", "pro")] == [10, 20, 30]
    assert [book[c].extra_project_price_month for c in ("start", "agency", "pro")] == [1, 1, 1]
    assert [book[c].max_extra_project_slots for c in ("start", "agency", "pro")] == [3, 8, 10]


def test_unknown_public_plan_is_rejected_instead_of_becoming_start():
    try:
        pricing.resolve_plan_strict("definitely-not-a-plan", _billing_cfg())
    except ValueError:
        pass
    else:
        raise AssertionError("неизвестный код тарифа должен отклоняться")


def test_versioned_price_book_and_snapshot_restore_old_price():
    cfg = _billing_cfg(price_book_json='{"version":7,"plans":{"agency":{"price_month":7777}}}')
    current = pricing.build_price_book(cfg)["agency"]
    assert current.price_month == 7777
    assert pricing.current_price_book_version(cfg) == 7

    fallback = pricing.build_price_book(_billing_cfg(plan_basic_price_rub=9900))["agency"]
    restored = pricing.plan_from_snapshot({**current.__dict__, "_price_book_version": 7}, fallback)
    assert restored.price_month == 7777


def test_slot_is_part_of_recurring_total_and_separate_receipt_line():
    spec = pricing.build_price_book(_billing_cfg(
        plan_basic_price_rub=6900,
        slot_price_agency_rub=800,
    ))["agency"]
    plan = SubscriptionService.get_plan_from_config("agency", spec=spec)
    assert billing._subscription_total(plan, "month", 3) == 9300

    cfg = SimpleNamespace(cloudpayments=SimpleNamespace(
        receipt_vat=None,
        receipt_method=4,
        receipt_object=4,
        receipt_taxation_system=0,
    ))
    receipt = billing._subscription_receipt(plan, "month", 3, "owner@example.com", cfg)
    assert [item["amount"] for item in receipt["items"]] == [6900.0, 2400.0]
    assert "Дополнительные слоты" in receipt["items"][1]["label"]


def test_slot_checkout_requires_active_recurring_subscription():
    source = inspect.getsource(billing.slots_purchase)
    assert "active_subscription_required" in source
    assert "cloudpayments_subscription_id" in source
    assert "cancel_at_period_end" in source


def test_white_label_subscribe_is_blocked_by_backend_not_only_frontend():
    source = inspect.getsource(billing.subscribe)
    assert "requested_spec.white_label" in source
    assert "request_only" in source


def test_comments_soft_cap_scales_with_plan_projects():
    book = pricing.build_price_book(_billing_cfg())
    assert book["start"].effective_comments_soft_cap == 90
    assert book["agency"].effective_comments_soft_cap == 300
    assert book["pro"].effective_comments_soft_cap == 750
