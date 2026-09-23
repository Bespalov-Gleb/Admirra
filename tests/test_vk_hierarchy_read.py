"""Synthetic VK transport, real single-slot PostgreSQL; no provider mutations."""
import asyncio
from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import HTTPException
import httpx
import pytest

from automation import vk_hierarchy_contract as transport
from automation.vk_ads import VKAdsAPI
from backend_api import vk_hierarchy_read as work, hierarchy_read as shared, stats
from core import models, security
from tests.assistant_pg import pg
from tests.test_attribution_read import source, assert_free, DAY, P


@pytest.fixture
def vk_source(source):
    factory, engine, keys = source
    with factory.begin() as db:
        integration = models.Integration(client_id=keys.project, platform=P.VK_ADS,
            account_id='1234', access_token=security.encrypt_token('vk-synthetic'))
        db.add(integration); db.flush()
        campaign = models.Campaign(integration_id=integration.id, external_id='111', name='VK project')
        db.add(campaign); db.flush()
        db.add(models.VKStats(client_id=keys.project, campaign_id=campaign.id, date=DAY,
            impressions=1000, clicks=100, cost=3400, conversions=34))
        keys.vk_integration, keys.vk_campaign = integration.id, campaign.id
    return factory, engine, keys


def provider(monkeypatch, engine, db, *, fail=None, kind='personal'):
    calls = []
    def check(stage):
        assert_free(engine, db)
        calls.append(stage)
        if fail == stage:
            raise TimeoutError('synthetic timeout')
    async def detect(api):
        check('detect')
        return kind
    async def catalog(api, parents, *, banners=False):
        check('banners_catalog' if banners else 'groups_catalog')
        assert api.account_id == ('1234' if kind != 'personal' else None)
        return ([dict(id=100, ad_group_id=10, name='Banner'), dict(id=101, ad_group_id=10)] if banners
                else [dict(id=10, ad_plan_id=111, name='Group'), dict(id=11, ad_plan_id=111)])
    async def statistics(api, level, ids, start, end):
        check(level)
        return [dict(date=str(DAY), object_id='100' if level == 'banners' else '10',
                     cost=3400, clicks=100, impressions=1000, conversions=34)]
    monkeypatch.setattr(work.VKAdsAPI, 'detect_token_kind', detect)
    monkeypatch.setattr(work, 'catalog', catalog)
    monkeypatch.setattr(work, 'statistics', statistics)
    return calls


async def run(db, keys, ads=True, start=DAY, end=DAY):
    await work.ensure_vk(db, keys.vk_campaign, keys.project, start, end,
                         include_ads=ads, user_id=keys.user)


def prepare(db, keys):
    return shared.prepare(db, keys.vk_campaign, keys.project, DAY, DAY, True, keys.user, platform=P.VK_ADS)


@pytest.mark.asyncio
@pytest.mark.parametrize('kind', ['personal', 'agency', 'manager'])
async def test_detached_atomic_hierarchy_and_cache(vk_source, monkeypatch, kind):
    factory, engine, keys = vk_source
    with factory() as db:
        calls = provider(monkeypatch, engine, db, kind=kind)
        await run(db, keys)
        assert_free(engine, db)
        assert calls == ['detect', 'groups_catalog', 'ad_groups', 'banners_catalog', 'banners']
        assert db.query(models.VKGroups).filter_by(group_id='10').one().conversions == 34
        assert db.query(models.VKGroups).filter_by(group_id='11').one().cost == 0
        assert db.query(models.VKBanners).filter_by(banner_id='100').one().cost == 3400
        assert db.query(models.VKBanners).filter_by(banner_id='101').one().conversions == 0
        await run(db, keys)
        assert len(calls) == 5
        assert db.query(models.VKGroups).count() == 2
        assert db.query(models.VKBanners).count() == 2


