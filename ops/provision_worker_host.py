"""Bootstrap Docker on the explicitly selected NEW Ubuntu 24.04 worker host.

Run via SSH stdin. Does not touch production, SSH authentication, partitions,
firewall policy or existing Docker installations. No curl|shell scripts.
"""
import os
from pathlib import Path
import shutil
import subprocess


def run(*args):
    subprocess.run(args, check=True, env={**os.environ, "DEBIAN_FRONTEND": "noninteractive"})


def main():
    if os.geteuid() != 0:
        raise SystemExit("Run as root on the new worker host")
    release = dict(line.split("=", 1) for line in Path("/etc/os-release").read_text().splitlines() if "=" in line)
    if release.get("ID", "").strip('"') != "ubuntu" or release.get("VERSION_ID", "").strip('"') != "24.04":
        raise SystemExit("This bootstrap supports Ubuntu 24.04 only")
    if shutil.which("docker"):
        run("docker", "version", "--format", "{{.Server.Version}}")
        return
    run("apt-get", "update", "-qq")
    run("apt-get", "install", "-y", "--no-install-recommends", "ca-certificates", "curl")
    Path("/etc/apt/keyrings").mkdir(mode=0o755, exist_ok=True)
    key = "/etc/apt/keyrings/docker.asc"
    run("curl", "-fsSL", "--proto", "=https", "https://download.docker.com/linux/ubuntu/gpg", "-o", key)
    os.chmod(key, 0o644)
    architecture = subprocess.check_output(["dpkg", "--print-architecture"], text=True).strip()
    source = Path("/etc/apt/sources.list.d/docker.sources")
    if source.exists():
        raise SystemExit("Existing Docker apt source: review it manually before bootstrap")
    source.write_text(
        "Types: deb\nURIs: https://download.docker.com/linux/ubuntu\n"
        f"Suites: noble\nComponents: stable\nArchitectures: {architecture}\nSigned-By: {key}\n"
    )
    run("apt-get", "update", "-qq")
    # Match the current host's major/minor package if available; explicit pin.
    version = "5:29.6.1-1~ubuntu.24.04~noble"
    run("apt-get", "install", "-y", "--no-install-recommends",
        f"docker-ce={version}", f"docker-ce-cli={version}",
        "containerd.io", "docker-buildx-plugin", "docker-compose-plugin")
    run("docker", "version", "--format", "{{.Server.Version}}")
    run("docker", "compose", "version")


if __name__ == "__main__":
    main()
