import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from ai.assistant import tools, vk_reporting


def row(cid, cost=0, clicks=0, conversions=0, day='2026-09-08'):
    return dict(campaign_id=str(cid), campaign_name='Campaign ' + str(cid), date=day,
                cost=cost, clicks=clicks, conversions=conversions, impressions=clicks * 100)


class ReportingTests(unittest.TestCase):
    def test_totals_include_activity_after_first_200_rows(self):
        rows = [row(i) for i in range(300)] + [row(400, '25723.60', 371, 22)]
        totals, grouped = vk_reporting.aggregate(rows)
        self.assertEqual(totals['cost'], 25723.6)
        self.assertEqual(totals['conversions'], 22)
        self.assertEqual(grouped[0]['campaign_id'], '400')
        page = vk_reporting.page(grouped, 0, 100)
        self.assertTrue(page['has_more'])
        self.assertEqual(page['next_offset'], 100)

    def test_ratios_are_weighted_and_money_is_decimal(self):
        totals, grouped = vk_reporting.aggregate([row(1, '0.1', 1, 1), row(1, '0.2', 2, 0)])
        self.assertEqual(totals['cost'], .3)
        self.assertEqual(totals['cpc'], .1)
        self.assertEqual(totals['cpa'], .3)
        self.assertEqual(len(grouped), 1)

    def test_daily_totals_and_zero_denominators(self):
        total, days = vk_reporting.aggregate([row(1, 8, day='2026-09-09'), row(2, 2)], 'date')
        self.assertEqual([d['date'] for d in days], ['2026-09-08', '2026-09-09'])
        self.assertEqual(total['cost'], 10)
        self.assertIsNone(total['cpa'])
        self.assertIsNone(total['cpc'])

    def test_string_and_integer_ids(self):
        campaigns = [{'id': '10'}, {'id': '20'}]
        self.assertEqual(vk_reporting.select_campaigns(campaigns, ['10', 10]), campaigns[:1])
        for ids in [['foreign'], '10', [{'id': '10'}], [True]]:
            with self.assertRaises(ValueError):
                vk_reporting.select_campaigns(campaigns, ids)

    def test_validation(self):
        for args in [{'offset': -1}, {'limit': 201}, {'limit': 0}, {'offset': True}]:
            with self.assertRaises(ValueError):
                vk_reporting.page_options(args)
        with self.assertRaises(ValueError):
            vk_reporting.validate_period({'date_from': '2026-09-15', 'date_to': '2026-09-01'})


class ToolTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.api = SimpleNamespace(get_campaigns=AsyncMock(return_value=[{'id': '1', 'name': 'One'}]),
                                   get_statistics=AsyncMock(return_value=[row(1, 10, 2, 1)]))
        self.ctx = SimpleNamespace(vk=lambda: SimpleNamespace(api=AsyncMock(return_value=self.api)))
        self.args = {'date_from': '2026-09-08', 'date_to': '2026-09-14'}

    async def test_filtered_tool_accepts_schema_string_ids(self):
        result = json.loads(await tools.execute_tool('vk_get_statistics', {**self.args, 'campaign_ids': ['1']}, self.ctx))
        self.assertNotIn('error', result)
        self.assertEqual(result['totals']['cost'], 10)
        self.assertEqual(self.api.get_statistics.call_args.kwargs['campaigns'], [{'id': '1', 'name': 'One'}])

    async def test_unknown_filter_never_falls_back_to_full_cabinet(self):
        result = json.loads(await tools.execute_tool('vk_get_statistics', {**self.args, 'campaign_ids': ['999']}, self.ctx))
        self.assertIn('error', result)
        self.api.get_statistics.assert_not_awaited()

    async def test_empty_campaigns_do_not_refetch_full_cabinet(self):
        self.api.get_campaigns.return_value = []
        result = json.loads(await tools.execute_tool('vk_get_statistics', self.args, self.ctx))
        self.assertEqual(result['data_status'], 'no_rows')
        self.api.get_statistics.assert_not_awaited()

    async def test_totals_unchanged_across_pages(self):
        self.api.get_statistics.return_value = [row(i, i, 1, 1) for i in range(250)]
        first = json.loads(await tools.execute_tool('vk_get_statistics', self.args, self.ctx))
        second = json.loads(await tools.execute_tool('vk_get_statistics', {**self.args, 'offset': 100}, self.ctx))
        self.assertEqual(first['totals'], second['totals'])
        self.assertEqual(first['totals']['cost'], sum(range(250)))
        self.assertEqual(first['rows'][0]['campaign_id'], '249')
        self.assertEqual(second['rows'][0]['campaign_id'], '149')

    async def test_campaign_list_includes_full_status_counts_and_pagination(self):
        self.api.get_campaigns.return_value = [dict(id=str(i), status='deleted') for i in range(250)] + [dict(id='999', status='active')]
        result = json.loads(await tools.execute_tool('vk_get_campaigns', {}, self.ctx))
        self.assertEqual(result['campaigns'][0]['id'], '999')
        self.assertEqual(result['status_counts'], {'active': 1, 'deleted': 250})
        self.assertEqual(result['row_count'], 251)
        self.assertTrue(result['has_more'])

    async def test_upstream_error_is_not_reported_as_zero(self):
        self.api.get_statistics.side_effect = RuntimeError('VK temporarily unavailable')
        result = json.loads(await tools.execute_tool('vk_get_statistics', self.args, self.ctx))
        self.assertIn('error', result)
        self.assertNotIn('totals', result)

    async def test_daily_tool_mode(self):
        result = json.loads(await tools.execute_tool('vk_get_statistics', {**self.args, 'group_by': 'date'}, self.ctx))
        self.assertEqual(result['rows'][0]['date'], '2026-09-08')
        self.assertEqual(result['totals']['cost'], 10)


if __name__ == '__main__':
    unittest.main()
