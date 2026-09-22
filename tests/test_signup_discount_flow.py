import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import uuid
import os
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request

from core import models, schemas
from backend_api import billing
from backend_api.services import signup_discount as discount, signup_discount_mail as mail
from backend_api.services.subscription import SubscriptionService


@pytest.fixture
def pg():
    url = os.getenv('ISOLATED_POSTGRES_URL')
    if not url:
        pytest.skip('requires isolated PostgreSQL')
    assert os.getenv('WW_TEST') == '1' and urlsplit(url).hostname == 'test-db'
    schema = 'signup_' + uuid.uuid4().hex
    admin = sa.create_engine(url)
    with admin.begin() as db:
        db.execute(sa.text(f'CREATE SCHEMA "{schema}"'))
    engine = sa.create_engine(url, connect_args={'options': f'-csearch_path={schema} -cstatement_timeout=5000'})
    try:
        yield sessionmaker(bind=engine), engine
    finally:
        engine.dispose()
        with admin.begin() as db:
            db.execute(sa.text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


@pytest.fixture
def scope(pg, monkeypatch):
    factory, engine = pg
    models.Base.metadata.create_all(engine)
    monkeypatch.setenv('SIGNUP_DISCOUNT_ENABLED','true')
    cfg=deepcopy(billing.get_config())
    cfg.cloudpayments.public_id='isolated-test'
    cfg.billing.plan_basic_price_rub=6900
    monkeypatch.setattr(billing,'get_config',lambda:cfg)
    monkeypatch.setattr(billing.CloudPaymentsService,'validate_webhook_signature',lambda *a: True)
    monkeypatch.setattr(billing,'_update_recurrent_total',AsyncMock(return_value=True))
    monkeypatch.setattr(mail,'SessionLocal',factory)
    from backend_api.services import metrika_conversions
    monkeypatch.setattr(metrika_conversions,'upload_offline_conversion',AsyncMock(return_value=True))
    with factory.begin() as db:
        user=models.User(email=f'{uuid.uuid4()}@example.test',password_hash='synthetic',email_verified=True)
        db.add(user); db.flush()
        uid=user.id
        db.add(models.Subscription(user_id=uid,plan_code='start',status=models.SubscriptionStatus.TRIAL,
            current_period_start=datetime.now(timezone.utc),current_period_end=datetime.now(timezone.utc)+timedelta(days=7)))
        client=models.Client(owner_id=uid,name='Synthetic'); db.add(client); db.flush()
        integration=models.Integration(client_id=client.id,platform=models.IntegrationPlatform.YANDEX_DIRECT,
            access_token='synthetic-not-real',account_id='test')
        db.add(integration); db.flush(); iid=integration.id
    return factory,uid,iid


def grant(scope):
    factory,uid,iid=scope
    with factory.begin() as db:
        return discount.grant_for_integration(db,db.get(models.Integration,iid),finalized=True)


def checkout(scope, period='month'):
    factory,uid,_=scope
    with factory() as db:
        return asyncio.run(billing.subscribe(schemas.BillingSubscribeRequest(plan_code='agency',billing_period=period), db.get(models.User,uid),db))


def request(data):
    async def receive():
        return {'type':'http.request','body':json.dumps(data).encode()}
    return Request({'type':'http','headers':[(b'content-type',b'application/json')]},receive)


def check(scope, quote, transaction='test-tx', **overrides):
    factory,uid,_=scope
    data={'AccountId':str(uid),'InvoiceId':quote.invoice_id,'Amount':quote.amount,'Currency':'RUB','TransactionId':transaction,**overrides}
    with factory() as db:
        return asyncio.run(billing.cloudpayments_check(request(data),db)).code


def test_grant_is_once_survives_disconnect_and_reconnect(scope):
    assert grant(scope)
    assert not grant(scope)
    factory,uid,iid=scope
    with factory.begin() as db:
        user=db.get(models.User,uid); expiry=user.signup_discount_expires_at
        db.get(models.Integration,iid).access_token=None
    assert not grant(scope)
    with factory.begin() as db:
        db.get(models.Integration,iid).access_token='synthetic-not-real'
    assert not grant(scope)
    with factory() as db:
        assert db.get(models.User,uid).signup_discount_expires_at==expiry


@pytest.mark.parametrize('period,amount', [('month',6900), ('year',69000)])
def test_disabled_feature_preserves_regular_payments(scope,monkeypatch,period,amount):
    monkeypatch.setenv('SIGNUP_DISCOUNT_ENABLED','false')
    monkeypatch.setenv('SIGNUP_DISCOUNT_PILOT_USER_IDS','')
    assert not grant(scope)
    factory,uid,_=scope
    with factory() as db:
        user=db.get(models.User,uid)
        assert billing.signup_discount_status(user,db)['eligible'] is False
        assert billing.signup_discount_claim_display('modal',user,db)['show'] is False
    q=checkout(scope,period)
    assert q.amount==amount and not q.signup_discount
    assert 'userRequisiteData' not in q.receipt
    assert check(scope,q)==0
    assert webhook(scope,q).code==0
    with factory() as db:
        result=billing.payment_confirmation(q.invoice_id,db.get(models.User,uid),db)
        assert result['purchase']['amount']==amount
        assert db.get(models.User,uid).signup_discount_used_at is None
    assert asyncio.run(mail.send_signup_discount_reminders())==0


def test_pilot_grant_and_mail_do_not_touch_other_accounts(scope,monkeypatch):
    factory,uid,_=scope
    monkeypatch.setenv('SIGNUP_DISCOUNT_ENABLED','false')
    monkeypatch.setenv('SIGNUP_DISCOUNT_PILOT_USER_IDS',str(uuid.uuid4()))
    assert not grant(scope)
    monkeypatch.setenv('SIGNUP_DISCOUNT_PILOT_USER_IDS',str(uid))
    assert grant(scope)
    with factory.begin() as db:
        db.get(models.User,uid).signup_discount_expires_at=datetime.now(timezone.utc)+timedelta(hours=47)
    monkeypatch.setenv('SIGNUP_DISCOUNT_PILOT_USER_IDS',str(uuid.uuid4()))
    assert not checkout(scope).signup_discount
    assert asyncio.run(mail.send_signup_discount_reminders())==0
    with factory() as db:
        assert db.get(models.User,uid).signup_discount_reminder_claimed_at is None


@pytest.mark.parametrize('period,amount,total,discount_amount',[('month',5520,6900,1380),('year',66240,69000,16560)])
def test_checkout_receipt_full_renewal_and_confirmation(scope,period,amount,total,discount_amount):
    grant(scope); quote=checkout(scope,period)
    assert quote.amount==amount and quote.signup_discount
    assert quote.discount_amount==discount_amount
    assert quote.recurrent.amount==total
    assert quote.recurrent.customerReceipt['items'][0]['amount']==total
    assert quote.receipt['items'][0]['amount']==amount
    assert 'userRequisiteData' in quote.receipt and 'additionalReceiptInfos' in quote.receipt
    assert sum(i['amount'] for i in quote.receipt['items'])==quote.receipt['amounts']['electronic']==amount
    assert check(scope,quote)==0
    assert check(scope,quote)==0
    assert check(scope,quote,'second-tx')==13
    with pytest.raises(billing.HTTPException) as error:
        checkout(scope,period)
    assert error.value.status_code==409


def test_old_invoice_is_rejected_when_plan_selection_changes(scope):
    grant(scope); first=checkout(scope); second=checkout(scope,'year')
    assert check(scope,first)==13
    assert check(scope,second)==0


def test_expired_and_wrong_amount_checks(scope):
    grant(scope); q=checkout(scope)
    assert check(scope,q,Amount=q.amount-1)==12
    factory,uid,_=scope
    with factory.begin() as db:
        db.get(models.User,uid).signup_discount_expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)
    assert check(scope,q)==20


