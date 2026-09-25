"""One account, one grant, first payment only. No external IO in transactions."""
import os
import uuid
import math
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from core import models
from sqlalchemy import func, or_

PERCENT = 20


def pilot_user_ids():
    ids = set()
    for item in os.getenv('SIGNUP_DISCOUNT_PILOT_USER_IDS', '').split(','):
        try:
            ids.add(uuid.UUID(item.strip()))
        except ValueError:
            continue
    return ids


def enabled(user_id=None):
    # Enable only after deploying schema + configuring CloudPayments Check URL.
    if os.getenv('SIGNUP_DISCOUNT_ENABLED', '').lower() in {'1', 'true'}:
        return True
    try:
        return uuid.UUID(str(user_id)) in pilot_user_ids()
    except ValueError:
        return False


def any_enabled():
    return enabled() or bool(pilot_user_ids())


def aware(value):
    return value.replace(tzinfo=timezone.utc) if value and value.tzinfo is None else value


def now():
    return datetime.now(timezone.utc)


def has_paid(db, user_id):
    return db.query(models.BillingEvent.id).filter(
        models.BillingEvent.user_id == user_id, models.BillingEvent.event_type == 'pay',
        models.BillingEvent.amount > 0,
    ).first() is not None


def eligible_trial(db, user, sub):
    return bool(sub and sub.status == models.SubscriptionStatus.TRIAL
                and sub.current_period_end and aware(sub.current_period_end) > now()
                and not getattr(user, 'signup_discount_used_at', None) and not has_paid(db, user.id))


def active(db, user, sub):
    expiry = getattr(user, 'signup_discount_expires_at', None)
    return bool(enabled(user.id) and getattr(user, 'signup_discount_granted_at', None)
                and expiry and aware(expiry) > now() and eligible_trial(db, user, sub))


def grant_for_integration(db, integration, *, finalized=False):
    if not any_enabled() or not finalized or integration.platform not in {
        models.IntegrationPlatform.YANDEX_DIRECT, models.IntegrationPlatform.VK_ADS,
        models.IntegrationPlatform.AVITO_ADS,
    }:
        return False
    # Draft links / standalone Metrika are not connected advertising accounts.
    if not (integration.account_id or integration.agency_client_login) or not (integration.access_token or integration.platform_client_secret):
        return False
    from backend_api.services.subscription import SubscriptionService
    client = db.query(models.Client).filter(models.Client.id == integration.client_id).first()
    if not client or not enabled(client.owner_id):
        return False
    sub = SubscriptionService.get_user_subscription(db, client.owner_id, for_update=True)
    user = db.query(models.User).filter(models.User.id == client.owner_id).with_for_update().first()
    if not user or user.signup_discount_granted_at or not eligible_trial(db, user, sub):
        return False
    user.signup_discount_granted_at = now()
    user.signup_discount_expires_at = sub.current_period_end
    return True


def quote(plan_month, regular_price, billing):
    base = int(plan_month) * (12 if billing == 'year' else 1)
    discounted = int((Decimal(base) * Decimal('0.8')).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    return {'list_price': base, 'amount': min(int(regular_price), discounted),
            'discount_kind': 'year' if billing == 'year' and int(regular_price) < discounted else 'signup20'}


def status(db, user, sub):
    eligible = enabled(user.id) and eligible_trial(db, user, sub)
    granted = bool(getattr(user, 'signup_discount_granted_at', None))
    is_active = active(db, user, sub) if eligible else False
    return {'eligible': bool(eligible and (not granted or is_active)), 'active': is_active,
            'percent': PERCENT,
            'expires_at': getattr(user, 'signup_discount_expires_at', None) or (sub.current_period_end if sub else None),
            'modal_seen': bool(getattr(user, 'signup_discount_modal_seen_at', None)),
            'toast_seen': bool(getattr(user, 'signup_discount_toast_seen_at', None))}


def onboarding_status(db, user, sub):
    """Small indexed aggregates, not dashboard statistics or external API calls."""
    result = status(db, user, sub)
    paid = has_paid(db, user.id)
    end = aware(sub.current_period_end) if sub else None
    start = aware(sub.current_period_start) if sub else None
    trial = bool(sub and not paid and sub.status in {
        models.SubscriptionStatus.TRIAL, models.SubscriptionStatus.EXPIRED,
    })
    days = max(0, math.ceil((end - now()).total_seconds() / 86400)) if trial and end else 0
    used = bool(getattr(user, 'signup_discount_used_at', None))
    granted = bool(getattr(user, 'signup_discount_granted_at', None))
    state = ('used' if used else 'granted' if result['active'] else
             'expired' if granted or (trial and not days) else 'not_granted')
    projects = db.query(func.count(models.Client.id)).filter(models.Client.owner_id == user.id).scalar()
    cabinets = db.query(func.count(models.Integration.id)).join(
        models.Client, models.Client.id == models.Integration.client_id,
    ).filter(
        models.Client.owner_id == user.id,
        models.Integration.connection_status == 'active',
        models.Integration.platform.in_([
            models.IntegrationPlatform.YANDEX_DIRECT, models.IntegrationPlatform.VK_ADS,
            models.IntegrationPlatform.AVITO_ADS,
        ]),
        or_(models.Integration.account_id.notin_(['', '0']), models.Integration.agency_client_login != ''),
        or_(models.Integration.access_token != '', models.Integration.platform_client_secret != ''),
    ).scalar()
    result.update(trial_visible=trial and not used, trial_days_left=days,
                  trial_ends_at=end if trial else None,
                  trial_total_days=max(1, math.ceil((end - start).total_seconds() / 86400)) if trial and start and end else max(1, days),
                  projects_count=int(projects or 0), cabinets_count=int(cabinets or 0),
                  discount_state=state)
    return result
