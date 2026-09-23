from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from automation.ads_sync_contract import (IncompleteAdsSnapshot, direct_tsv, number,
                                         vk_statistics, avito_entity)
from automation.ads_sync_work import windows
from automation.yandex_direct import YandexDirectAPI
from automation.avito_ads import AvitoAdsAPI


@pytest.mark.parametrize("value", [None, "NaN", "Infinity", "-1", True, "broken", "1e18"])
def test_invalid_metrics_are_not_silent_zero(value):
    with pytest.raises(IncompleteAdsSnapshot):
        number(value)


def test_integer_counts_and_explicit_missing_conversion():
    with pytest.raises(IncompleteAdsSnapshot):
        number("1.4", integer=True)
    assert number("--", integer=True, missing=True) == 0
    assert number("1.25") == Decimal("1.25")


HEADER = "Date\tCampaignId\tCampaignName\tImpressions\tClicks\tCost\tConversions"
ROW = "2026-09-10\t42\tTest\t10\t2\t1000000\t1"


def test_direct_explicit_empty_and_keyword_campaign_binding():
    assert direct_tsv(HEADER + "\nTotal rows: 0", "campaign") == []
    assert direct_tsv(HEADER + "\n" + ROW + "\nTotal rows: 1", "campaign")[0]["cost"] == 1
    keyword = ROW.replace("42\tTest", "42\tkeyword\tTest")
    row = direct_tsv(keyword, "keyword")[0]
    assert row["campaign_id"] == "42" and row["name"] == "keyword"


@pytest.mark.parametrize('quoted', [False, True])
def test_direct_real_report_title_before_columns(quoted):
    title = 'AgencyStats_campaign_2026-09-10_2026-09-10_123 (2026-09-10 - 2026-09-10)'
    if quoted:
        title = '"' + title + '"'
    assert direct_tsv(title + '\n' + HEADER + '\n' + ROW + '\nTotal rows: 1', 'campaign')[0]['cost'] == 1
    assert direct_tsv(title + '\n' + HEADER + '\nTotal rows: 0', 'campaign') == []
    with pytest.raises(IncompleteAdsSnapshot):
        direct_tsv(title + '\n' + HEADER + '\n' + ROW + '\nTotal rows: 2', 'campaign')
    with pytest.raises(IncompleteAdsSnapshot):
        direct_tsv(title, 'campaign')


@pytest.mark.parametrize("response", ["", "upstream error", HEADER + "\ntruncated",
    HEADER + "\n" + ROW + "\nTotal rows: 2", ROW.replace("1000000", "NaN")])
def test_direct_truncation_fails(response):
    with pytest.raises((IncompleteAdsSnapshot, ValueError)):
        direct_tsv(response, "campaign")


def test_direct_campaign_wizard_groups_preserve_all_metrics_without_invented_ids():
    header = HEADER.replace('CampaignName', 'CampaignName\tAdGroupId\tAdGroupName')
    row = ROW.replace('42\tTest', '42\tTest\t--\t--')
    numeric = ROW.replace('42\tTest', '42\tTest\t123\tGroup')
    rows = direct_tsv('\n'.join([header, row, row, numeric, 'Total rows: 3']), 'group')
    assert len(rows) == 2
    assert rows[0]['group_id'] is None
    assert rows[0]['cost'] == 2 and rows[0]['conversions'] == 2
    assert sum(r['clicks'] for r in rows) == 6
    assert rows[1]['group_id'] == '123'
    with pytest.raises(IncompleteAdsSnapshot):
        direct_tsv('\n'.join([header, row, row, 'Total rows: 1']), 'group')
    for bad in ('\tbad\t--', '\t--\tNamed', '\t\t--'):
        with pytest.raises(IncompleteAdsSnapshot):
            direct_tsv(header + '\n' + row.replace('\t--\t--', bad), 'group')


def test_opaque_groups_are_only_allowed_for_direct_and_still_reject_duplicates():
    from automation.ads_sync_work import validate
    from core import models
    plan = SimpleNamespace(start='2026-09-10', end='2026-09-10', platform=models.IntegrationPlatform.YANDEX_DIRECT)
    row = dict(date=plan.start, campaign_id='42', group_id=None, name='--',
               impressions=10, clicks=2, cost=Decimal('1'), conversions=1)
    snapshot = {'data': {'groups': [row]}}
    validate(plan, snapshot)
    snapshot['data']['groups'].append(dict(row))
    with pytest.raises(IncompleteAdsSnapshot):
        validate(plan, snapshot)
    snapshot['data']['groups'].pop()
    plan.platform = models.IntegrationPlatform.AVITO_ADS
    with pytest.raises(IncompleteAdsSnapshot):
        validate(plan, snapshot)


