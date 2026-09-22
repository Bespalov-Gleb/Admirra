from decimal import Decimal
from types import SimpleNamespace as NS
import pytest
from backend_api.services.purchase_analytics import purchase_snapshot, confirmed_purchase
from core.pricing import analytics_sku

@pytest.mark.parametrize('code,sku', [('start','start'), ('agency','basic'), ('pro','standard'), ('basic','basic'), ('standard','standard'), ('white_label','white_label')])
@pytest.mark.parametrize('period', ['month','year'])
def test_stable_sku(code, sku, period):
    assert analytics_sku(code, period) == f'{sku}_{period}'

def example():
    snapshot = purchase_snapshot(plan=NS(code='agency',name='Агентство'), billing='year', amount=66240, list_price=82800, signup_discount=True)
    intent = NS(user_id='owner', invoice_id='order', amount=Decimal('66240'), payload={'purpose':'plan','analytics':snapshot})
    payment = NS(user_id='owner',invoice_id='order',transaction_id='123',amount=Decimal('66240'),event_type='pay',currency='RUB')
    return intent, payment

def test_confirmed_uses_transaction_and_no_personal_data():
    i,p=example()
    data=confirmed_purchase(i,p)
    assert data['amount']==66240 and data['discount']==16560 and data['sku']=='basic_year'
    assert data['payment_id']=='123' and data['signup_discount'] is True
    assert not {'email','user_id','phone','account_id'} & data.keys()

@pytest.mark.parametrize('field,value', [('event_type','fail'),('event_type','rejected'),('amount',Decimal('0')), ('amount',Decimal('1')),('currency','USD'),('user_id','other'),('invoice_id','other'),('transaction_id',None)])
def test_no_unconfirmed_or_mismatched_charge(field,value):
    i,p=example(); setattr(p,field,value)
    assert confirmed_purchase(i,p) is None

def test_no_slot_or_legacy_purchase():
    i,p=example(); i.payload['purpose']='slot_purchase'
    assert confirmed_purchase(i,p) is None
    i.payload={}
    assert confirmed_purchase(i,p) is None


def test_archived_price_book_snapshot():
    data=purchase_snapshot(plan=NS(code='agency',name='Агентство'),billing='month',amount=5000,list_price=5000,price_book_version=1)
    assert data['price_book_version']==1
