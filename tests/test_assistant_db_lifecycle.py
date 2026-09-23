"""Real SQL/ORM lifecycles, fake providers: a single DB slot must stay free in IO."""
import asyncio
from contextlib import aclosing, asynccontextmanager
from datetime import datetime, timedelta, timezone
import json
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
import httpx
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from ai.assistant import agent, tools, token_provider
from ai.assistant.db_lifecycle import AccessChanged
from core import models, security
from tests.assistant_pg import pg


@pytest.fixture
def source(pg, monkeypatch):
    _, admin = pg
    models.Base.metadata.create_all(admin)
    with admin.connect() as conn:
        schema = conn.scalar(sa.text('SELECT current_schema()'))
    engine = sa.create_engine(admin.url, pool_size=1, max_overflow=0, pool_timeout=.3,
        connect_args={'options': f'-csearch_path={schema} -cstatement_timeout=5000'})
    factory = sessionmaker(bind=engine)
    with factory.begin() as db:
        user = models.User(email='lifecycle@example.test', password_hash='synthetic')
        db.add(user); db.flush()
        project = models.Client(owner_id=user.id, name='Synthetic project')
        db.add(project); db.flush()
        conv = models.AiConversation(user_id=user.id, client_id=project.id, model='synthetic')
        db.add(conv); db.flush()
        ids = {}
        for platform in (models.IntegrationPlatform.YANDEX_DIRECT, models.IntegrationPlatform.VK_ADS,
                         models.IntegrationPlatform.AVITO_ADS):
            integration = models.Integration(client_id=project.id, platform=platform,
                account_id='cabinet', account_name='Synthetic', connection_status='active',
                access_token=security.encrypt_token('old-token'), refresh_token=security.encrypt_token('old-refresh'),
                platform_client_id=security.encrypt_token('app'), platform_client_secret=security.encrypt_token('secret'),
                expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
                selected_counters='["123"]', selected_goals='["456"]')
            db.add(integration); db.flush()
            ids[platform.value] = integration.id
        attachment = models.AiMessage(conversation_id=conv.id, role='attachment', content='Document text',
            tool_calls={'filename': 'test.md', 'size': 13})
        db.add(attachment); db.flush()
        db.add(models.AiMessage(conversation_id=conv.id, role='user', content='Old question',
            tool_calls={'attachments': [{'id': str(attachment.id)}]}))
        keys = SimpleNamespace(user=user.id, project=project.id, conv=conv.id, attachment=attachment.id,
                               integrations=ids)
    monkeypatch.setattr(agent.llm, 'is_configured', lambda: True)
    monkeypatch.setattr(agent, 'cfg', SimpleNamespace(openrouter=SimpleNamespace(max_tool_iterations=5)))
    try:
        yield factory, engine, keys
    finally:
        assert engine.pool.checkedout() == 0
        engine.dispose()


def context(db, keys):
    ctx = tools.ToolContext(db, db.get(models.User, keys.user), db.get(models.AiConversation, keys.conv))
    ctx.set_project(keys.project)
    return ctx


def assert_free(engine, db):
    assert not db.in_transaction()
    assert engine.pool.checkedout() == 0
    # A second request must be able to borrow the ONLY SQL connection.
    with engine.connect() as connection:
        assert connection.scalar(sa.text('SELECT 1')) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize('forced', [False, True])
async def test_llm_tools_attachments_and_sse_never_hold_sql(source, monkeypatch, forced):
    factory, engine, keys = source
    calls = []
    if forced:
        monkeypatch.setattr(agent, 'cfg', SimpleNamespace(openrouter=SimpleNamespace(max_tool_iterations=1)))
    with factory() as db:
        async def complete(**kwargs):
            assert_free(engine, db)
            calls.append(kwargs)
            if len(calls) == 1:
                assert 'Document text' in str(kwargs['messages'])
                yield {'type': 'message', 'message': {'tool_calls': [
                    {'id': 'tool-1', 'function': {'name': 'list_projects', 'arguments': '{}'}}]}}
            else:
                assert (kwargs['tools'] is None) == forced
                yield {'type': 'text', 'delta': 'Answer'}
                assert_free(engine, db)
                yield {'type': 'message', 'message': {'content': 'Answer'},
                       'usage': {'prompt_tokens': 2, 'completion_tokens': 1}}
        monkeypatch.setattr(agent.llm, 'stream_completion', complete)
        events = []
        async for event in agent.run(db, db.get(models.AiConversation, keys.conv), 'Question',
                SimpleNamespace(id='synthetic'), None, db.get(models.User, keys.user),
                attachments=[db.get(models.AiMessage, keys.attachment)]):
            assert_free(engine, db)  # Includes tool start/done and final message id.
            events.append(event)
        done = next(event for event in events if event['type'] == 'done')
        assert db.get(models.AiMessage, UUID(done['message_id'])).content == 'Answer'
    assert len(calls) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize('kind', ['yandex', 'vk', 'avito', 'wordstat'])