@pytest.mark.asyncio
@pytest.mark.parametrize('fail', ['detect', 'groups_catalog', 'ad_groups', 'banners_catalog', 'banners'])
async def test_failure_never_saves_partial_or_zero(vk_source, monkeypatch, fail):
    factory, engine, keys = vk_source
    with factory() as db:
        provider(monkeypatch, engine, db, fail=fail)
        with pytest.raises(HTTPException) as caught:
            await run(db, keys)
        assert caught.value.status_code == 502
        assert_free(engine, db)
        assert db.query(models.VKGroups).count() == db.query(models.VKBanners).count() == 0
        assert db.query(models.VKStats).one().conversions == 34


@pytest.mark.asyncio
async def test_unknown_token_scope_fails_without_requesting_catalog(vk_source, monkeypatch):
    factory, engine, keys = vk_source
    with factory() as db:
        calls = provider(monkeypatch, engine, db, kind='unknown')
        with pytest.raises(HTTPException) as caught:
            await run(db, keys)
        assert caught.value.status_code == 502
        assert calls == ['detect']
        assert_free(engine, db)


@pytest.mark.asyncio
@pytest.mark.parametrize('change', ['sync', 'settings', 'owner', 'delete', 'rename', 'disable'])
async def test_late_apply_rejected(vk_source, monkeypatch, change):
    factory, engine, keys = vk_source
    with factory() as db:
        provider(monkeypatch, engine, db)
        plan = prepare(db, keys)
        operations = await work.collect(plan)
        with factory.begin() as other:
            if change == 'sync':
                other.query(models.VKStats).one().cost = 9876
            elif change == 'settings':
                other.get(models.Integration, keys.vk_integration).account_id = '999'
            elif change == 'owner':
                other.get(models.Client, keys.project).owner_id = keys.other
            elif change == 'delete':
                other.delete(other.get(models.Campaign, keys.vk_campaign))
            elif change == 'disable':
                other.get(models.User, keys.user).is_active = False
            else:
                other.get(models.Campaign, keys.vk_campaign).name = 'New name'
        with pytest.raises(HTTPException) as caught:
            shared.apply(db, plan, operations)
        assert caught.value.status_code == (403 if change in ('owner', 'disable') else 409)
        assert_free(engine, db)
        assert db.query(models.VKGroups).count() == db.query(models.VKBanners).count() == 0
        if change == 'sync':
            assert db.query(models.VKStats).one().cost == 9876


@pytest.mark.asyncio
async def test_concurrent_late_result_and_cancellation(vk_source, monkeypatch):
    factory, engine, keys = vk_source
    with factory() as db:
        provider(monkeypatch, engine, db)
        one, two = prepare(db, keys), prepare(db, keys)
        operations = await work.collect(one)
        shared.apply(db, one, operations)
        with pytest.raises(HTTPException) as caught:
            shared.apply(db, two, operations)
        assert caught.value.status_code == 409
        with factory.begin() as other:
            other.query(models.VKGroups).delete()
            other.query(models.VKBanners).delete()
        async def cancel(*args, **kwargs):
            assert_free(engine, db)
            raise asyncio.CancelledError()
        monkeypatch.setattr(work, 'statistics', cancel)
        with pytest.raises(asyncio.CancelledError):
            await run(db, keys)
        assert_free(engine, db)
        assert db.query(models.VKGroups).count() == 0


@pytest.mark.asyncio
@pytest.mark.parametrize('level,node', [('campaign', None), ('group', '10')])
async def test_real_children_route(vk_source, monkeypatch, level, node):
    factory, engine, keys = vk_source
    with factory() as db:
        provider(monkeypatch, engine, db)
        rows = await stats.get_campaign_children(campaign_id=str(keys.vk_campaign),
            start_date=str(DAY), end_date=str(DAY), client_id=str(keys.project), level=level,
            node_id=node, sort_by='leads', sort_dir='desc', current_user=db.get(models.User, keys.user), db=db)
        assert sum(row['conversions'] for row in rows) == 34
        assert sum(row['cost'] for row in rows) == 3400


