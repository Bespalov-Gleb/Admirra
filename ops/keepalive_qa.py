"""Isolated loopback Nginx instance proves idle retirement, not incident reproduction."""
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import threading
import time


def main():
    assert os.environ.get('WW_TEST') == '1' and os.environ.get('WW_TEST_ID')

    class Handler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def do_GET(self):
            body = json.dumps({'peer_port': self.client_address[1]}).encode()
            self.send_response(200)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    backend = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=backend.serve_forever, daemon=True).start()
    process = None
    connection = None
    try:
        with tempfile.TemporaryDirectory(prefix='admirra-keepalive-qa-') as tmp:
            root = Path(tmp)
            with socket.socket() as s:
                s.bind(('127.0.0.1', 0))
                port = s.getsockname()[1]
            config = f'''worker_processes 1;
pid {root}/nginx.pid;
error_log {root}/error.log;
events {{ worker_connections 32; }}
http {{
    access_log off;
    # Ubuntu's compiled defaults are absolute; -p alone does not isolate them.
    client_body_temp_path {root}/body;
    proxy_temp_path {root}/proxy;
    fastcgi_temp_path {root}/fastcgi;
    uwsgi_temp_path {root}/uwsgi;
    scgi_temp_path {root}/scgi;
    upstream test_backend {{
        server 127.0.0.1:{backend.server_address[1]};
        keepalive 16;
        keepalive_timeout 3s;
    }}
    server {{
        listen 127.0.0.1:{port};
        location / {{
            proxy_pass http://test_backend;
            proxy_http_version 1.1;
            proxy_set_header Connection "";
            proxy_next_upstream off;
        }}
    }}
}}'''
            (root / 'nginx.conf').write_text(config)
            process = subprocess.Popen(['nginx', '-p', tmp, '-c', str(root / 'nginx.conf'), '-g', 'daemon off;'])
            for _ in range(50):
                try:
                    with socket.create_connection(('127.0.0.1', port), timeout=.1):
                        break
                except OSError:
                    if process.poll() is not None:
                        raise RuntimeError('Isolated nginx failed')
                    time.sleep(.1)
            connection = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
            def read():
                connection.request('GET', '/')
                response = connection.getresponse()
                assert response.status == 200
                return json.loads(response.read())['peer_port']
            first = read()
            time.sleep(.25)
            assert read() == first, 'Active pooled socket should be reused'
            time.sleep(4)
            assert read() != first, 'Idle pooled socket must retire before backend 5s timeout'
            print('PASS: short-idle connection reused; at 4s new upstream socket; no retries; all HTTP 200')
    finally:
        if connection:
            connection.close()
        if process:
            process.terminate()
            process.wait(timeout=5)
        backend.shutdown()
        backend.server_close()


if __name__ == '__main__':
    main()
