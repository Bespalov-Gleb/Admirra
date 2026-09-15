"""Isolated real-nginx synthetic SSE/guard checks. No external API or credentials.

Run on the gateway: python3 test_gateway.py. Uses loopback ports 18080/18081;
does not edit/reload the live nginx configuration. Requires installed nginx.
"""
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import http.client
import json
from pathlib import Path
import subprocess
import tempfile
import threading
import time


class Mock(ThreadingHTTPServer):
    request_queue_size = 256
    daemon_threads = True


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    failures = 0

    def log_message(self, *_args):
        pass

    def do_POST(self):
        self.rfile.read(int(self.headers.get('Content-Length', 0)))
        if self.headers.get('X-Test-Fail'):
            Handler.failures += 1
            self.send_response(503)
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Connection', 'close')
        self.end_headers()
        try:
            for i in range(3):
                self.wfile.write(('data: ' + json.dumps({'part': i}) + '\n\n').encode())
                self.wfile.flush()
                if i < 2:
                    time.sleep(0.5)
            self.wfile.write(b'data: [DONE]\n\n')
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        self.close_connection = True


def request(method, path, headers=None, stream=False):
    c = http.client.HTTPConnection('127.0.0.1', 18080, timeout=10)
    start = time.monotonic()
    try:
        c.request(method, path, body=b'{}' if method == 'POST' else None, headers=headers or {})
        r = c.getresponse()
        if stream:
            first = r.readline()
            first_at = time.monotonic() - start
            rest = r.read()
            elapsed = time.monotonic() - start
            assert r.status == 200 and b'"part": 0' in first and b'[DONE]' in rest
            assert elapsed - first_at >= 0.8, (first_at, elapsed)
            return round(first_at, 3)
        r.read()
        return r.status
    finally:
        c.close()


def main():
    source = Path(__file__).resolve().parent
    mock = Mock(('127.0.0.1', 18081), Handler)
    threading.Thread(target=mock.serve_forever, daemon=True).start()
    try:
        with tempfile.TemporaryDirectory(prefix='admirra-ai-nginx-test-') as directory:
            tmp = Path(directory)
            proxy = (source / 'proxy.conf').read_text().replace('set $ai_upstream openrouter.ai;', 'set $ai_upstream 127.0.0.1:18081;').replace('proxy_pass https://', 'proxy_pass http://')
            (tmp / 'proxy.conf').write_text(proxy)
            server = (source / 'openrouter.conf').read_text().replace('listen 10.78.0.3:8080;', 'listen 127.0.0.1:18080;').replace('allow 10.78.0.1;', 'allow 127.0.0.1;').replace('/etc/nginx/snippets/admirra-openrouter-proxy.conf', str(tmp / 'proxy.conf')).replace('/var/log/nginx/ai-gateway-access.log', str(tmp / 'access.log')).replace('/var/log/nginx/ai-gateway-error.log', str(tmp / 'error.log'))
            config = tmp / 'nginx.conf'
            config.write_text(f'pid {tmp}/nginx.pid; error_log {tmp}/main-error.log; worker_processes 1; events {{ worker_connections 4096; }} http {{ {server} }}')
            command = ['nginx', '-p', str(tmp), '-c', str(config)]
            subprocess.run(command + ['-t'], check=True)
            subprocess.run(command, check=True)
            try:
                assert request('GET', '/unknown') == 404
                assert request('GET', '/api/v1/chat/completions') == 403
                assert request('POST', '/api/v1/models') == 403
                assert request('POST', '/api/v1/chat/completions', {'X-Test-Fail': 'yes'}) == 503
                assert Handler.failures == 1, 'Gateway retried failed paid request'
                for count in (25, 50, 100):
                    with ThreadPoolExecutor(max_workers=count) as pool:
                        first = list(pool.map(lambda _: request('POST', '/api/v1/chat/completions', stream=True), range(count)))
                    print(json.dumps({'parallel_streams': count, 'passed': len(first), 'max_first_chunk_seconds': max(first)}), flush=True)
                print('PASS: exact paths/methods, upstream errors preserved, no retries, unbuffered SSE at 25/50/100 concurrency')
            finally:
                subprocess.run(command + ['-s', 'quit'], check=True)
                for _ in range(30):
                    if not (tmp / 'nginx.pid').exists():
                        break
                    time.sleep(0.1)
    finally:
        mock.shutdown()
        mock.server_close()


if __name__ == '__main__':
    main()
