"""Immutable, non-PII analytics captured with a server-priced payment intent."""
from decimal import Decimal

from core import pricing


def purchase_snapshot(*, plan, billing, amount, list_price, coupon=None, goal='payment_success', signup_discount=False, price_book_version=None):
    return {
        'plan': pricing.normalize_code(plan.code), 'name': plan.name,
        'sku': pricing.analytics_sku(plan.code, billing),
        'billing': billing, 'list_price': float(list_price),
        'discount': float(max(Decimal('0'), Decimal(str(list_price)) - Decimal(str(amount)))),
        'coupon': coupon or None, 'goal': goal, 'signup_discount': bool(signup_discount),
        'price_book_version': price_book_version or pricing.current_price_book_version(),
    }


def confirmed_purchase(intent, payment):
    """Only accepted Pay events, never client success callbacks or charge attempts."""
    meta = (intent.payload or {}).get('analytics')
    if (not isinstance(meta, dict) or (intent.payload or {}).get('purpose') != 'plan'
            or payment.event_type != 'pay' or not payment.transaction_id
            or payment.user_id != intent.user_id or payment.invoice_id != intent.invoice_id
            or payment.amount is None or payment.amount <= 0
            or payment.amount != intent.amount or payment.currency != 'RUB'):
        return None
    return {**meta, 'payment_id': str(payment.transaction_id),
            'amount': float(payment.amount), 'currency': 'RUB'}