def test_direct_same_criteria_text_is_coalesced_only_within_campaign_and_day():
    header = HEADER.replace('CampaignId\t', 'CampaignId\tCriteria\t')
    row = ROW.replace('42\tTest', '42\t---autotargeting\tTest')
    rows = direct_tsv('\n'.join([header, row, row, row.replace('\t42\t', '\t43\t'),
                               row.replace('2026-09-10', '2026-09-11'), 'Total rows: 4']), 'keyword')
    assert len(rows) == 3 and rows[0]['cost'] == 2 and rows[0]['conversions'] == 2
    assert sum(r['cost'] for r in rows) == 4
    with pytest.raises(IncompleteAdsSnapshot):
        direct_tsv('\n'.join([header, row, row, 'Total rows: 1']), 'keyword')


@pytest.mark.asyncio
async def test_direct_catalog_pages_and_repeated_page_rejected(monkeypatch):
    pages = [{"result": {"Campaigns": [{"Id": 42, "Name": "One"}], "LimitedBy": 1}},
             {"result": {"Campaigns": [{"Id": 43, "Name": "Two"}]}}]
    calls = []
    async def send(url, **kwargs):
        calls.append(kwargs["json"]["params"]["Page"])
        return httpx.Response(200, json=pages.pop(0), request=httpx.Request("POST", url))
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.post.side_effect = send
    monkeypatch.setattr("automation.provider_transport.provider_client", lambda *a: client)
    monkeypatch.setattr("automation.request_queue.get_api_limiter", lambda *a: SimpleNamespace(acquire=AsyncMock()))
    api = YandexDirectAPI("synthetic")
    api.strict_sync = True
    assert [r["id"] for r in await api.get_campaigns()] == ["42", "43"]
    assert [c["Offset"] for c in calls] == [0, 1]
    pages.extend([{"result": {"Campaigns": [{"Id": 42}], "LimitedBy": 1}},
                  {"result": {"Campaigns": [{"Id": 42}]}}])
    with pytest.raises(IncompleteAdsSnapshot):
        await api.get_campaigns()


def test_vk_zero_nested_goal_is_not_overridden_and_empty_is_explicit():
    payload = {"items": [{"id": 42, "rows": [{"date": "2026-09-10",
        "base": {"shows": 10, "clicks": 2, "spent": 4, "goals": 65, "vk": {"goals": 0}}}]}]}
    assert vk_statistics(payload, {"42": "Test"}, "2026-09-10", "2026-09-10", {"42"})[0]["conversions"] == 0
    for invalid in ({}, {"items": [{"id": 42}]}, {"items": [{"id": 43, "rows": []}]}):
        with pytest.raises(IncompleteAdsSnapshot):
            vk_statistics(invalid, {"42": "Test"}, "2026-09-10", "2026-09-10", {"42"})


def test_vk_provider_rates_are_preserved_with_calculation_only_as_fallback():
    base = dict(shows=10, clicks=2, spent=100, cpc="48.52", vk=dict(goals=1, cpa="98.21"))
    payload = {"items": [{"id": 42, "rows": [{"date": "2026-09-10", "base": base}]}]}
    def parse(): return vk_statistics(payload, {"42": "Test"}, "2026-09-10", "2026-09-10", {"42"})[0]
    row = parse()
    assert row["cpc"] == Decimal("48.52") and row["cpa"] == Decimal("98.21")
    base.pop("cpc")
    base["vk"]["cpa"] = 0
    assert parse()["cpc"] == 50 and parse()["cpa"] == 100


@pytest.mark.asyncio
async def test_avito_mixed_children_fetch_missing_not_synthetic_zero():
    api = AvitoAdsAPI(credential_type="client_credentials", client_id="test", client_secret="test", account_id="1")
    api.strict_sync = True
    data = [{"timestamp": "2026-09-10", "views": 10, "clicks": 2, "spend": 4}]
    api._request = AsyncMock(return_value={"campaign": {"id": 42, "data": data},
        "groups": [{"id": 1, "data": data}, {"id": 2}], "creatives": []})
    api.get_group_statistics = AsyncMock(return_value=[{"group_id": "2", "cost": 7}])
    result = await api.get_campaign_statistics_bundle("42", "2026-09-10", "2026-09-10")
    assert len(result["groups"]) == 2
    api.get_group_statistics.assert_awaited_once_with("42", ["2"], "2026-09-10", "2026-09-10", account_id="1")


def test_avito_missing_daily_data_is_not_empty_success():
    with pytest.raises(IncompleteAdsSnapshot):
        avito_entity({"id": 1})
    avito_entity({"id": 1, "data": []})


def test_windows_are_contiguous_and_at_most_ninety_days():
    chunks = list(windows("2026-01-01", "2026-09-22"))
    assert len(chunks) == 3
    assert chunks[0][0] == "2026-01-01" and chunks[-1][1] == "2026-09-22"
    for index, (start, end) in enumerate(chunks):
        assert (date.fromisoformat(end) - date.fromisoformat(start)).days < 90
        if index:
            assert (date.fromisoformat(start) - date.fromisoformat(chunks[index - 1][1])).days == 1
