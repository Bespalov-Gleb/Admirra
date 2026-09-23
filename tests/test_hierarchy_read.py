"""Direct drill-down: no SQL over IO and no late/partial apply."""
import asyncio
from contextlib import asynccontextmanager

from fastapi import HTTPException
import httpx
import pytest

from backend_api import hierarchy_read as work, stats
from core import models
from tests.assistant_pg import pg
from tests.test_attribution_read import source, assert_free, DAY, P


def fake_provider(monkeypatch, engine, db, *, fail=None):
    calls = []
    async def report(api, start, end, level, **kwargs):
        assert_free(engine, db)
        calls.append(level)
        if fail == level:
            raise TimeoutError('synthetic failure')
        row = dict(date=str(DAY), campaign_id='111', campaign_name='Газобетон', impressions=1000,
                   clicks=100, cost=3400, conversions=34)
        if level in ('group', 'ad'):
            row.update(group_id='10', name='Group')
        if level == 'ad':
            row.update(ad_id='100')
        return [row]
    async def catalog(api, campaign_id, ads=False):
        assert_free(engine, db)
        calls.append('ads_catalog' if ads else 'groups_catalog')
        if fail == 'catalog':
            raise ValueError('synthetic malformed catalog')
        return ([dict(Id=100, CampaignId=111, AdGroupId=10), dict(Id=101, CampaignId=111, AdGroupId=10)] if ads
                else [dict(Id=10, CampaignId=111, Name='Group'), dict(Id=11, CampaignId=111, Name='Zero')])
    monkeypatch.setattr(work.YandexDirectAPI, 'get_report', report)
    monkeypatch.setattr(work, 'catalog', catalog)
    return calls


async def run(db, keys, ads=True):
    await work.ensure_yandex(db, keys.campaigns[(P.YANDEX_DIRECT, 'Газобетон')], keys.project,
                            DAY, DAY, include_ads=ads, user_id=keys.user)


@pytest.mark.asyncio
async def test_all_provider_stages_free_pool_and_catalog_never_erases_metrics(source, monkeypatch):
    factory, engine, keys = source
    with factory() as db:
        cid = keys.campaigns[(P.YANDEX_DIRECT, 'Газобетон')]
        # No row in the report for group 11; its catalog zero must not erase 777.
        db.add(models.YandexGroups(client_id=keys.project, campaign_id=cid, date=DAY,
            group_id='11', campaign_name='Old name', cost=777, clicks=7, impressions=70, conversions=2))
        db.commit()
        calls = fake_provider(monkeypatch, engine, db)
        await run(db, keys)
        assert_free(engine, db)
        assert calls == ['campaign', 'group', 'groups_catalog', 'ad', 'ads_catalog']
        assert db.query(models.YandexGroups).filter_by(group_id='11').one().cost == 777
        assert db.query(models.YandexGroups).filter_by(group_id='10').one().cost == 3400
        assert db.query(models.YandexAds).filter_by(ad_id='100').one().conversions == 34
        assert db.query(models.YandexAds).filter_by(ad_id='101').one().cost == 0
        # An existing ad slice keeps the old no-refetch behaviour; no duplicates.
        calls.clear()
        await run(db, keys)
        assert calls == ['campaign', 'group', 'groups_catalog']
        assert db.query(models.YandexGroups).count() == 2
        assert db.query(models.YandexAds).count() == 2


@pytest.mark.asyncio
@pytest.mark.parametrize('stage', ['campaign', 'group', 'ad', 'catalog'])
async def test_partial_failure_writes_nothing(source, monkeypatch, stage):
    factory, engine, keys = source
    with factory() as db:
        fake_provider(monkeypatch, engine, db, fail=stage)
        with pytest.raises(HTTPException) as exc:
            await run(db, keys)
        assert exc.value.status_code == 502
        assert_free(engine, db)
        assert db.query(models.YandexGroups).count() == 0
        assert db.query(models.YandexAds).count() == 0
        assert db.query(models.YandexStats).filter_by(campaign_id=keys.campaigns[(P.YANDEX_DIRECT, 'Газобетон')]).one().conversions == 65