async def test_live_tools_and_oauth_run_without_sql(source, monkeypatch, kind):
    factory, engine, keys = source
    from backend_api.services import IntegrationService
    from automation.vk_ads import VKAdsAPI
    from automation.avito_ads import AvitoAdsAPI
    from ai.assistant.yandex_client import AiYandexClient
    with factory() as db:
        ctx = context(db, keys)
        async def refreshed(*args):
            assert_free(engine, db)
            await asyncio.sleep(0)
            return {'access_token': 'new-token', 'refresh_token': 'new-refresh', 'expires_in': 3600}
        monkeypatch.setattr(IntegrationService, 'refresh_yandex_token', refreshed)
        monkeypatch.setattr(IntegrationService, 'refresh_vk_token', refreshed)
        async def direct(client, *args):
            assert_free(engine, db)
            assert client.access.access_token() == 'old-token'
            assert await client.access.refresh() == 'new-token'
            assert_free(engine, db)
            return {'Campaigns': [{'Id': 1}]}
        async def balance(*args):
            assert_free(engine, db)
            return {'balance': 123}
        monkeypatch.setattr(AiYandexClient, 'direct_call', direct)
        monkeypatch.setattr(VKAdsAPI, 'get_balance', balance)
        monkeypatch.setattr(AvitoAdsAPI, 'get_balance', balance)
        monkeypatch.setattr(tools.wordstat_client, 'top_requests', balance)
        names = {'yandex': 'direct_get_campaigns', 'vk': 'vk_get_balance',
                 'avito': 'avito_get_balance', 'wordstat': 'wordstat_top_requests'}
        result = json.loads(await tools.execute_tool(names[kind], {'phrase': 'test'}, ctx))
        assert 'error' not in result, result
        assert_free(engine, db)
    if kind in {'yandex', 'vk'}:
        platform = 'YANDEX_DIRECT' if kind == 'yandex' else 'VK_ADS'
        with factory() as db:
            assert security.decrypt_token(db.get(models.Integration, keys.integrations[platform]).access_token) == 'new-token'


@pytest.mark.asyncio
@pytest.mark.parametrize('change', ['token', 'account', 'user', 'project', 'delete'])
async def test_late_refresh_cannot_overwrite_changed_access(source, monkeypatch, change):
    factory, engine, keys = source
    from backend_api.services import IntegrationService
    with factory() as db:
        ctx = context(db, keys)
        integration_id = keys.integrations['YANDEX_DIRECT']
        async def refreshed(*args):
            assert_free(engine, db)
            with factory.begin() as writer:
                row = writer.get(models.Integration, integration_id)
                if change == 'token': row.access_token = security.encrypt_token('manual-token')
                elif change == 'account': row.account_id = 'other-cabinet'
                elif change == 'user': writer.get(models.User, keys.user).is_active = False
                elif change == 'project':
                    other = models.User(email='other@example.test', password_hash='synthetic')
                    writer.add(other); writer.flush()
                    writer.get(models.Client, keys.project).owner_id = other.id
                elif change == 'delete': writer.delete(row)
            return {'access_token': 'late-token', 'refresh_token': 'late-refresh'}
        monkeypatch.setattr(IntegrationService, 'refresh_yandex_token', refreshed)
        with pytest.raises(AccessChanged):
            await ctx.access.refresh()
        assert_free(engine, db)
    with factory() as db:
        row = db.get(models.Integration, integration_id)
        if row:
            assert security.decrypt_token(row.access_token) == ('manual-token' if change == 'token' else 'old-token')