@pytest.mark.asyncio
async def test_existing_groups_not_erased_while_fetching_banners(vk_source, monkeypatch):
    factory, engine, keys = vk_source
    with factory() as db:
        db.add(models.VKGroups(client_id=keys.project, campaign_id=keys.vk_campaign, date=DAY,
            group_id='10', group_name='Old', cost=777, clicks=7, impressions=70, conversions=2))
        db.commit()
        calls = provider(monkeypatch, engine, db)
        await run(db, keys)
        assert 'ad_groups' not in calls
        assert db.query(models.VKGroups).one().cost == 777
        assert db.query(models.VKBanners).filter_by(banner_id='100').one().conversions == 34


@pytest.mark.asyncio
async def test_pending_edits_invalid_dates_and_duplicates(vk_source, monkeypatch):
    factory, engine, keys = vk_source
    with factory() as db:
        provider(monkeypatch, engine, db)
        campaign = db.get(models.Campaign, keys.vk_campaign)
        campaign.name = 'Unsaved'
        with pytest.raises(RuntimeError):
            await run(db, keys)
        assert campaign.name == 'Unsaved' and db.dirty
        db.rollback()
        with pytest.raises(HTTPException) as caught:
            await run(db, keys, start=DAY + timedelta(days=1))
        assert caught.value.status_code == 422
        for _ in range(2):
            db.add(models.VKGroups(client_id=keys.project, campaign_id=keys.vk_campaign,
                                  date=DAY, group_id='10', cost=777))
        db.commit()
        with pytest.raises(HTTPException) as caught:
            await run(db, keys)
        assert caught.value.status_code == 409
        assert db.query(models.VKBanners).count() == 0
        assert db.query(models.VKGroups).count() == 2


def http_provider(monkeypatch, handler):
    @asynccontextmanager
    async def client(*args):
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as value:
            yield value
    async def throttle(*args):
        pass
    monkeypatch.setattr(transport, 'provider_client', client)
    monkeypatch.setattr(VKAdsAPI, '_throttle', throttle)


@pytest.mark.asyncio
async def test_foreign_legacy_row_never_blocks_or_gets_updated(vk_source, monkeypatch):
    factory, engine, keys = vk_source
    with factory() as db:
        foreign = models.Client(owner_id=keys.other, name='Foreign')
        db.add(foreign); db.flush()
        foreign_id = foreign.id
        db.add(models.VKGroups(client_id=foreign_id, campaign_id=keys.vk_campaign,
                              date=DAY, group_id='10', cost=999))
        db.commit()
        provider(monkeypatch, engine, db)
        await run(db, keys)
        assert db.query(models.VKGroups).filter_by(client_id=foreign_id).one().cost == 999
        assert db.query(models.VKGroups).filter_by(client_id=keys.project, group_id='10').one().cost == 3400


@pytest.mark.asyncio
@pytest.mark.parametrize('malformed', ['group_parent', 'banner_parent', 'metric', 'date', 'duplicate'])
async def test_collector_rejects_bad_normalized_data(vk_source, monkeypatch, malformed):
    factory, engine, keys = vk_source
    with factory() as db:
        provider(monkeypatch, engine, db)
        original_catalog, original_statistics = work.catalog, work.statistics
        async def catalog(*args, **kwargs):
            rows = await original_catalog(*args, **kwargs)
            if malformed == 'group_parent' and not kwargs.get('banners'):
                rows[0]['ad_plan_id'] = 999
            if malformed == 'banner_parent' and kwargs.get('banners'):
                rows[0]['ad_group_id'] = 999
            return rows
        async def statistics(*args):
            rows = await original_statistics(*args)
            if malformed == 'metric':
                rows[0]['cost'] = -1
            elif malformed == 'date':
                rows[0]['date'] = str(DAY - timedelta(days=1))
            elif malformed == 'duplicate':
                rows *= 2
            return rows
        monkeypatch.setattr(work, 'catalog', catalog)
        monkeypatch.setattr(work, 'statistics', statistics)
        with pytest.raises(HTTPException) as caught:
            await run(db, keys)
        assert caught.value.status_code == 502
        assert_free(engine, db)
        assert db.query(models.VKGroups).count() == db.query(models.VKBanners).count() == 0


