from pathlib import Path
import unittest

from ops.deploy_pool_keepalive import patch_rules, patch_upstream, SUMMARIES

ROOT = Path(__file__).resolve().parents[1]


class PoolKeepaliveTests(unittest.TestCase):
    def test_production_weights_log_and_failover_are_preserved(self):
        source = '''upstream admirra_api_read_canary {
    least_conn;
    server 127.0.0.1:8001 weight=1 max_fails=3 fail_timeout=5s;
    server 10.77.0.2:8001 weight=1 max_fails=3 fail_timeout=5s;
    keepalive 16;
}
log_format admirra_api_canary 'unchanged';
'''
        result = patch_upstream(source)
        self.assertEqual(result.count('weight=1'), 2)
        self.assertNotIn('proxy_next_upstream', result)
        self.assertIn('keepalive_timeout 3s;', result)
        self.assertTrue(result.endswith("log_format admirra_api_canary 'unchanged';\n"))
        for bad in (result, source.replace('weight=1 max_fails=3 fail_timeout=5s;', 'down;'), ''):
            with self.assertRaises(ValueError):
                patch_upstream(bad)

    def test_alert_patch_changes_only_human_summary_not_expressions_or_names(self):
        desired = (ROOT / 'ops/monitoring/rules.yml').read_text()
        old = desired
        for original, new in SUMMARIES.items():
            old = old.replace(new, original)
        self.assertEqual(patch_rules(old), desired)
        with self.assertRaises(ValueError):
            patch_rules(desired)


if __name__ == '__main__':
    unittest.main()
