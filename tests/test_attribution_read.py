"""Live attribution: real PostgreSQL/pool, synthetic Metrika, no outbound IO."""
import asyncio
from datetime import date, timedelta
from types import SimpleNamespace

from fastapi import HTTPException
import pytest
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from backend_api import stats
from core import models, security
from tests.assistant_pg import pg


DAY = date(2026, 9, 10)
P = models.IntegrationPlatform


@pytest.fixture
def source(pg):
    _, admin = pg
    models.Base.metadata.create_all(admin)
    with admin.connect() as conn:
        schema = conn.scalar(sa.text('SELECT current_schema()'))
    engine = sa.create_engine(admin.url, pool_size=1, max_overflow=0, pool_timeout=.3,
        connect_args={'options': f'-csearch_path={schema} -cstatement_timeout=5000'})
    factory = sessionmaker(bind=engine)
    with factory.begin() as db:
        user = models.User(email='attribution@example.test', password_hash='synthetic')
        other = models.User(email='foreign@example.test', password_hash='synthetic')
        db.add_all([user, other]); db.flush()
        project = models.Client(owner_id=user.id, name='Synthetic attribution')
        db.add(project); db.flush()
        integrations = {}
        campaigns = {}
        for platform in (P.YANDEX_DIRECT, P.AVITO_ADS):
            integration = models.Integration(client_id=project.id, platform=platform,
                account_id='cabinet', access_token=security.encrypt_token('direct-token'),
                metrika_access_token=security.encrypt_token('avito-metrika-token'),
                metrika_account_id='avito-login', selected_counters='["123"]', selected_goals='["456"]')
            db.add(integration); db.flush()
            integrations[platform] = integration.id
            for name, external, cost, native in [('Газобетон', '111', 3400, 65), ('Другое', '222', 3100, 0)]:
                campaign = models.Campaign(integration_id=integration.id, name=name, external_id=external)
                db.add(campaign); db.flush()
                campaigns[(platform, name)] = campaign.id
                cls = models.YandexStats if platform == P.YANDEX_DIRECT else models.AvitoStats
                db.add(cls(client_id=project.id, campaign_id=campaign.id, date=DAY,
                           cost=cost, clicks=100, impressions=1000, conversions=native))
            db.add(models.MetrikaGoals(client_id=project.id, integration_id=integration.id,
                goal_id='456', goal_name='Заявка', date=DAY, conversion_count=65))
        direction = models.ProjectDirection(client_id=project.id, name='Газобетон')
        db.add(direction); db.flush()
        db.add(models.ProjectDirectionMask(direction_id=direction.id, mask='Газобетон', position=0))
        keys = SimpleNamespace(user=user.id, other=other.id, project=project.id,
                               integrations=integrations, campaigns=campaigns, direction=direction.id)
    try:
        yield factory, engine, keys
    finally:
        assert engine.pool.checkedout() == 0
        engine.dispose()


def assert_free(engine, db):
    assert not db.in_transaction()
    assert engine.pool.checkedout() == 0
    with engine.connect() as conn:
        assert conn.scalar(sa.text('SELECT 1')) == 1


def provider(monkeypatch, engine, db, calls):
    from automation.yandex_metrica import YandexMetricaAPI
    stats._metrika_counter_goals_cache.clear()
    async def goals(api, counter):
        assert_free(engine, db)
        calls.append(('goals', api.client_login))
        await asyncio.sleep(0)
        return [{'id': 456}]
    async def conversions(api, **kwargs):
        assert_free(engine, db)
        calls.append(('conversions', kwargs))
        await asyncio.sleep(0)
        if not kwargs['date_from'] <= str(DAY) <= kwargs['date_to']:
            return []
        dim = kwargs['dimension']
        if dim.startswith('ym:s:UTM'):
            assert api.headers['Authorization'] == 'OAuth avito-metrika-token'
            assert kwargs['filters'] == "ym:s:UTMSource=='avito-ads'"
            pairs = [('111', 34), ('222', 31)]
        else:
            assert api.headers['Authorization'] == 'OAuth direct-token'
            pairs = [('Газобетон', 34), ('Другое', 31)]
        return [{'dimensions': ([{'name': str(DAY)}] if kwargs.get('extra_dimension') else [])
                + [{'name': name}], 'conversions': value} for name, value in pairs]
    monkeypatch.setattr(YandexMetricaAPI, 'get_counter_goals', goals)
    monkeypatch.setattr(YandexMetricaAPI, 'get_conversions_by_dimension', conversions)