def test_display_claim_once(scope):
    factory,uid,_=scope
    with factory() as db:
        user=db.get(models.User,uid)
        assert billing.signup_discount_claim_display('modal',user,db)['show']
        assert not billing.signup_discount_claim_display('modal',user,db)['show']
    grant(scope)
    with factory() as db:
        user=db.get(models.User,uid)
        assert billing.signup_discount_claim_display('toast',user,db)['show']
        assert not billing.signup_discount_claim_display('toast',user,db)['show']


def test_reminder_once_no_sql_during_smtp(scope,monkeypatch):
    grant(scope)
    factory,uid,_=scope
    with factory.begin() as db:
        db.get(models.User,uid).signup_discount_expires_at=datetime.now(timezone.utc)+timedelta(hours=47)
    sent=[]
    def sender(email,subject,body,**kwargs):
        assert factory.kw['bind'].pool.checkedout()==0
        assert 'https://admirra.ru/tariffs' in kwargs['html_body']
        sent.append((subject,body)); return True
    monkeypatch.setattr(mail,'_send_sync',sender)
    assert asyncio.run(mail.send_signup_discount_reminders())==1
    assert asyncio.run(mail.send_signup_discount_reminders())==0
    assert len(sent)==1 and 'https://admirra.ru/tariffs' in sent[0][1]


def test_concurrent_grant_only_once(scope):
    with ThreadPoolExecutor(3) as pool:
        results=list(pool.map(lambda _:grant(scope),range(3)))
    assert sum(results)==1


def webhook(scope,quote,transaction='test-tx',event='Pay',**overrides):
    factory,uid,_=scope
    data={'AccountId':str(uid),'InvoiceId':quote.invoice_id,'TransactionId':transaction,
          'Amount':quote.amount,'Currency':'RUB','Type':event,'Status':'Completed' if event=='Pay' else 'Declined',**overrides}
    with factory() as db:
        return asyncio.run(billing.cloudpayments_webhook(request(data),db))


