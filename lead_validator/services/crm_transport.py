"""One HTTPS POST to a public, DNS-pinned destination; never follow redirects."""
import http.client
import ipaddress
import json
import socket
import ssl
from urllib.parse import urlsplit

from automation.work_errors import RejectedBeforeExternalIO
from core import delivery_outcome


def target(url):
    try:
        parsed = urlsplit(url)
        if (len(url) > 2048 or parsed.scheme != 'https' or not parsed.hostname
                or parsed.username or parsed.password or parsed.fragment or parsed.port not in (None, 443)
                or any(ord(c) < 32 for c in url)):
            raise ValueError('Invalid target')
        host = parsed.hostname.encode('idna').decode('ascii')
        return host, (parsed.path or '/') + ('?' + parsed.query if parsed.query else '')
    except Exception:
        raise RejectedBeforeExternalIO('CRM requires a public HTTPS endpoint on port 443') from None


def public_address(address):
    ip = ipaddress.ip_address(address)
    ip = getattr(ip, 'ipv4_mapped', None) or ip
    return ip.is_global and not ip.is_multicast


def post(url, payload):
    delivery_outcome.rejected()
    host, path = target(url)
    addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not public_address(item[4][0]) for item in addresses):
        raise RejectedBeforeExternalIO('CRM destination is not public')
    # Only one connect attempt, using the already verified IP. TLS SNI and the
    # certificate check use the original hostname, not the IP address.
    address = addresses[0][4][0]
    context = ssl.create_default_context()
    class PinnedHTTPS(http.client.HTTPSConnection):
        def connect(self):
            raw = socket.create_connection((address, 443), timeout=self.timeout)
            try:
                self.sock = context.wrap_socket(raw, server_hostname=host)
            except BaseException:
                raw.close()
                raise
    connection = PinnedHTTPS(host, port=443, timeout=10, context=context)
    try:
        connection.connect()
        body = json.dumps(payload, ensure_ascii=False).encode()
        delivery_outcome.before_send()
        connection.request('POST', path, body=body, headers={'Content-Type': 'application/json',
            'Idempotency-Key': payload['lead_id']})
        response = connection.getresponse()
        if 400 <= response.status < 500:
            delivery_outcome.rejected()
        return 200 <= response.status < 300
    finally:
        connection.close()