@pytest.mark.asyncio
@pytest.mark.parametrize('change', ['sync', 'settings', 'owner', 'delete', 'rename'])
async def test_late_result_cannot_overwrite_sync_or_new_settings(source, monkeypatch, change):
    factory, engine, keys = source
    with factory() as db:
        fake_provider(monkeypatch, engine, db)
        original = work.collect
        async def collect(plan):
            operations = await original(plan)
            assert_free(engine, db)
            with factory.begin() as other:
                if change == 'sync':
                    other.query(models.YandexStats).filter_by(campaign_id=plan.campaign.id).update({'cost': 9876})
                elif change == 'settings':
                    other.get(models.Integration, plan.integration.id).selected_counters = '["999"]'
                elif change == 'owner':
                    other.get(models.Client, keys.project).owner_id = keys.other
                elif change == 'delete':
                    other.delete(other.get(models.Campaign, plan.campaign.id))
                else:
                    other.get(models.Campaign, plan.campaign.id).name = 'Renamed'
            return operations
        monkeypatch.setattr(work, 'collect', collect)
        with pytest.raises(HTTPException) as exc:
            await run(db, keys)
        assert exc.value.status_code == (403 if change == 'owner' else 409)
        assert_free(engine, db)
        assert db.query(models.YandexGroups).count() == 0
        if change == 'sync':
            assert db.query(models.YandexStats).filter_by(campaign_id=keys.campaigns[(P.YANDEX_DIRECT, 'Газобетон')]).one().cost == 9876


@pytest.mark.asyncio
async def test_two_inflight_fetches_only_one_apply_and_cancel_is_clean(source, monkeypatch):
    factory, engine, keys = source
    with factory() as db:
        fake_provider(monkeypatch, engine, db)
        cid = keys.campaigns[(P.YANDEX_DIRECT, 'Газобетон')]
        a = work.prepare(db, cid, keys.project, DAY, DAY, True, keys.user)
        b = work.prepare(db, cid, keys.project, DAY, DAY, True, keys.user)
        first, second = await asyncio.gather(work.collect(a), work.collect(b))
        work.apply(db, a, first)
        with pytest.raises(HTTPException) as exc:
            work.apply(db, b, second)
        assert exc.value.status_code == 409
        assert_free(engine, db)
        assert db.query(models.YandexGroups).count() == 2
        async def cancelled(plan):
            assert_free(engine, db)
            raise asyncio.CancelledError()
        monkeypatch.setattr(work, 'collect', cancelled)
        with pytest.raises(asyncio.CancelledError):
            await run(db, keys)
        assert_free(engine, db)


@pytest.mark.asyncio
@pytest.mark.parametrize('level', ['campaign', 'group'])
async def test_real_children_route_uses_detached_metrika_too(source, monkeypatch, level):
    factory, engine, keys = source
    with factory() as db:
        fake_provider(monkeypatch, engine, db)
        async def drill(integration, campaign, level, *dates):
            assert_free(engine, db)
            return ({'10': 34} if level == 'campaign' else {'100': 34}), True
        async def total(*args):
            assert_free(engine, db)
            return {'газобетон': 34}, True
        monkeypatch.setattr(stats, '_metrika_drill_conv_map', drill)
        monkeypatch.setattr(stats, '_metrika_campaign_conv_map', total)
        result = await stats.get_campaign_children(str(keys.campaigns[(P.YANDEX_DIRECT, 'Газобетон')]),
            start_date=str(DAY), end_date=str(DAY), client_id=str(keys.project), level=level,
            node_id='10' if level == 'group' else None, sort_by='leads', sort_dir='desc',
            current_user=db.get(models.User, keys.user), db=db)
        assert sum(row['conversions'] for row in result) == 34
        assert sum(row['cost'] for row in result) == 3400