async def build(db, keys, kind, **kwargs):
    if kind == 'daily':
        return await stats._build_yandex_campaign_daily_conversion_overrides(
            db, [keys.project], DAY, DAY, user_id=keys.user, **kwargs)
    fn = (stats._build_avito_campaign_conversion_overrides if kind == 'avito'
          else stats._build_yandex_campaign_conversion_overrides)
    return await fn(db, [keys.project], DAY, DAY, user_id=keys.user, **kwargs)


@pytest.mark.asyncio
@pytest.mark.parametrize('kind', ['yandex', 'daily', 'avito'])
async def test_live_attribution_releases_only_pool_slot_and_preserves_numbers(source, monkeypatch, kind):
    factory, engine, keys = source
    with factory() as db:
        # A second integration catches accidental lazy loading between calls.
        extra = models.Integration(client_id=keys.project, platform=P.YANDEX_DIRECT,
            access_token=security.encrypt_token('direct-token'), selected_counters='["123"]', selected_goals='["456"]')
        db.add(extra); db.flush()
        db.add(models.Campaign(integration_id=extra.id, name='Газобетон', external_id='333'))
        db.commit()
        calls = []
        provider(monkeypatch, engine, db, calls)
        result = await build(db, keys, kind)
        assert_free(engine, db)
        cid = str(keys.campaigns[(P.YANDEX_DIRECT, 'Газобетон')])
        if kind == 'daily':
            assert result[1] is True and result[0][DAY][cid] == 34
        elif kind == 'avito':
            assert result == {'111': 34, '222': 31}
        else:
            assert result[cid] == 34
        assert calls


@pytest.mark.asyncio
@pytest.mark.parametrize('endpoint', ['campaigns', 'summary', 'dynamics', 'series', 'directions', 'goals'])
async def test_direction_stays_34_not_project_total_65(source, monkeypatch, endpoint):
    factory, engine, keys = source
    with factory() as db:
        calls = []
        provider(monkeypatch, engine, db, calls)
        cid = str(keys.campaigns[(P.YANDEX_DIRECT, 'Газобетон')])
        kwargs = dict(start_date=str(DAY), end_date=str(DAY), client_id=str(keys.project),
            folder_id=None, campaign_ids=[cid], platform='yandex',
            current_user=db.get(models.User, keys.user), db=db)
        if endpoint == 'campaigns':
            rows = await stats.get_campaign_stats(**kwargs, goal_action_ids=None)
            assert len(rows) == 1 and rows[0]['conversions'] == 34 and rows[0]['cpa'] == 100
        elif endpoint == 'summary':
            result = await stats.get_summary(**kwargs, goal_action_ids=None, period_preset=None)
            assert result['leads'] == 34 and result['cpa'] == 100
            assert db.get(models.Client, keys.project).last_dashboard_snapshot['current']['leads'] == 34
        elif endpoint == 'dynamics':
            result = await stats.get_dynamics(**kwargs, goal_action_ids=None)
            assert result['leads'] == [34] and result['cpa'] == [100]
        elif endpoint == 'series':
            result = await stats.get_dynamics_series_endpoint(**kwargs, granularity='week')
            assert result['periods'][0]['leads'] == 34 and result['periods'][0]['cpl'] == 100
        elif endpoint == 'goals':
            result = await stats.get_goals(client_id=keys.project, folder_id=None, integration_id=None,
                date_from=str(DAY), date_to=str(DAY), platform='yandex', campaign_ids=cid,
                direction_name=None, period_preset=None, current_user=kwargs['current_user'], db=db)
            assert result[0]['count'] == 34
        else:
            from backend_api.directions import get_direction_stats
            result = await get_direction_stats(client_id=keys.project, start_date=str(DAY), end_date=str(DAY),
                platform='yandex', current_user=kwargs['current_user'], db=db)
            row = next(item for item in result['items'] if item['id'] == str(keys.direction))
            assert row['leads'] == 34 and row['cpl'] == 100
        assert calls


