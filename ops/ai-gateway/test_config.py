"""Non-network regression checks for gateway policy and rollback safety."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('switch_assistant', ROOT / 'switch_assistant.py')
switch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(switch)


class GatewayConfigTests(unittest.TestCase):
    def test_private_listener_and_acl(self):
        conf = (ROOT / 'openrouter.conf').read_text()
        self.assertIn('listen 10.78.0.3:8080;', conf)
        self.assertNotIn('listen 80;', conf)
        self.assertIn('deny all;', conf)
        self.assertIn('location = /api/v1/chat/completions', conf)
        self.assertIn('limit_except POST { deny all; }', conf)
        self.assertIn('location / { return 404; }', conf)

    def test_streaming_tls_and_no_replay(self):
        conf = (ROOT / 'proxy.conf').read_text()
        for directive in ('proxy_buffering off;', 'proxy_request_buffering off;',
                          'proxy_cache off;', 'proxy_next_upstream off;',
                          'proxy_ssl_verify on;', 'proxy_ignore_client_abort off;'):
            self.assertIn(directive, conf)
        self.assertIn('set $ai_upstream openrouter.ai;', conf)
        self.assertNotIn('$http_host', conf)

    def test_logs_do_not_record_request_payload(self):
        log = (ROOT / 'openrouter.conf').read_text().split('log_format ', 1)[1].split(';', 1)[0]
        for field in ('$request_body', '$request_uri', '$args', '$http_authorization', '$request"'):
            self.assertNotIn(field, log)

    def test_firewall_only_replaces_own_table(self):
        conf = (ROOT / 'gateway.nft').read_text()
        self.assertNotIn('flush ruleset', conf)
        self.assertIn('destroy table inet admirra_ai_gateway', conf)
        self.assertIn('policy drop;', conf)
        self.assertIn('udp sport 67 udp dport 68 accept', conf)
        self.assertIn('udp sport 547 udp dport 546 accept', conf)

    def test_rollback_refuses_intervening_change(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env = root / '.env'
            env.write_text('OTHER=changed\n')
            (root / 'metadata.json').write_text(json.dumps({'activated_env_sha256': switch.digest(b'OTHER=original\n')}))
            with patch.object(switch, 'ENV', env), patch.object(switch, 'compose') as compose:
                with self.assertRaises(SystemExit):
                    switch.rollback(root)
                compose.assert_not_called()
                self.assertEqual(env.read_text(), 'OTHER=changed\n')

    def test_rollback_restores_exact_env_and_pinned_image(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env = root / '.env'
            active = b'AI_ASSISTANT_PROVIDER=openrouter\n'
            original = b'AI_ASSISTANT_PROVIDER=proxyapi\nOTHER=preserved\n'
            env.write_bytes(active)
            (root / 'metadata.json').write_text(json.dumps({'activated_env_sha256': switch.digest(active)}))
            (root / 'original.env').write_bytes(original)
            with patch.object(switch, 'ENV', env), patch.object(switch, 'compose') as compose:
                switch.rollback(root)
                compose.assert_called_once_with(root / 'image.json')
                self.assertEqual(env.read_bytes(), original)
                self.assertEqual(env.stat().st_mode & 0o777, 0o600)

    def test_compose_cannot_build_pull_or_restart_dependencies(self):
        with patch.object(switch.subprocess, 'run') as run:
            switch.compose(Path('/root/test/image.json'))
            command = run.call_args.args[0]
            for option in ('--no-deps', '--no-build', '--pull'):
                self.assertIn(option, command)
            self.assertEqual(command[command.index('--pull') + 1], 'never')
            self.assertEqual(command[-1], 'backend')


if __name__ == '__main__':
    unittest.main()
