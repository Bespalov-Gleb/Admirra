"""Synthetic PostgreSQL only: account scope, lifecycle and concurrent claims."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
from core import models, schemas
from backend_api import billing, auth
from tests.test_signup_discount_flow import pg, scope, grant, checkout, check, webhook


def read(scope):
    factory, uid, _ = scope
    with factory() as db:
        return billing.signup_discount_status(db.get(models.User, uid), db)


def test_trial_lifecycle(scope):
    factory, uid, iid = scope
    with factory.begin() as db:
        db.get(models.Integration, iid).account_id = None  # unfinished OAuth
    s = read(scope)
    assert s['trial_visible'] and s['trial_days_left'] == 7
    assert s['projects_count'] == 1 and s['cabinets_count'] == 0
    assert s['discount_state'] == 'not_granted'
    with factory.begin() as db:
        db.get(models.Integration, iid).account_id = 'synthetic'
    assert grant(scope)
    s = read(scope)
    assert s['discount_state'] == 'granted' and s['cabinets_count'] == 1
    q = checkout(scope)
    assert check(scope, q) == 0 and webhook(scope, q).code == 0
    s = read(scope)
    assert not s['trial_visible'] and s['discount_state'] == 'used'
    assert not s['eligible'] and not s['active']


def test_expired_trial_does_not_offer_again(scope):
    factory, uid, _ = scope
    grant(scope)
    with factory.begin() as db:
        sub = db.query(models.Subscription).filter_by(user_id=uid).one()
        sub.current_period_end = datetime.now(timezone.utc) - timedelta(seconds=1)
        sub.status = models.SubscriptionStatus.EXPIRED
        db.get(models.User, uid).signup_discount_expires_at = sub.current_period_end
    s = read(scope)
    assert s['trial_visible'] and s['trial_days_left'] == 0
    assert s['discount_state'] == 'expired' and not s['eligible']
    assert not grant(scope)


def test_only_owner_real_ad_accounts_count(scope):
    factory, uid, iid = scope
    with factory.begin() as db:
        integ = db.get(models.Integration, iid)
        integ.platform = models.IntegrationPlatform.YANDEX_METRIKA
        other = models.User(email='other@example.test', password_hash='synthetic'); db.add(other); db.flush()
        client = models.Client(owner_id=other.id, name='Other'); db.add(client); db.flush()
        db.add(models.Integration(client_id=client.id, platform=models.IntegrationPlatform.VK_ADS,
                                 access_token='synthetic', account_id='other'))
    s = read(scope)
    assert s['projects_count'] == 1 and s['cabinets_count'] == 0


def test_offer_claim_serialized_across_tabs(scope):
    factory, uid, _ = scope
    def claim(_):
        with factory() as db:
            return auth.claim_metrika_milestone(schemas.MetrikaMilestoneRequest(name='signup_offer_click'), db.get(models.User, uid), db).first
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(claim, range(2)))
    assert sorted(results) == [False, True]
    with factory() as db:
        assert json.loads(db.get(models.User, uid).ym_milestones) == ['signup_offer_click']


def test_checkout_confirmation_analytics_and_receipt(scope):
    factory, uid, _ = scope
    grant(scope); q = checkout(scope, onboarding=True)
    assert check(scope, q) == 0 and webhook(scope, q).code == 0
    with factory() as db:
        p = billing.payment_confirmation(q.invoice_id, db.get(models.User, uid), db)['purchase']
    assert p['discount_kind'] == 'signup20' and p['trial_to_paid'] is True
    assert p['amount'] == 5520
    from backend_api.services import metrika_conversions
    assert metrika_conversions.upload_offline_conversion.call_args_list == []