@pytest.mark.asyncio
async def test_project_selection_persists_and_revocation_blocks_next_tool(source, monkeypatch):
    factory, engine, keys = source
    with factory() as db:
        ctx = context(db, keys)
        result = json.loads(await tools.execute_tool('use_project', {'query': 'Synthetic project'}, ctx))
        assert result['selected_project']['id'] == str(keys.project)
        assert_free(engine, db)
        with factory.begin() as writer:
            assert writer.get(models.AiConversation, keys.conv).client_id == keys.project
            writer.get(models.User, keys.user).is_active = False
        async def forbidden(*args):
            pytest.fail('Revoked actor must not reach provider')
        monkeypatch.setattr(token_provider.VkAccess, 'api', forbidden)
        assert 'error' in json.loads(await tools.execute_tool('vk_get_balance', {}, ctx))
        assert_free(engine, db)


@pytest.mark.asyncio
@pytest.mark.parametrize('failure', ['cancel', 'provider'])
async def test_llm_cancellation_and_failure_leave_pool_free(source, monkeypatch, failure):
    factory, engine, keys = source
    closed = asyncio.Event()
    with factory() as db:
        async def complete(**kwargs):
            try:
                assert_free(engine, db)
                yield {'type': 'text', 'delta': 'Start'}
                if failure == 'provider':
                    raise agent.llm.LLMError('synthetic secret must not escape')
                await asyncio.Event().wait()
            finally:
                closed.set()
        monkeypatch.setattr(agent.llm, 'stream_completion', complete)
        stream = agent.run(db, db.get(models.AiConversation, keys.conv), 'Question',
                          SimpleNamespace(id='synthetic'), None, db.get(models.User, keys.user))
        async with aclosing(stream):
            assert (await anext(stream))['type'] == 'text'
            assert_free(engine, db)
            if failure == 'provider':
                remaining = [event async for event in stream]
                assert remaining[-1]['type'] == 'error'
                assert 'secret' not in str(remaining)
        # Async-generator provider must be explicitly closed, not left to GC.
        await asyncio.sleep(0)
        assert closed.is_set()
        assert_free(engine, db)


@pytest.mark.asyncio
@pytest.mark.parametrize('cancel', [False, True])
async def test_chat_route_releases_sql_before_sse_and_settles_once(source, monkeypatch, cancel):
    from ai.assistant import router, runs
    factory, engine, keys = source
    runs.metadata.create_all(engine)
    monkeypatch.setattr(runs.Subscriptions, 'ensure_can_use_ai', lambda *args: None)
    monkeypatch.setattr(runs.Subscriptions, 'is_admin_bypass', lambda *args: False)
    closed = asyncio.Event()
    calls = []
    with factory() as db:
        async def complete(**kwargs):
            try:
                assert_free(engine, db)
                runs.before_provider()
                calls.append(1)
                assert_free(engine, db)
                yield {'type': 'text', 'delta': 'Answer'}
                if cancel:
                    await asyncio.Event().wait()
                runs.record_usage({'usage': {'completion_tokens': 1}}, provider='synthetic', model='synthetic')
                assert_free(engine, db)
                yield {'type': 'message', 'message': {'content': 'Answer'}}
            finally:
                closed.set()
        monkeypatch.setattr(agent.llm, 'stream_completion', complete)
        request = router.ChatRequest(request_id=uuid4(), message='Question', conversation_id=str(keys.conv))
        response = await router.chat(request, db, db.get(models.User, keys.user))
        assert_free(engine, db)  # Even before the first byte is consumed.
        received = []
        async with aclosing(response.body_iterator) as body:
            async for chunk in body:
                received.append(chunk)
                if cancel and '"type": "text"' in chunk:
                    break
        assert closed.is_set()
        assert_free(engine, db)
        if not cancel:
            replay = await router.chat(request, db, db.get(models.User, keys.user))
            assert b'"replayed": true' in replay.body
            assert_free(engine, db)
    with factory() as db:
        row = db.execute(sa.select(runs.runs)).mappings().one()
        assert row['state'] == ('interrupted' if cancel else 'succeeded')
        assert row['provider_calls'] == 1
        assert db.get(models.User, keys.user).ai_requests_used == 1
        assert bool(row['message_id']) == (not cancel)
    assert calls == [1]


