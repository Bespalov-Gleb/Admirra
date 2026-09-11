"""Narrow additive guards for database/Redis ports; never changes SSH policy.

Protect INPUT and Docker forwarding (UFW alone does not protect published ports).
Run after Docker and WireGuard; safe to repeat. Does not flush existing rules,
modify default policies, or touch ports 22/80/443/8001/8080.
"""
import argparse
import json
import os
import subprocess

PORTS = "5432,6379,6380"


def rules(local, peer, public_interface, ipv6=False):
    incoming = [["-i", "lo", "-j", "ACCEPT"]]
    forward = []
    if not ipv6:
        incoming.append(["-s", peer + "/32", "-d", local + "/32", "-i", "admirra0", "-j", "ACCEPT"])
        forward.append(["-s", peer + "/32", "-i", "admirra0", "-j", "RETURN"])
    incoming.append(["-j", "DROP"])
    forward.extend([["-i", public_interface, "-j", "DROP"],
                    ["-i", "admirra0", "-j", "DROP"], ["-j", "RETURN"]])
    hooks = [("INPUT", ["-p", "tcp", "-m", "multiport", "--dports", PORTS, "-j", "ADMR-PRIV-IN"]),
             ("DOCKER-USER", ["-p", "tcp", "-m", "multiport", "--dports", PORTS,
                              "-m", "conntrack", "--ctdir", "ORIGINAL", "-j", "ADMR-PRIV-FWD"])]
    return {"ADMR-PRIV-IN": incoming, "ADMR-PRIV-FWD": forward}, hooks


def command(binary, *args, check=True):
    return subprocess.run([binary, "-w", "5", *args], check=check, capture_output=True, text=True)


def install(binary, chains, hooks):
    # Require Docker's chain: do not guess the host firewall backend.
    command(binary, "-S", "DOCKER-USER")
    for chain, entries in chains.items():
        existing = command(binary, "-S", chain, check=False)
        if existing.returncode:
            command(binary, "-N", chain)
            present = []
        else:
            present = [line for line in existing.stdout.splitlines() if line.startswith("-A ")]
        if present:
            if len(present) != len(entries) or any(command(binary, "-C", chain, *row, check=False).returncode for row in entries):
                raise RuntimeError("Existing private firewall rules differ; review before changing")
            if not present[-1].endswith("-j " + entries[-1][-1]):
                raise RuntimeError("Unexpected firewall rule order")
        else:
            for entry in entries:
                command(binary, "-A", chain, *entry)
    for chain, entry in hooks:
        if command(binary, "-C", chain, *entry, check=False).returncode:
            command(binary, "-I", chain, "1", *entry)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node", choices=("1", "2"), required=True)
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise SystemExit("Root required")
    local, peer = ("10.77.0.1", "10.77.0.2") if args.node == "1" else ("10.77.0.2", "10.77.0.1")
    addresses = json.loads(subprocess.check_output(["ip", "-j", "address", "show", "admirra0"], text=True))
    if not any(info.get("local") == local for iface in addresses for info in iface.get("addr_info", [])):
        raise SystemExit("Expected private address is not active")
    routes = json.loads(subprocess.check_output(["ip", "-j", "route", "show", "default"], text=True))
    interfaces = {route["dev"] for route in routes}
    if len(interfaces) != 1:
        raise SystemExit("Expected exactly one public interface")
    interface = interfaces.pop()
    for binary, ipv6 in (("iptables", False), ("ip6tables", True)):
        chains, hooks = rules(local, peer, interface, ipv6)
        install(binary, chains, hooks)
    print("Private DB/Redis ingress guarded on IPv4 and IPv6; SSH/web/default policies unchanged")


if __name__ == "__main__":
    main()