@pytest.mark.asyncio
@pytest.mark.parametrize('change', ['goals', 'counters', 'token', 'profile', 'rename', 'add_campaign',
                                    'rebind', 'delete', 'owner', 'disabled_user', 'team_revoke'])
async def test_late_result_is_rejected_after_settings_or_access_changed(source, monkeypatch, change):
    factory, engine, keys = source
    if change == 'team_revoke':
        with factory.begin() as other:
            member = models.TeamMember(account_id=keys.user, user_id=keys.other,
                email='foreign@example.test', role=models.TeamMemberRole.MEMBER,
                status=models.TeamMemberStatus.ACTIVE)
            other.add(member); other.flush()
            other.add(models.TeamMemberProject(team_member_id=member.id, project_id=keys.project))
        keys.user = keys.other
    with factory() as db:
        async def fetched(*args):
            assert_free(engine, db)
            with factory.begin() as other:
                integration = other.get(models.Integration, keys.integrations[P.YANDEX_DIRECT])
                if change in ('goals', 'counters', 'token', 'profile'):
                    attr = {'goals': 'selected_goals', 'counters': 'selected_counters',
                            'token': 'access_token', 'profile': 'account_id'}[change]
                    setattr(integration, attr, 'changed')
                elif change == 'rename':
                    other.get(models.Campaign, keys.campaigns[(P.YANDEX_DIRECT, 'Газобетон')]).name = 'Renamed'
                elif change == 'add_campaign':
                    other.add(models.Campaign(integration_id=integration.id, external_id='999', name='Газобетон'))
                elif change == 'delete':
                    other.delete(integration)
                elif change == 'rebind':
                    project = models.Client(owner_id=keys.other, name='Another project')
                    other.add(project); other.flush()
                    integration.client_id = project.id
                elif change == 'owner':
                    other.get(models.Client, keys.project).owner_id = keys.other
                elif change == 'disabled_user':
                    other.get(models.User, keys.user).is_active = False
                else:
                    other.query(models.TeamMemberProject).delete()
            return {'газобетон': 34}, True
        monkeypatch.setattr(stats, '_metrika_campaign_conv_map', fetched)
        with pytest.raises(HTTPException) as exc:
            await build(db, keys, 'yandex')
        assert exc.value.status_code == (403 if change in ('owner', 'disabled_user', 'team_revoke') else 409)
        assert_free(engine, db)


@pytest.mark.asyncio
@pytest.mark.parametrize('failure', [RuntimeError, asyncio.CancelledError])
async def test_error_and_cancel_leave_sql_free(source, monkeypatch, failure):
    factory, engine, keys = source
    with factory() as db:
        async def fetched(*args):
            assert_free(engine, db)
            raise failure()
        monkeypatch.setattr(stats, '_metrika_campaign_conv_map', fetched)
        with pytest.raises(failure):
            await build(db, keys, 'yandex')
        assert_free(engine, db)


@pytest.mark.asyncio
async def test_pending_writes_are_neither_flushed_nor_discarded(source):
    factory, engine, keys = source
    with factory() as db:
        project = db.get(models.Client, keys.project)
        project.name = 'Unsaved user edit'
        with pytest.raises(RuntimeError, match='pending changes'):
            await build(db, keys, 'yandex')
        assert project in db.dirty and project.name == 'Unsaved user edit'


