"""Policy tests plus opt-in isolated real-Nginx failure injection (no prod I/O)."""
import collections
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import unittest

from ops.api2_canary.advance_rollout import business_routes
from ops.api2_canary.harden_read_transport import patch_reads, patch_site, NOTIFICATIONS

ROOT = Path(__file__).resolve().parents[1]
CONF = ROOT / 'ops/api2_canary/nginx'


def expanded_site():
    return business_routes((CONF / 'admirra.ru').read_text())


class ReadTransportPolicyTest(unittest.TestCase):
    def test_upgrade_old_site_and_preserve_mutations(self):
        old = expanded_site().replace(NOTIFICATIONS, '').replace('proxy_connect_timeout 3s;', 'proxy_connect_timeout 1s;')
        result = patch_site(old)
        self.assertEqual(result, old.replace('proxy_connect_timeout 1s;', 'proxy_connect_timeout 3s;').replace('    location /api/ {', NOTIFICATIONS + '    location /api/ {'))
        self.assertEqual(result.count('proxy_next_upstream off;'), 3)
        self.assertIn('client_max_body_size 25m;', result)
        self.assertNotIn('location /api/notifications/', result)  # Exact only!
        self.assertEqual(patch_site(result), result)

    def test_drift_is_rejected(self):
        for old in (expanded_site().replace('proxy_next_upstream off;', 'proxy_next_upstream timeout;'),
                    expanded_site().replace('proxy_connect_timeout 3s;', 'proxy_connect_timeout 60s;'),
                    expanded_site().replace('^(GET|HEAD)$', '^GET$')):
            with self.assertRaises(ValueError):
                patch_site(old)

    def test_read_limits_and_idempotence(self):
        text = (CONF / 'admirra-api2-read-proxy.conf').read_text()
        self.assertEqual(patch_reads(text), text)
        self.assertEqual(patch_reads(text.replace('proxy_connect_timeout 3s;', 'proxy_connect_timeout 1s;')), text)
        with self.assertRaises(ValueError):
            patch_reads(text.replace('proxy_read_timeout 5s;', 'proxy_read_timeout 120s;'))


NGINX = shutil.which('nginx')


@unittest.skipUnless(NGINX and os.getenv('WW_TEST') == '1' and os.getenv('WW_TEST_ID'),
                     'requires explicit isolated WW_TEST=1 WW_TEST_ID and nginx')
