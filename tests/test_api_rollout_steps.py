import datetime as dt
import unittest
from ops.api2_canary.advance_rollout import business_routes,weighted,soak_ready

class RolloutStepsTest(unittest.TestCase):
    def test_weights_only_change_two_reviewed_servers(self):
        source='server 127.0.0.1:8001 weight=9 max_fails=1 fail_timeout=10s;\nserver 10.77.0.2:8001 weight=1 max_fails=1 fail_timeout=10s;'
        self.assertIn('weight=3',weighted(source,25))
        self.assertEqual(weighted(weighted(source,25),50).count('weight=1'),2)
        with self.assertRaises(ValueError): weighted(source.replace('8001','8002'),25)
        hardened = source.replace('max_fails=1 fail_timeout=10s', 'max_fails=3 fail_timeout=5s')
        self.assertEqual(weighted(hardened, 50).count('max_fails=3 fail_timeout=5s'), 2)

    def test_mutations_have_no_retries_and_attachment_limit_is_preserved(self):
        source='''location /api/ {
          proxy_pass http://127.0.0.1:8001/api/;
        }
        location ~ ^/api/assistant/conversations/ {
          client_max_body_size 25m;
          proxy_pass http://127.0.0.1:8001;
        }
        location / { proxy_pass http://127.0.0.1:8080; }
        '''
        result=business_routes(source)
        self.assertEqual(result.count('proxy_next_upstream off;'),2)
        self.assertEqual(result.count('proxy_pass http://admirra_api_read_canary;'),2)
        self.assertIn('client_max_body_size 25m;',result)
        self.assertIn('proxy_pass http://127.0.0.1:8080;',result)
        with self.assertRaises(ValueError): business_routes(result)

    def test_soak_cannot_be_skipped_or_future_dated(self):
        now=dt.datetime.now(dt.timezone.utc)
        self.assertFalse(soak_ready({'started_at':now.isoformat()},now))
        self.assertFalse(soak_ready({'started_at':(now+dt.timedelta(hours=1)).isoformat()},now))
        self.assertTrue(soak_ready({'started_at':(now-dt.timedelta(minutes=30)).isoformat()},now))
