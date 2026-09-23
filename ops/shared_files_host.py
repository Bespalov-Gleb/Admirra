"""Private legacy-file bridge; additive install only, no app restarts.

New report objects use mTLS, not NFS. Legacy uploads retain paths and URLs.
Run guard before installing nfs-kernel-server/nfs-common. No public exports.
"""
import argparse
import os
from pathlib import Path
import subprocess

from ops.private_firewall import install
from ops.private_redis import write_once

PORTS = "111,2049,20048,9443"


def firewall_rules(ipv6=False, node="1"):
    local, peer = ("10.77.0.1", "10.77.0.2") if node == "1" else ("10.77.0.2", "10.77.0.1")
    incoming = [["-i", "lo", "-j", "ACCEPT"]]
    forward = []
    if not ipv6:
        incoming.append(["-s", peer + "/32", "-d", local + "/32", "-i", "admirra0", "-j", "ACCEPT"])
        forward.append(["-s", peer + "/32", "-i", "admirra0", "-j", "RETURN"])
        # Private local artifact smoke clients on API1 Docker bridges.
        incoming.append(["-s", "172.16.0.0/12", "-d", "10.77.0.1/32", "-i", "br+", "-p", "tcp", "--dport", "9443", "-j", "ACCEPT"])
    incoming.append(["-j", "DROP"])
    forward.extend([["-i", "eth0", "-j", "DROP"], ["-i", "admirra0", "-j", "DROP"], ["-j", "RETURN"]])
    hooks = []
    for proto in ("tcp", "udp"):
        hooks += [("INPUT", ["-p", proto, "-m", "multiport", "--dports", PORTS, "-j", "ADMR-FILES-IN"]),
                  ("DOCKER-USER", ["-p", proto, "-m", "multiport", "--dports", PORTS,
                                   "-m", "conntrack", "--ctdir", "ORIGINAL", "-j", "ADMR-FILES-FWD"])]
    hooks.append(("DOCKER-USER", ["-i", "admrfiles0", "-m", "conntrack", "--ctstate", "NEW", "-j", "DROP"]))
    return {"ADMR-FILES-IN": incoming, "ADMR-FILES-FWD": forward}, hooks


def server_files():
    return {
        "/etc/nfs.conf.d/admirra.conf": "[nfsd]\nhost=10.77.0.1\nvers3=n\nvers4=y\nvers4.0=n\nvers4.1=y\nvers4.2=y\nudp=n\ntcp=y\nthreads=4\n[mountd]\nport=20048\n",
        "/etc/exports.d/admirra.exports": (
            "/srv/admirra/shared 10.77.0.2(ro,sync,fsid=0,no_subtree_check,all_squash,anonuid=10001,anongid=10001)\n"
            "/srv/admirra/shared/uploads 10.77.0.2(rw,sync,fsid=1,no_subtree_check,all_squash,anonuid=10001,anongid=10001)\n"
            "/srv/admirra/shared/rejected-leads 10.77.0.2(rw,sync,fsid=2,no_subtree_check,all_squash,anonuid=10001,anongid=10001)\n"),
        "/etc/systemd/system/srv-admirra-shared-uploads.mount": (
            "[Unit]\nDescription=AdMirra existing uploads (same inode, no copy)\nBefore=nfs-server.service\n"
            "[Mount]\nWhat=/root/Admirra/uploads\nWhere=/srv/admirra/shared/uploads\nType=none\nOptions=bind\n"
            "[Install]\nWantedBy=multi-user.target\n"),
        "/etc/systemd/system/srv-admirra-shared-rejected\\x2dleads.mount": (
            "[Unit]\nDescription=AdMirra private rejected-lead files\nBefore=nfs-server.service\n"
            "[Mount]\nWhat=/srv/admirra/rejected-leads\nWhere=/srv/admirra/shared/rejected-leads\nType=none\nOptions=bind\n"
            "[Install]\nWantedBy=multi-user.target\n"),
        "/etc/systemd/system/nfs-server.service.d/admirra.conf": (
            "[Unit]\nRequires=wg-quick@admirra0.service srv-admirra-shared-uploads.mount srv-admirra-shared-rejected\\x2dleads.mount admirra-files-firewall.service\n"
            "After=wg-quick@admirra0.service srv-admirra-shared-uploads.mount srv-admirra-shared-rejected\\x2dleads.mount admirra-files-firewall.service\n"),
        "/etc/systemd/system/admirra-files-firewall.service": (
            "[Unit]\nDescription=Guard private AdMirra file ports\nRequires=docker.service wg-quick@admirra0.service\n"
            "After=docker.service wg-quick@admirra0.service\nBefore=nfs-server.service\nPartOf=docker.service\n"
            "[Service]\nType=oneshot\nRemainAfterExit=yes\nWorkingDirectory=/opt/admirra-file-ops\n"
            "ExecStart=/usr/bin/python3 -m ops.shared_files_host guard\n[Install]\nWantedBy=multi-user.target docker.service\n"),
    }


def client_files():
    return {
        "/etc/systemd/system/admirra-client-files-firewall.service": (
            "[Unit]\nDescription=Guard AdMirra NFS client RPC ports\nRequires=docker.service wg-quick@admirra0.service\n"
            "After=docker.service wg-quick@admirra0.service\nPartOf=docker.service\n"
            "[Service]\nType=oneshot\nRemainAfterExit=yes\nWorkingDirectory=/opt/admirra-file-ops\n"
            "ExecStart=/usr/bin/python3 -m ops.shared_files_host guard --node 2\n"
            "[Install]\nWantedBy=multi-user.target docker.service\n"),
        "/etc/systemd/system/srv-admirra-shared.mount": (
            "[Unit]\nDescription=AdMirra legacy files over private WireGuard\n"
            "Requires=wg-quick@admirra0.service\nAfter=wg-quick@admirra0.service network-online.target\n"
            "[Mount]\nWhat=10.77.0.1:/\nWhere=/srv/admirra/shared\nType=nfs4\n"
            "Options=vers=4.2,proto=tcp,hard,timeo=600,retrans=2,nosuid,nodev,noexec\nTimeoutSec=30\n"
            "[Install]\nWantedBy=multi-user.target\n"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("guard", "server-config", "client-config"))
    parser.add_argument("--node", choices=("1", "2"), default="1")
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise SystemExit("Root required")
    if args.action == "guard":
        for binary, ipv6 in (("iptables", False), ("ip6tables", True)):
            install(binary, *firewall_rules(ipv6, args.node))
        print("Private file ingress guarded; SSH/web policies unchanged")
        return
    files = server_files() if args.action == "server-config" else client_files()
    for name, content in files.items():
        path = Path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and not path.is_symlink() and path.read_text() == content:
            path.chmod(0o644)
        write_once(path, content, 0o644)
        path.chmod(0o644)
    root = Path("/srv/admirra/shared")
    root.mkdir(parents=True, exist_ok=True)
    if args.action == "server-config":
        root.chmod(0o755)  # NFS maps even client root to uid 10001.
        (root / "uploads").mkdir(exist_ok=True)
        rejected = root / "rejected-leads"
        rejected.mkdir(mode=0o770, exist_ok=True)
        os.chown(rejected, 10001, 10001)
        source = Path("/srv/admirra/rejected-leads")
        source.mkdir(mode=0o770, exist_ok=True)
        os.chown(source, 10001, 10001)
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    print("Shared-file configuration installed; application services unchanged")


if __name__ == "__main__":
    main()