class ReadTransportNginxTest(unittest.TestCase):
    """Own loopback ports, temp config/pid, mock APIs; never reload system nginx."""
    def setUp(self):
        self.calls = collections.Counter()
        self.requests = []
        self.primary_status = 503
        self.backup_status = 200
        self.delay = 0
        case = self

        def handler(role):
            class Handler(BaseHTTPRequestHandler):
                def do_GET(self):
                    case.calls[role] += 1
                    length = int(self.headers.get('Content-Length', 0))
                    payload = self.rfile.read(length) if length else b''
                    case.requests.append((role, self.command, self.path, payload))
                    if role == 'primary' and case.delay:
                        time.sleep(case.delay)
                    status = case.primary_status if role == 'primary' else case.backup_status
                    self.send_response(status)
                    self.send_header('Content-Length', '2')
                    self.end_headers()
                    if self.command != 'HEAD':
                        try:
                            self.wfile.write(b'[]')
                        except (BrokenPipeError, ConnectionResetError):
                            pass
                do_POST = do_PUT = do_DELETE = do_HEAD = do_GET
                def log_message(self, *args):
                    pass
            return Handler

        self.servers = []
        for role in ('primary', 'backup'):
            server = ThreadingHTTPServer(('127.0.0.1', 0), handler(role))
            self.servers.append(server)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            self.addCleanup(server.server_close)
            self.addCleanup(server.shutdown)
        primary, backup = [s.server_address[1] for s in self.servers]
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            self.port = sock.getsockname()[1]
        self.tmp = tempfile.TemporaryDirectory(prefix='admirra-read-transport-')
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        reads = patch_reads((CONF / 'admirra-api2-read-proxy.conf').read_text())
        reads = re.sub(r'access_log .*?;', 'access_log off;', reads)
        (root / 'reads.conf').write_text(reads)
        site = patch_site(expanded_site())
        # Keep all production API locations/guards, strip only frontend/TLS/docs.
        start = site.index('    location ~ ^/api/assistant/conversations/')
        end = site.index('    location /docs')
        locations = site[start:end].replace('http://127.0.0.1:8001;', f'http://127.0.0.1:{primary};')
        locations = locations.replace('/etc/nginx/snippets/admirra-api2-read-proxy.conf', str(root / 'reads.conf'))
        locations = re.sub(r'access_log .*?;', 'access_log off;', locations)
        config = f'''worker_processes 1;
daemon off;
pid {root}/nginx.pid;
error_log {root}/error.log;
events {{ worker_connections 64; }}
http {{
    access_log off;
    upstream admirra_api_read_canary {{
        server 127.0.0.1:{primary} max_fails=0;
        server 127.0.0.1:{backup} backup;
    }}
    server {{ listen 127.0.0.1:{self.port};
{locations}
    }}
}}
'''
        (root / 'nginx.conf').write_text(config)
        command = [NGINX, '-p', str(root), '-c', str(root / 'nginx.conf')]
        subprocess.run(command + ['-t'], check=True, capture_output=True, timeout=5)
        self.nginx = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(self.stop_nginx)
        for _ in range(100):
            try:
                with socket.create_connection(('127.0.0.1', self.port), timeout=.1):
                    return
            except OSError:
                time.sleep(.02)
        self.fail('Isolated nginx did not start')

    def stop_nginx(self):
        self.nginx.terminate()
        try:
            self.nginx.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.nginx.kill()
            self.nginx.wait(timeout=5)

    def request(self, path='/api/notifications/', method='GET'):
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=18)
        try:
            connection.request(method, path, body=b'test' if method == 'POST' else None)
            response = connection.getresponse()
            response.read()
            return response.status
        finally:
            connection.close()

    def test_notifications_slash_and_query_fail_over(self):
        self.assertEqual(self.request('/api/notifications/?test=1'), 200)
        self.assertEqual(dict(self.calls), {'primary': 1, 'backup': 1})
        self.assertTrue(all(r[2].endswith('?test=1') for r in self.requests))

    def test_read_timeout_fails_over(self):
        self.delay = 6
        started = time.monotonic()
        self.assertEqual(self.request(), 200)
        self.assertGreater(time.monotonic() - started, 4.8)
        self.assertLess(time.monotonic() - started, 8)
        self.assertEqual(dict(self.calls), {'primary': 1, 'backup': 1})

    def test_connection_refused_fails_over(self):
        self.servers[0].shutdown()
        self.servers[0].server_close()
        self.assertEqual(self.request(), 200)
        self.assertEqual(dict(self.calls), {'backup': 1})

    def test_existing_slashless_and_head_reads_keep_failover(self):
        self.assertEqual(self.request('/api/notifications'), 200)
        self.assertEqual(self.request('/api/notifications/', 'HEAD'), 200)
        self.assertEqual(dict(self.calls), {'primary': 2, 'backup': 2})

    def test_both_failed_only_two_attempts(self):
        self.backup_status = 503
        self.assertEqual(self.request(), 503)
        self.assertEqual(dict(self.calls), {'primary': 1, 'backup': 1})

    def test_auth_error_not_retried(self):
        self.primary_status = 401
        self.assertEqual(self.request(), 401)
        self.assertEqual(dict(self.calls), {'primary': 1})

    def test_non_get_notifications_preserves_method_body_no_retry(self):
        self.assertEqual(self.request('/api/notifications/?test=1', 'POST'), 503)
        self.assertEqual(self.requests, [('primary', 'POST', '/api/notifications/?test=1', b'test')])

    def test_business_mutations_and_streaming_never_retry(self):
        for path in ('/api/notifications/read-all', '/api/notifications/test/read',
                     '/api/billing/pay', '/api/reports/send', '/api/assistant/conversations/test/messages'):
            with self.subTest(path=path):
                self.assertEqual(self.request(path, 'POST'), 503)
        self.assertEqual(dict(self.calls), {'primary': 5})


if __name__ == '__main__':
    unittest.main()