@pytest.mark.asyncio
async def test_duplicate_names_keep_existing_fallback_and_foreign_campaigns_excluded(source, monkeypatch):
    factory, engine, keys = source
    with factory() as db:
        db.get(models.Campaign, keys.campaigns[(P.YANDEX_DIRECT, 'Другое')]).name = 'Газобетон'
        db.commit()
        provider(monkeypatch, engine, db, [])
        assert await build(db, keys, 'yandex') == {}
        # Other platform's id cannot select a Yandex integration.
        assert await build(db, keys, 'yandex', campaign_ids=[keys.campaigns[(P.AVITO_ADS, 'Газобетон')]]) == {}
        assert_free(engine, db)


@pytest.mark.asyncio
@pytest.mark.parametrize('kind', ['yandex', 'daily', 'avito'])
@pytest.mark.parametrize('available', [False, True])
async def test_empty_response_is_not_confused_with_unavailable_goals(source, monkeypatch, kind, available):
    factory, engine, keys = source
    with factory() as db:
        async def fetched(*args):
            assert_free(engine, db)
            return ({}, {}, available) if kind == 'avito' else ({}, available)
        name = {'yandex': '_metrika_campaign_conv_map', 'daily': '_metrika_campaign_daily_conv_map',
                'avito': '_avito_metrika_utm_conv_maps'}[kind]
        monkeypatch.setattr(stats, name, fetched)
        result = await build(db, keys, kind)
        if kind == 'daily':
            assert result == ({}, available)
        elif kind == 'yandex' and available:
            assert result == {str(keys.campaigns[(P.YANDEX_DIRECT, name)]): 0 for name in ('Газобетон', 'Другое')}
        else:
            assert result == {}
        assert_free(engine, db)


@pytest.mark.asyncio
async def test_avito_grant_changed_and_detector_does_not_hide_conflict(source, monkeypatch):
    factory, engine, keys = source
    with factory() as db:
        async def fetched(*args):
            assert_free(engine, db)
            with factory.begin() as other:
                other.get(models.Integration, keys.integrations[P.AVITO_ADS]).metrika_access_token = 'rotated'
            return {'111': 34}, {}, True
        monkeypatch.setattr(stats, '_avito_metrika_utm_conv_maps', fetched)
        with pytest.raises(HTTPException) as exc:
            await build(db, keys, 'avito')
        assert exc.value.status_code == 409
        assert_free(engine, db)

        from backend_api import detector
        monkeypatch.setattr(detector, '_assert_detector_access', lambda *a, **k: None)
        async def conflict(*args, **kwargs):
            raise HTTPException(409, 'Settings changed')
        monkeypatch.setattr(stats, '_build_yandex_campaign_conversion_overrides', conflict)
        with pytest.raises(HTTPException) as exc:
            await detector.get_campaign_highlights(keys.project, str(DAY), str(DAY),
                                                   db.get(models.User, keys.user), db)
        assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_background_sync_does_not_invalidate_settings(source, monkeypatch):
    factory, engine, keys = source
    with factory() as db:
        async def fetched(*args):
            assert_free(engine, db)
            with factory.begin() as other:
                other.get(models.Integration, keys.integrations[P.YANDEX_DIRECT]).balance = 12345
                other.query(models.YandexStats).update({'impressions': 2222})
            return {'газобетон': 34, 'другое': 31}, True
        monkeypatch.setattr(stats, '_metrika_campaign_conv_map', fetched)
        result = await build(db, keys, 'yandex')
        assert result[str(keys.campaigns[(P.YANDEX_DIRECT, 'Газобетон')])] == 34
        assert_free(engine, db)