@pytest.mark.asyncio
@pytest.mark.parametrize('failure', [None, 'http', 'missing', 'foreign', 'repeat', 'truncated', 'count', 'budget'])
async def test_catalog_pagination_scope_and_fail_closed(monkeypatch, failure):
    calls = []
    def handler(request):
        offset = int(request.url.params['offset'])
        calls.append(offset)
        assert request.url.params['_ad_plan_id__in'] == '111'
        assert request.url.params['client_id'] == '1234'
        if failure == 'http' and offset:
            return httpx.Response(500)
        if failure == 'missing':
            return httpx.Response(200, json={})
        row = dict(id=10 if not offset or failure == 'repeat' else 11,
                   ad_plan_id=999 if failure == 'foreign' else 111)
        count = (3 if offset and failure == 'count' else 2)
        page = [] if offset and failure == 'truncated' else [row]
        return httpx.Response(200, json=dict(items=page, count=count))
    http_provider(monkeypatch, handler)
    if failure == 'budget':
        monkeypatch.setattr(transport, 'MAX_PAGES', 1)
    api = VKAdsAPI('synthetic', '1234', send_client_id=True)
    if failure:
        with pytest.raises((httpx.HTTPError, transport.IncompleteAdsSnapshot)):
            await transport.catalog(api, ['111'])
    else:
        assert [row['id'] for row in await transport.catalog(api, ['111'])] == [10, 11]
        assert calls == [0, 1]


@pytest.mark.asyncio
async def test_banner_catalog_chunks_and_personal_scope(monkeypatch):
    calls = []
    def handler(request):
        assert request.url.path.endswith('/banners.json')
        assert 'client_id' not in request.url.params
        parents = request.url.params['_ad_group_id__in'].split(',')
        calls.append(len(parents))
        rows = [dict(id=int(key) + 1000, ad_group_id=int(key)) for key in parents]
        return httpx.Response(200, json=dict(items=rows, count=len(rows)))
    http_provider(monkeypatch, handler)
    rows = await transport.catalog(VKAdsAPI('synthetic', '1234', send_client_id=False),
                                   list(range(1, 206)), banners=True)
    assert len(rows) == 205 and calls == [200, 5]


@pytest.mark.asyncio
@pytest.mark.parametrize('failure', [None, 'http', 'missing', 'foreign', 'duplicate', 'date', 'metric'])
async def test_statistics_chunks_validate_every_response(monkeypatch, failure):
    calls = []
    def handler(request):
        assert 'client_id' not in request.url.params
        ids = request.url.params['id'].split(',')
        calls.append((len(ids), request.url.params['date_from']))
        if failure == 'http' and len(calls) == 2:
            return httpx.Response(429)
        if failure == 'missing':
            return httpx.Response(200, json={})
        rows = [dict(date='2020-01-01' if failure == 'date' else request.url.params['date_from'],
                     base=dict(shows=100, clicks=10, spent='NaN' if failure == 'metric' else '3400',
                               vk=dict(goals=34)))]
        if failure == 'duplicate':
            rows *= 2
        return httpx.Response(200, json=dict(items=[dict(id='999' if failure == 'foreign' else ids[0], rows=rows)]))
    http_provider(monkeypatch, handler)
    api = VKAdsAPI('synthetic', '1234', send_client_id=True)
    if failure:
        with pytest.raises((httpx.HTTPError, transport.IncompleteAdsSnapshot)):
            await transport.statistics(api, 'banners', list(range(1, 206)), '2026-01-01', '2026-04-02')
    else:
        rows = await transport.statistics(api, 'banners', list(range(1, 206)), '2026-01-01', '2026-04-02')
        assert len(rows) == 4 and sum(row['conversions'] for row in rows) == 136
        assert [call[0] for call in calls] == [200, 5, 200, 5]