def test_pay_consumes_once_and_server_confirms_purchase(scope):
    grant(scope); q=checkout(scope)
    factory,uid,_=scope
    with factory() as db:
        assert billing.payment_confirmation(q.invoice_id,db.get(models.User,uid),db)['status']=='pending'
    assert check(scope,q)==0
    assert webhook(scope,q).code==0
    assert webhook(scope,q).code==0
    with factory() as db:
        user=db.get(models.User,uid)
        assert user.signup_discount_used_at
        result=billing.payment_confirmation(q.invoice_id,user,db)
        assert result['status']=='confirmed' and result['purchase']['amount']==5520
        assert result['purchase']['payment_id']=='test-tx'
        assert db.query(models.BillingEvent).filter_by(event_type='pay',user_id=uid).count()==1
    assert not checkout(scope).signup_discount


def test_failed_payment_does_not_burn_discount(scope):
    grant(scope); q=checkout(scope)
    assert check(scope,q)==0
    assert webhook(scope,q,event='Fail').code==0
    factory,uid,_=scope
    with factory() as db:
        assert db.get(models.User,uid).signup_discount_used_at is None
    # Failed payment changes subscription status in legacy billing; verify that
    # trial eligibility is preserved for signup offers rather than lost.
    assert checkout(scope).signup_discount


def test_confirmation_does_not_expose_other_accounts(scope):
    grant(scope); q=checkout(scope)
    factory,uid,_=scope
    with factory.begin() as db:
        other=models.User(email='other@example.test',password_hash='synthetic');db.add(other);db.flush()
        with pytest.raises(billing.HTTPException) as error:
            billing.payment_confirmation(q.invoice_id,other,db)
        assert error.value.status_code==404


def test_discount_pay_without_check_is_not_accepted(scope):
    grant(scope); q=checkout(scope)
    assert webhook(scope,q).code==0
    factory,uid,_=scope
    with factory() as db:
        user=db.get(models.User,uid)
        assert user.signup_discount_used_at is None
        assert billing.payment_confirmation(q.invoice_id,user,db)['status'] != 'confirmed'
        assert db.query(models.Subscription).filter_by(user_id=uid).one().status==models.SubscriptionStatus.TRIAL


def test_check_requires_signature(scope,monkeypatch):
    grant(scope); q=checkout(scope)
    monkeypatch.setattr(billing.CloudPaymentsService,'validate_webhook_signature',lambda *a:False)
    with pytest.raises(billing.HTTPException) as error:
        check(scope,q)
    assert error.value.status_code==401


def test_signup_schema_roundtrip(pg):
    import importlib.util
    from pathlib import Path
    import sqlalchemy as sa
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    _, engine=pg
    spec=importlib.util.spec_from_file_location('signup_schema', Path(__file__).resolve().parents[1] / 'alembic/versions/ef1a2b3c4d5e_signup_discount.py')
    migration=importlib.util.module_from_spec(spec); spec.loader.exec_module(migration)
    with engine.begin() as db:
        db.execute(sa.text('CREATE TABLE users (id integer PRIMARY KEY)'))
        db.execute(sa.text('INSERT INTO users (id) VALUES (1)'))
        migration.op=Operations(MigrationContext.configure(db))
        migration.upgrade()
        migration.upgrade()  # adopt a separately deployed additive schema safely
        assert len(sa.inspect(db).get_columns('users'))==9
        assert db.execute(sa.text('SELECT signup_discount_used_at FROM users WHERE id=1')).scalar() is None
        assert len(sa.inspect(db).get_indexes('users'))==1
        migration.downgrade()
        assert [col['name'] for col in sa.inspect(db).get_columns('users')]==['id']
        assert db.execute(sa.text('SELECT count(*) FROM users')).scalar()==1


def test_full_price_renewal_keeps_original_purchase_confirmation(scope,monkeypatch):
    grant(scope); q=checkout(scope)
    assert check(scope,q)==0
    assert webhook(scope,q,SubscriptionId='test-recurring').code==0
    from backend_api.services import metrika_conversions
    assert [c.kwargs['target'] for c in metrika_conversions.upload_offline_conversion.call_args_list]==['trial_to_paid']
    assert check(scope,q,SubscriptionId='test-recurring')==13
    assert check(scope,q,'renewal',SubscriptionId='wrong',Amount=6900)==13
    assert check(scope,q,'renewal',SubscriptionId='test-recurring')==12
    assert check(scope,q,'renewal',SubscriptionId='test-recurring',Amount=6900)==0
    assert webhook(scope,q,'renewal',SubscriptionId='test-recurring',Amount=6900).code==0
    factory,uid,_=scope
    with factory() as db:
        purchase=billing.payment_confirmation(q.invoice_id,db.get(models.User,uid),db)['purchase']
        assert purchase['payment_id']=='test-tx' and purchase['amount']==5520
