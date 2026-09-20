"""Add only the approved API-2 peer to a running gateway without restarting it.

Private configuration stays on the gateway. Existing peers are never replaced.
See wg(8): `set ... peer` changes only the specified peer, unlike setconf.
"""
import argparse
import base64
import fcntl
import ipaddress
import json
import os
from pathlib import Path
import subprocess
import tempfile

INTERFACE = "admirraai"
ADDRESS = "10.78.0.2/32"
ENDPOINT = "91.221.68.94:51821"
ROOT = Path("/etc/wireguard")


def plan(original, public_key):
    try:
        valid = len(base64.b64decode(public_key, validate=True)) == 32
    except (ValueError, TypeError):
        valid = False
    if not valid:
        raise ValueError("Invalid public key")
    sections = []
    for line in original.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        if line in ("[Interface]", "[Peer]"):
            sections.append((line, {}))
        elif "=" in line and sections:
            name, value = (part.strip() for part in line.split("=", 1))
            if name in sections[-1][1]:
                raise ValueError("Duplicate configuration field")
            sections[-1][1][name] = value
        else:
            raise ValueError("Unexpected configuration syntax")
    interfaces = [fields for kind, fields in sections if kind == "[Interface]"]
    if len(interfaces) != 1 or interfaces[0].get("Address") != "10.78.0.3/32":
        raise ValueError("This command is only for the approved AI gateway")
    if interfaces[0].get("SaveConfig", "false").lower() != "false":
        raise ValueError("SaveConfig must not overwrite the managed configuration")
    peers = [fields for kind, fields in sections if kind == "[Peer]"]
    if not any(peer.get("AllowedIPs") == "10.78.0.1/32" for peer in peers):
        raise ValueError("Existing API-1 peer is required")
    expected = {"PublicKey": public_key, "AllowedIPs": ADDRESS,
                "Endpoint": ENDPOINT, "PersistentKeepalive": "25"}
    for peer in peers:
        networks = [ipaddress.ip_network(value.strip())
                    for value in peer.get("AllowedIPs", "").split(",") if value.strip()]
        overlaps = any(ipaddress.ip_address("10.78.0.2") in net for net in networks)
        if peer.get("PublicKey") == public_key or overlaps:
            if peer != expected:
                raise ValueError("Existing key/address conflicts with API-2; refusing replacement")
            return original, peers
    addition = "\n[Peer]\n" + "".join(f"{key} = {value}\n" for key, value in expected.items())
    return original.rstrip() + "\n" + addition, peers


def atomic_write(path, content):
    fd, temp = tempfile.mkstemp(prefix=".admirraai-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            os.fchmod(handle.fileno(), 0o600)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
        directory = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def run(*command):
    return subprocess.check_output(command, text=True, stderr=subprocess.PIPE).strip()


def apply(public_key):
    path = ROOT / f"{INTERFACE}.conf"
    original = path.read_text()
    candidate, peers = plan(original, public_key)
    live = dict(line.split(None, 1) for line in run("wg", "show", INTERFACE, "allowed-ips").splitlines())
    expected = {peer["PublicKey"]: peer["AllowedIPs"] for peer in peers}
    # A persisted new peer may be absent after interruption before `wg set`.
    expected.pop(public_key, None)
    others = {key: value for key, value in live.items() if key != public_key}
    if others != expected or (public_key in live and live[public_key] != ADDRESS):
        raise ValueError("Runtime peers differ from configuration; refusing automatic repair")
    routes = json.loads(run("ip", "-j", "route"))
    route_exists = False
    for route in routes:
        if route.get("dst", "default") == "default":
            continue
        network = ipaddress.ip_network(route["dst"], strict=False)
        if ipaddress.ip_address("10.78.0.2") in network:
            if str(network) != ADDRESS or route.get("dev") != INTERFACE or route.get("gateway"):
                raise ValueError("Overlapping route; refusing modification")
            route_exists = True
    backup = ROOT / "admirraai.before-api2.conf"
    if candidate != original:
        # Exclusive creation retains the original pre-change recovery file.
        with backup.open("x") as handle:
            os.fchmod(handle.fileno(), 0o600)
            handle.write(original)
            handle.flush()
            os.fsync(handle.fileno())
        atomic_write(path, candidate)
    # Only this new peer is changed. No setconf, interface/service restart,
    # firewall, default route, or API-1 peer update.
    run("wg", "set", INTERFACE, "peer", public_key, "allowed-ips", ADDRESS,
        "endpoint", ENDPOINT, "persistent-keepalive", "25")
    if not route_exists:
        run("ip", "route", "add", ADDRESS, "dev", INTERFACE)
    after = dict(line.split(None, 1) for line in run("wg", "show", INTERFACE, "allowed-ips").splitlines())
    if after != {**expected, public_key: ADDRESS}:
        raise ValueError("Unexpected peer state after update")
    print("API-2 peer persisted and enabled; API-1 peer preserved; no restart")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-key", required=True)
    args = parser.parse_args()
    try:
        with (ROOT / ".admirraai-api2.lock").open("a") as lock:
            os.fchmod(lock.fileno(), 0o600)
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            apply(args.public_key)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        # Never dump configuration, captured command stderr, or traceback locals.
        raise SystemExit(f"Peer setup stopped ({type(error).__name__}); inspect protected config and retry. No existing peer removed.") from None


if __name__ == "__main__":
    main()
