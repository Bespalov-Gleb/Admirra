"""VK ID contact import: API-returned phone only, no real provider calls."""
import asyncio
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import parse_qs, urlparse
import uuid

import pytest
from fastapi import HTTPException, Request, Response
from backend_api import oauth_login as oauth
from core import models, schemas


@pytest.mark.parametrize('raw,expected', [
    ('79000000001','+79000000001'), ('+7 (900) 000-00-01','+79000000001'),
    ('  +442012345678  ','+442012345678'), ('+123456789012345','+123456789012345'),
    (None,None), ('',None), ('   ',None), ('+7 *** *** ** 01',None),
    ('+7••••••••01',None), ({'number':'79000000001'},None), (79000000001,None),
    (True,None), ('0000000',None), ('+123',None), ('+1234567890123456',None),
    ('7\n9000000001',None), ('7+9000000001',None), ('tel:+79000000001',None),
    ('+７９００００００００１',None), ('9'*10000,None),
])
def test_vk_phone_is_full_and_normalized(raw, expected):
    assert oauth._vk_profile_phone({'phone':raw}) == expected


@pytest.mark.parametrize('existing', [None,'','   ','+79000000002'])
def test_existing_contact_is_preserved(existing):
    user=SimpleNamespace(phone=existing)
    oauth._fill_missing_profile_phone(user,'+79000000001')
    assert user.phone == (existing if existing and existing.strip() else '+79000000001')
    oauth._fill_missing_profile_phone(user,None)
    assert user.phone


def test_authorize_url_requests_configured_phone_permission():
    with patch.object(oauth,'VK_LOGIN_CLIENT_ID','test'), patch.object(oauth,'VK_LOGIN_SCOPE','email phone'):
        result=oauth.vk_oauth_authorize_url('https://admirra.ru/auth/vk/callback','a'*43)
    params=parse_qs(urlparse(result['url']).query)
    assert params['scope'] == ['email phone']
    assert params['code_challenge_method'] == ['S256']
    assert params['response_type'] == ['code']


def callback_case(branch='new', raw_phone='+7 (900) 000-00-01', existing_phone=None, conflict=False):
    user=models.User(id=uuid.uuid4(),email='user@example.invalid',phone=existing_phone)
    current = user if branch=='attach' else None
    identity = SimpleNamespace(user_id=user.id) if branch=='existing' else None
    if conflict:
        current=models.User(id=uuid.uuid4(),email='other@example.invalid')
    db=MagicMock()
    added=[]
    committed=[]
    def add(row):
        added.append(row)
        if isinstance(row,models.User) and row.id is None:
            row.id=uuid.uuid4()
    db.add.side_effect=add
    def query(model):
        result=MagicMock()
        result.filter.return_value.first.return_value=identity if model is models.UserOAuthIdentity else user
        return result
    db.query.side_effect=query
    db.commit.side_effect=lambda: committed.append([r.phone for r in added if isinstance(r,models.User)])
    body=schemas.OAuthLoginCallbackRequest(code='test-code',state='test-state',
        redirect_uri='https://admirra.ru/auth/vk/callback',device_id='device',code_verifier='x'*43)
    info={'user_id':'123','email':'user@example.invalid','first_name':'Test','phone':raw_phone}
    with ExitStack() as stack:
        values={
            'VK_LOGIN_CLIENT_ID':'test-app', '_verify_oauth_state':MagicMock(),
            '_vk_id_exchange_code_for_login':AsyncMock(return_value={'access_token':'test-token','user_id':123}),
            '_vk_id_user_info':AsyncMock(return_value=info),
            '_optional_current_user':MagicMock(return_value=current),
            '_find_user_by_email_ci':MagicMock(return_value=user if branch=='email_match' else None),
            '_attach_identity':MagicMock(),
            '_issue_token_for_user':MagicMock(return_value={'access_token':'jwt','token_type':'bearer','is_new_user':False}),
        }
        for key,value in values.items():
            stack.enter_context(patch.object(oauth,key,value))
        stack.enter_context(patch.object(oauth.SubscriptionService,'ensure_default_subscription'))
        stack.enter_context(patch.object(oauth.security,'get_password_hash',return_value='test-hash'))
        if conflict:
            with pytest.raises(HTTPException) as error:
                asyncio.run(oauth.vk_oauth_callback(body,Request({'type':'http','headers':[]}),Response(),db))
            assert error.value.status_code==409
            assert user.phone is None
            db.commit.assert_not_called()
            return
        result=asyncio.run(oauth.vk_oauth_callback(body,Request({'type':'http','headers':[]}),Response(),db))
    target=next(r for r in added if isinstance(r,models.User)) if branch=='new' else user
    return result,target,db,committed


@pytest.mark.parametrize('branch',['new','existing','attach','email_match'])
def test_phone_saved_for_all_vk_account_paths(branch):
    result,user,db,commits=callback_case(branch)
    assert user.phone=='+79000000001'
    assert result['is_new_user']==(branch=='new')
    assert db.commit.called
    if branch=='new':
        assert commits[0]==['+79000000001']  # Present before registration/outbox commit.


@pytest.mark.parametrize('raw',[None,'','+7 *** *** ** 01',{},'garbage'])
def test_optional_phone_never_blocks_registration(raw):
    result,user,db,_=callback_case(raw_phone=raw)
    assert result['is_new_user'] is True
    assert user.phone is None


@pytest.mark.parametrize('branch',['existing','attach','email_match'])
@pytest.mark.parametrize('returned',[None,'+79000000001'])
def test_existing_contact_is_not_replaced_in_callback(branch,returned):
    _,user,_,_=callback_case(branch,returned,'+79000000002')
    assert user.phone=='+79000000002'


def test_identity_conflict_does_not_change_contact():
    callback_case('existing',conflict=True)