@pytest.mark.asyncio
@pytest.mark.parametrize('failure', [None, 'http', 'partial', 'foreign', 'repeat'])
async def test_strict_catalog_pagination(monkeypatch, failure):
    api = work.YandexDirectAPI('synthetic')
    requests = []
    def handle(request):
        import json
        body = json.loads(request.content)
        offset = body['params']['Page']['Offset']
        requests.append(offset)
        if failure == 'http':
            return httpx.Response(503)
        if failure == 'partial' and offset:
            return httpx.Response(200, json={'result': {}})
        row = {'Id': 10 if not offset or failure == 'repeat' else 11,
               'CampaignId': 999 if failure == 'foreign' else 111, 'Name': 'Group'}
        result = {'AdGroups': [row]}
        if not offset:
            result['LimitedBy'] = 1
        return httpx.Response(200, json={'result': result})
    @asynccontextmanager
    async def client(*args):
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as value:
            yield value
    class Limiter:
        async def acquire(self):
            pass
    monkeypatch.setattr(work, 'provider_client', client)
    monkeypatch.setattr(work, 'get_api_limiter', lambda *a: Limiter())
    if failure:
        with pytest.raises((httpx.HTTPError, work.IncompleteAdsSnapshot)):
            await work.catalog(api, '111')
    else:
        assert [row['Id'] for row in await work.catalog(api, '111')] == [10, 11]
        assert requests == [0, 1]


def test_strict_ad_tsv_rejects_partial_rows():
    from automation.ads_sync_contract import direct_tsv, IncompleteAdsSnapshot
    text = 'Date\tCampaignId\tCampaignName\tAdGroupId\tAdId\tImpressions\tClicks\tCost\tConversions\n'
    text += '2026-09-10\t111\tCampaign\t10\t100\t1000\t100\t3400000000\t34\n'
    assert direct_tsv(text, 'ad')[0]['ad_id'] == '100'
    with pytest.raises(IncompleteAdsSnapshot):
        direct_tsv(text + '2026-09-10\t111\n', 'ad')


@pytest.mark.asyncio
async def test_existing_duplicates_and_pending_writes_are_not_silently_changed(source, monkeypatch):
    factory, engine, keys = source
    with factory() as db:
        project = db.get(models.Client, keys.project)
        project.name = 'Unsaved edit'
        with pytest.raises(RuntimeError, match='pending changes'):
            await run(db, keys)
        assert project in db.dirty and project.name == 'Unsaved edit'
        db.rollback()
        for cost in (1, 2):
            db.add(models.YandexGroups(client_id=keys.project,
                campaign_id=keys.campaigns[(P.YANDEX_DIRECT, 'Газобетон')], date=DAY, group_id='10', cost=cost))
        db.commit()
        fake_provider(monkeypatch, engine, db)
        with pytest.raises(HTTPException) as exc:
            await run(db, keys)
        assert exc.value.status_code == 409
        assert_free(engine, db)
        assert sorted(float(row.cost) for row in db.query(models.YandexGroups)) == [1, 2]


@pytest.mark.asyncio
async def test_mismatched_legacy_client_row_is_never_updated(source, monkeypatch):
    factory, engine, keys = source
    with factory() as db:
        foreign = models.Client(owner_id=keys.other, name='Foreign')
        db.add(foreign); db.flush()
        foreign_id = foreign.id
        db.add(models.YandexGroups(client_id=foreign_id,
            campaign_id=keys.campaigns[(P.YANDEX_DIRECT, 'Газобетон')], date=DAY, group_id='10', cost=999))
        db.commit()
        fake_provider(monkeypatch, engine, db)
        await run(db, keys)
        assert db.query(models.YandexGroups).filter_by(client_id=foreign_id).one().cost == 999
        assert db.query(models.YandexGroups).filter_by(client_id=keys.project, group_id='10').one().cost == 3400
