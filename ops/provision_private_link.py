"""Dedicated host-to-host WireGuard link; no default route, DNS or firewall edits.

Private keys are generated and kept on each host (0600), never in git/output.
Run --prepare on each host, then exchange only the public keys using --configure.
"""
import argparse
import base64
import ipaddress
import json
import os
from pathlib import Path
import shutil
import subprocess

DIRECTORY = Path("/etc/wireguard")
KEY = DIRECTORY / "admirra0.key"
CONFIG = DIRECTORY / "admirra0.conf"


def run(*args):
    return subprocess.run(args, check=True, env={**os.environ, "DEBIAN_FRONTEND": "noninteractive", "NEEDRESTART_MODE": "l"})


def configuration(local, peer, endpoint, private, public):
    local_ip, peer_ip = ipaddress.ip_address(local), ipaddress.ip_address(peer)
    endpoint_ip = ipaddress.ip_address(endpoint)
    private_networks = [ipaddress.ip_network(cidr) for cidr in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")]
    if local_ip.version != 4 or peer_ip.version != 4 or local_ip == peer_ip or not all(
        any(address in network for network in private_networks) for address in (local_ip, peer_ip)
    ):
        raise ValueError("Distinct private IPv4 host addresses required")
    if endpoint_ip.version != 4 or not endpoint_ip.is_global:
        raise ValueError("A public IPv4 peer endpoint is required")
    for key in (private, public):
        if len(base64.b64decode(key, validate=True)) != 32:
            raise ValueError("Invalid WireGuard key")
    return (f"[Interface]\nAddress = {local_ip}/32\nListenPort = 51820\nMTU = 1420\nPrivateKey = {private}\n\n"
            f"[Peer]\nPublicKey = {public}\nAllowedIPs = {peer_ip}/32\nEndpoint = {endpoint_ip}:51820\nPersistentKeepalive = 25\n")


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare", action="store_true")
    group.add_argument("--configure", action="store_true")
    parser.add_argument("--local")
    parser.add_argument("--peer")
    parser.add_argument("--endpoint")
    parser.add_argument("--public-key")
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise SystemExit("Root required")
    if args.prepare:
        if not shutil.which("wg"):
            run("apt-get", "update", "-qq")
            run("apt-get", "install", "-y", "--no-install-recommends", "wireguard-tools")
        DIRECTORY.mkdir(mode=0o700, exist_ok=True)
        if not KEY.exists():
            private = subprocess.check_output(["wg", "genkey"])
            fd = os.open(KEY, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(private)
        public = subprocess.check_output(["wg", "pubkey"], input=KEY.read_bytes()).decode().strip()
        print(json.dumps({"interface": "admirra0", "public_key": public}))
        return
    if not all((args.local, args.peer, args.endpoint, args.public_key)) or not KEY.exists():
        raise SystemExit("Prepare keys first; all peer options are required")
    content = configuration(args.local, args.peer, args.endpoint, KEY.read_text().strip(), args.public_key)
    if CONFIG.exists() and CONFIG.read_text() != content:
        raise SystemExit("Existing configuration differs; refusing to overwrite")
    if not CONFIG.exists():
        routes = json.loads(subprocess.check_output(["ip", "-j", "route"], text=True))
        for route in routes:
            if route.get("dst", "default") != "default":
                network = ipaddress.ip_network(route["dst"], strict=False)
                if any(ipaddress.ip_address(address) in network for address in (args.local, args.peer)):
                    raise SystemExit("Private link overlaps an existing route")
        fd = os.open(CONFIG, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.write(content)
    run("systemctl", "enable", "--now", "wg-quick@admirra0")
    print("Dedicated private link enabled; default route/SSH/firewall unchanged")


if __name__ == "__main__":
    main()
