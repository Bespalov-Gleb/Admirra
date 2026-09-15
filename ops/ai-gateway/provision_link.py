"""Separate AI-only WireGuard interface, no DNS/default route/NAT/DB changes."""
import argparse
import base64
import ipaddress
import json
import os
from pathlib import Path
import subprocess


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepare', action='store_true')
    p.add_argument('--local', choices=['10.78.0.1', '10.78.0.2', '10.78.0.3'])
    p.add_argument('--peer')
    p.add_argument('--public-key')
    p.add_argument('--endpoint')
    a = p.parse_args()
    root = Path('/etc/wireguard')
    root.mkdir(mode=0o700, exist_ok=True)
    key = root / 'admirraai.key'
    conf = root / 'admirraai.conf'
    if a.prepare:
        if not key.exists():
            with os.fdopen(os.open(key, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as f:
                f.write(subprocess.check_output(['wg', 'genkey']))
        print(subprocess.check_output(['wg', 'pubkey'], input=key.read_bytes()).decode().strip())
        return
    if not a.local or a.peer not in ['10.78.0.1', '10.78.0.2', '10.78.0.3'] or a.peer == a.local:
        p.error('Distinct approved local and peer addresses required')
    if len(base64.b64decode(a.public_key, validate=True)) != 32:
        p.error('Invalid public key')
    if not ipaddress.IPv4Address(a.endpoint).is_global:
        p.error('Public peer IPv4 required')
    content = (f'[Interface]\nAddress = {a.local}/32\nListenPort = 51821\nMTU = 1380\n'
               f'PrivateKey = {key.read_text().strip()}\n\n[Peer]\nPublicKey = {a.public_key}\n'
               f'AllowedIPs = {a.peer}/32\nEndpoint = {a.endpoint}:51821\nPersistentKeepalive = 25\n')
    if conf.exists() and conf.read_text() != content:
        raise SystemExit('Existing config differs; refusing overwrite')
    if not conf.exists():
        routes = json.loads(subprocess.check_output(['ip', '-j', 'route']))
        for route in routes:
            if route.get('dst', 'default') == 'default':
                continue
            network = ipaddress.ip_network(route['dst'], strict=False)
            if any(ipaddress.ip_address(ip) in network for ip in (a.local, a.peer)):
                raise SystemExit('Overlapping route; refusing setup')
        with os.fdopen(os.open(conf, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as f:
            f.write(content)
    subprocess.run(['systemctl', 'enable', '--now', 'wg-quick@admirraai'], check=True)
    print('AI-only link enabled; existing links and default route unchanged')


if __name__ == '__main__':
    main()