@pytest.mark.asyncio
@pytest.mark.parametrize('platform', ['yandex', 'avito'])
async def test_filtered_table_matches_full_table_including_previous_cpl(source, monkeypatch, platform):
    factory, engine, keys = source
    native_platform = P.YANDEX_DIRECT if platform == 'yandex' else P.AVITO_ADS
    cls = models.YandexStats if platform == 'yandex' else models.AvitoStats
    previous = DAY - timedelta(days=1)
    with factory.begin() as db:
        for name, cost in [('Газобетон', 3400), ('Другое', 3100)]:
            db.add(cls(client_id=keys.project, campaign_id=keys.campaigns[(native_platform, name)],
                date=previous, cost=cost, clicks=100, impressions=1000, conversions=99))
        db.add(models.MetrikaGoals(client_id=keys.project, integration_id=keys.integrations[native_platform],
            date=previous, goal_id='456', goal_name='Заявка', conversion_count=30))
    with factory() as db:
        async def direct(integration, start, end):
            assert_free(engine, db)
            return ({'газобетон': 34, 'другое': 31} if start == DAY else {'газобетон': 17, 'другое': 13}), True
        async def avito(_db, integration, start, end):
            assert_free(engine, db)
            return ({'111': 34, '222': 31} if start == DAY else {'111': 17, '222': 13}), {}, True
        monkeypatch.setattr(stats, '_metrika_campaign_conv_map', direct)
        monkeypatch.setattr(stats, '_avito_metrika_utm_conv_maps', avito)
        kwargs = dict(start_date=str(DAY), end_date=str(DAY), client_id=str(keys.project), folder_id=None,
            goal_action_ids=None, platform=platform, current_user=db.get(models.User, keys.user), db=db)
        full = await stats.get_campaign_stats(**kwargs, campaign_ids=None)
        cid = str(keys.campaigns[(native_platform, 'Газобетон')])
        filtered = await stats.get_campaign_stats(**kwargs, campaign_ids=[cid])
        assert filtered == [row for row in full if row['id'] == cid]
        assert filtered[0]['conversions'] == 34 and filtered[0]['cpa'] == 100
        assert filtered[0]['trend_cpa'] == -50


@pytest.mark.asyncio
async def test_mixed_table_does_not_count_same_goal_from_another_channel(source, monkeypatch):
    factory, engine, keys = source
    with factory() as db:
        provider(monkeypatch, engine, db, [])
        kwargs = dict(start_date=str(DAY), end_date=str(DAY), client_id=str(keys.project), folder_id=None,
            goal_action_ids=None, platform='all', current_user=db.get(models.User, keys.user), db=db)
        full = await stats.get_campaign_stats(**kwargs, campaign_ids=None)
        for channel in ('yandex', 'avito'):
            assert sum(row['conversions'] for row in full if row['platform'] == channel) == 65
        ids = [str(keys.campaigns[(channel, 'Газобетон')]) for channel in (P.YANDEX_DIRECT, P.AVITO_ADS)]
        filtered = await stats.get_campaign_stats(**kwargs, campaign_ids=ids)
        assert filtered == [row for row in full if row['id'] in ids]
        assert all(row['conversions'] == 34 and row['cpa'] == 100 for row in filtered)


@pytest.mark.asyncio
async def test_plan_query_count_does_not_grow_per_integration(source, monkeypatch):
    from tests.test_summary_queries import statements
    factory, engine, keys = source
    with factory() as db:
        provider(monkeypatch, engine, db, [])
        with statements(engine) as small:
            await build(db, keys, 'yandex')
        with factory.begin() as other:
            for i in range(20):
                integration = models.Integration(client_id=keys.project, platform=P.YANDEX_DIRECT)
                other.add(integration); other.flush()
                other.add(models.Campaign(integration_id=integration.id, name=f'Empty {i}', external_id=str(i)))
        with statements(engine) as large:
            await build(db, keys, 'yandex')
        # Provider test's SELECT 1 happens only for the original configured
        # integration; added integrations have no counter/goal/token.
        assert len(large) <= len(small)
        assert_free(engine, db)