@pytest.mark.asyncio
async def test_tool_reloads_changed_cabinet_between_calls(source, monkeypatch):
    factory, engine, keys = source
    observed = []
    with factory() as db:
        ctx = context(db, keys)
        def build(integration):
            observed.append(integration.account_id)
            async def balance():
                assert_free(engine, db)
                return {'balance': 1}
            return SimpleNamespace(get_balance=balance)
        monkeypatch.setattr('automation.avito_integration_helpers.build_avito_api_from_integration', build)
        assert 'error' not in json.loads(await tools.execute_tool('avito_get_balance', {}, ctx))
        with factory.begin() as writer:
            writer.get(models.Integration, keys.integrations['AVITO_ADS']).account_id = 'new-cabinet'
        assert 'error' not in json.loads(await tools.execute_tool('avito_get_balance', {}, ctx))
        assert_free(engine, db)
    assert observed == ['cabinet', 'new-cabinet']


@pytest.mark.asyncio
async def test_preparation_error_releases_session_before_stream_error(source, monkeypatch):
    factory, engine, keys = source
    def broken_history(*args):
        raise RuntimeError('synthetic preparation failure')
    monkeypatch.setattr(agent, '_history_to_messages', broken_history)
    with factory() as db:
        with pytest.raises(RuntimeError, match='preparation failure'):
            async for _ in agent.run(db, db.get(models.AiConversation, keys.conv), 'Question',
                    SimpleNamespace(id='synthetic'), None, db.get(models.User, keys.user)):
                pytest.fail('Preparation failed before any event')
        assert_free(engine, db)


@pytest.mark.asyncio
async def test_cancel_refresh_leaves_credentials_and_pool_untouched(source, monkeypatch):
    from backend_api.services import IntegrationService
    factory, engine, keys = source
    started = asyncio.Event()
    with factory() as db:
        ctx = context(db, keys)
        async def refresh(*args):
            assert_free(engine, db)
            started.set()
            await asyncio.Event().wait()
        monkeypatch.setattr(IntegrationService, 'refresh_vk_token', refresh)
        task = asyncio.create_task(tools.execute_tool('vk_get_balance', {}, ctx))
        await asyncio.wait_for(started.wait(), 2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert_free(engine, db)
    with factory() as db:
        assert security.decrypt_token(db.get(models.Integration, keys.integrations['VK_ADS']).access_token) == 'old-token'


@pytest.mark.asyncio
@pytest.mark.parametrize('method', ['direct', 'metrika', 'report'])
async def test_real_yandex_wire_401_refresh_and_retry_leave_sql_free(source, monkeypatch, method):
    from backend_api.services import IntegrationService
    from ai.assistant import yandex_client
    factory, engine, keys = source
    headers = []
    with factory() as db:
        ctx = context(db, keys)
        async def refresh(*args):
            assert_free(engine, db)
            return {'access_token': 'new-token', 'expires_in': 3600}
        monkeypatch.setattr(IntegrationService, 'refresh_yandex_token', refresh)
        class Wire:
            async def request(self, *args, **kwargs):
                assert_free(engine, db)
                headers.append(kwargs['headers']['Authorization'])
                if len(headers) == 1:
                    return httpx.Response(401, json={})
                if method == 'report':
                    return httpx.Response(200, text='CampaignId\tCost\n1\t10\n')
                return httpx.Response(200, json={'result': {'Campaigns': [{'Id': 1}]}, 'goals': []})
            post = request
            get = request
        @asynccontextmanager
        async def provider(*args, **kwargs):
            yield Wire()
        monkeypatch.setattr(yandex_client, 'provider_client', provider)
        if method == 'direct':
            assert (await ctx.client.direct_call('campaigns', 'get', {}))['Campaigns']
        elif method == 'metrika':
            assert 'goals' in await ctx.client.metrika_get('/management/v1/counter/123/goals')
        else:
            assert await ctx.client.direct_report({}) == [{'CampaignId': '1', 'Cost': '10'}]
        assert [header.split()[-1] for header in headers] == ['old-token', 'new-token']
        assert_free(engine, db)
