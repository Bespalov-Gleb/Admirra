from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
READ_PROXY = ROOT / "ops" / "api2_canary" / "nginx" / "admirra-api2-read-proxy.conf"


class Api2CanaryNginxTests(unittest.TestCase):
    def test_read_canary_has_bounded_failover_time(self):
        config = READ_PROXY.read_text(encoding="utf-8")

        self.assertIn("proxy_connect_timeout 1s;", config)
        self.assertIn("proxy_read_timeout 5s;", config)
        self.assertIn("proxy_send_timeout 2s;", config)
        self.assertIn("proxy_next_upstream_tries 2;", config)
        self.assertIn("proxy_next_upstream_timeout 12s;", config)
        self.assertNotIn("proxy_read_timeout 120s;", config)

    def test_single_timeout_does_not_eject_both_replicas(self):
        config = READ_PROXY.with_name('admirra-api2-upstream.conf').read_text()
        self.assertEqual(config.count('max_fails=3 fail_timeout=5s;'), 2)


if __name__ == "__main__":
    unittest.main()
