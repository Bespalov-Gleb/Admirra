"""Gateway-local health check; no API keys or billable generation requests."""
import json
import socket
import subprocess
import time
import urllib.request


def main():
    for unit in ('nginx', 'wg-quick@admirraai', 'admirra-ai-firewall'):
        subprocess.run(['systemctl', 'is-active', '--quiet', unit], check=True)
    handshakes = subprocess.check_output(['wg', 'show', 'admirraai', 'latest-handshakes'], text=True)
    timestamps = [int(line.split()[1]) for line in handshakes.splitlines() if line.strip()]
    if not timestamps or any(stamp == 0 or time.time() - stamp > 360 for stamp in timestamps):
        raise RuntimeError('WireGuard peer handshake is stale')
    with socket.create_connection(('10.78.0.3', 8080), timeout=5):
        pass
    with urllib.request.urlopen('https://openrouter.ai/api/v1/models', timeout=20) as response:
        if response.status != 200:
            raise RuntimeError('OpenRouter catalog unavailable')
        # Check format too, but never emit model payloads or store them.
        payload = response.read(8 * 1024 * 1024)
        if not isinstance(json.loads(payload).get('data'), list):
            raise RuntimeError('Invalid OpenRouter catalog')
    print('OK: gateway services, private listener, upstream TLS and catalog')


if __name__ == '__main__':
    main()
