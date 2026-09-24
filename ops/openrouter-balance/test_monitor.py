import copy
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('balance_monitor', ROOT / 'monitor.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.state, self.sent, self.snapshots = {}, [], []
        self.now = 1_000_000
        self.config = {'warning_usd': 20, 'critical_usd': 5}

    def run_poll(self, amount=50, error=False, sender=None, advance=900):
        self.now += advance
        def fetch():
            if error:
                raise TimeoutError('secret must not enter state or logs')
            return {'data': {'total_credits': 100, 'total_usage': 100 - Decimal(str(amount))}}
        return m.poll(self.state, self.config, fetch, sender or self.sent.append,
                      lambda state: self.snapshots.append(copy.deepcopy(state)), self.now)

    def test_decimal_money_and_negative_balance(self):
        self.assertEqual(m.balance({'data': {'total_credits': 0.3, 'total_usage': 0.2}}), Decimal('.1'))
        self.assertEqual(m.balance({'data': {'total_credits': 10, 'total_usage': 11}}), -1)

    def test_invalid_payload_is_not_zero(self):
        for value in (None, True, '12', float('nan'), float('inf'), -1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                m.balance({'data': {'total_credits': value, 'total_usage': 0}})
        for payload in ({}, {'data': {}}, {'data': None}):
            with self.assertRaises((KeyError, TypeError)):
                m.balance(payload)

    def test_startup_once(self):
        self.run_poll()
        self.run_poll()
        self.run_poll(advance=86400)
        self.assertEqual(len(self.sent), 1)
        self.assertIn('включён', self.sent[0])

    def test_crossing_warning_critical_recovery(self):
        for value in (50, 20, 19, 5, 4, 30, 29):
            self.run_poll(value)
        self.assertEqual(len(self.sent), 4)
        self.assertIn('Низкий', self.sent[1])
        self.assertIn('Критический', self.sent[2])
        self.assertIn('в норме', self.sent[3])

    def test_startup_low_does_not_send_healthy(self):
        self.run_poll(3)
        self.assertEqual(len(self.sent), 1)
        self.assertIn('Критический', self.sent[0])

    def test_critical_reminder_every_12_hours(self):
        self.run_poll(2)
        self.run_poll(1, advance=m.REPEAT - 1)
        self.assertEqual(len(self.sent), 1)
        self.run_poll(0, advance=1)
        self.assertEqual(len(self.sent), 2)

    def test_warning_no_recurring_spam(self):
        self.run_poll(12)
        self.run_poll(10, advance=86400)
        self.assertEqual(len(self.sent), 1)

    def test_restart_retains_deduplication(self):
        self.run_poll(10)
        self.state = json.loads(json.dumps(self.state))
        self.run_poll(9)
        self.assertEqual(len(self.sent), 1)

    def test_errors_do_not_overwrite_last_balance(self):
        self.run_poll(50)
        for _ in range(2):
            self.assertFalse(self.run_poll(error=True))
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(self.state['remaining_usd'], '50')
        self.run_poll(error=True)
        self.assertIn('Остаток неизвестен', self.sent[-1])
        self.run_poll(error=True)
        self.assertEqual(len(self.sent), 2)
        self.run_poll(49)
        self.assertEqual(len(self.sent), 3)
        self.assertIn('снова работает', self.sent[-1])

    def test_unconfirmed_delivery_is_throttled_and_persisted_before_send(self):
        def failed_send(message):
            self.assertFalse(self.snapshots[-1]['balance_notice']['sent'])
            self.sent.append(message)
            raise TimeoutError('secret')
        self.run_poll(10, sender=failed_send)
        self.run_poll(10)
        self.assertEqual(len(self.sent), 1)
        self.run_poll(9, advance=m.REPEAT)
        self.assertEqual(len(self.sent), 2)
        self.assertTrue(self.state['balance_notice']['sent'])

    def test_escalation_not_delayed_by_previous_delivery_failure(self):
        def fail(message):
            raise TimeoutError()
        self.run_poll(10, sender=fail)
        self.run_poll(4)
        self.assertEqual(len(self.sent), 1)
        self.assertIn('Критический', self.sent[-1])

    def test_bad_thresholds_fail_before_network(self):
        self.config['critical_usd'] = 30
        with self.assertRaises(ValueError):
            self.run_poll()
        self.assertFalse(self.sent)

    def test_atomic_private_state(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'state.json'
            m.save(path, {'test': 1})
            m.save(path, {'test': 2})
            self.assertEqual(json.loads(path.read_text()), {'test': 2})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertFalse(path.with_suffix('.tmp').exists())

    def test_no_redirects(self):
        self.assertIsNone(m.NoRedirect().redirect_request(None, None, None, None, None, None))

    def test_only_fixed_credits_get(self):
        with patch.object(m, 'request_json', return_value={}) as request:
            m.fetch_credits('sk-or-v1-test')
        req = request.call_args.args[0]
        self.assertEqual(req.full_url, m.CREDITS_URL)
        self.assertEqual(req.get_method(), 'GET')

    def test_telegram_response_requires_ack(self):
        with patch.object(m, 'request_json', return_value={'ok': False}):
            with self.assertRaises(ValueError):
                m.send_telegram({'chat_id': -123}, '123:test', 'hello')

    def test_telegram_group_only(self):
        with patch.object(m, 'request_json') as request, self.assertRaises(ValueError):
            m.send_telegram({'chat_id': 123}, '123:test', 'hello')
        request.assert_not_called()

    def test_credits_gateway_api1_read_only(self):
        conf = (ROOT.parent / 'ai-gateway/openrouter.conf').read_text()
        block = conf.split('location = /api/v1/credits {', 1)[1].split('location = ', 1)[0]
        self.assertIn('allow 10.78.0.1;', block)
        self.assertNotIn('allow 10.78.0.2;', block)
        self.assertIn('limit_except GET { deny all; }', block)

    def test_single_host_no_db_no_app_key(self):
        service = (ROOT / 'admirra-openrouter-balance.service').read_text()
        self.assertIn('DynamicUser=yes', service)
        self.assertIn('IPAddressDeny=any', service)
        self.assertIn('ConditionPathExists=', service)
        self.assertNotIn('EnvironmentFile=', service)
        source = (ROOT / 'monitor.py').read_text()
        self.assertNotIn('psycopg', source)
        self.assertNotIn('chat/completions', source)


if __name__ == '__main__':
    unittest.main()
