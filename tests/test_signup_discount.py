from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as NS
from unittest.mock import MagicMock
import pytest
from core import models
from backend_api.services import signup_discount as d

NOW=datetime(2026,9,22,tzinfo=timezone.utc)

@pytest.fixture
def context(monkeypatch):
    monkeypatch.setenv('SIGNUP_DISCOUNT_ENABLED','true')
    monkeypatch.setattr(d,'now',lambda: NOW)
    db=MagicMock(); db.query.return_value.filter.return_value.first.return_value=None
    user=NS(id='owner',signup_discount_granted_at=NOW, signup_discount_expires_at=NOW+timedelta(days=3),signup_discount_used_at=None)
    sub=NS(status=models.SubscriptionStatus.TRIAL,current_period_end=NOW+timedelta(days=3))
    return db,user,sub

def test_active(context):
    assert d.active(*context)

@pytest.mark.parametrize('field,value', [('signup_discount_used_at',NOW),('signup_discount_granted_at',None), ('signup_discount_expires_at',NOW),('signup_discount_expires_at',NOW-timedelta(seconds=1))])
def test_ineligible_grant(context,field,value):
    db,u,s=context; setattr(u,field,value)
    assert not d.active(db,u,s)

def test_paid_or_not_trial(context):
    db,u,s=context
    db.query.return_value.filter.return_value.first.return_value=NS(id='paid')
    assert not d.active(db,u,s)
    db.query.return_value.filter.return_value.first.return_value=None
    s.status=models.SubscriptionStatus.ACTIVE
    assert not d.active(db,u,s)

def test_feature_off(context,monkeypatch):
    monkeypatch.delenv('SIGNUP_DISCOUNT_ENABLED')
    assert not d.active(*context)


def test_pilot_is_scoped(context, monkeypatch):
    import uuid
    db, user, sub = context
    user.id = uuid.uuid4()
    monkeypatch.setenv('SIGNUP_DISCOUNT_ENABLED', 'false')
    monkeypatch.setenv('SIGNUP_DISCOUNT_PILOT_USER_IDS', str(user.id) + ',invalid')
    assert not d.enabled()
    assert d.any_enabled()
    assert d.active(db, user, sub)
    assert d.status(db, user, sub)['eligible']
    user.id = uuid.uuid4()
    assert not d.active(db, user, sub)
    assert not d.status(db, user, sub)['eligible']

@pytest.mark.parametrize('monthly,regular,period,expected', [(6900,6900,'month',5520),(6900,69000,'year',66240), (2900,29000,'year',27840),(13900,139000,'year',133440), (6900,60000,'year',60000),(10,10,'month',8)])
def test_no_stacking_annual_discount(monthly,regular,period,expected):
    q=d.quote(monthly,regular,period)
    assert q['amount']==expected
    assert q['list_price']==monthly*(12 if period=='year' else 1)

def test_grant_skips_draft(context):
    db,_,_=context
    integration=NS(platform=models.IntegrationPlatform.VK_ADS,is_active=False)
    assert not d.grant_for_integration(db,integration)
