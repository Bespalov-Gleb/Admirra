"""Transfer only the selected service env over SSH pipes, never local files/output."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlsplit

from ops.private_redis import write_once


def validate(kind, content):
    lines = [line for line in content.splitlines() if line]
    rows = dict(line.split("=", 1) for line in lines)
    if len(rows) != len(lines):
        raise ValueError("Duplicate environment keys")
    if kind == "db-worker":
        if set(rows) != {"DATABASE_URL"}:
            raise ValueError("Unexpected database environment")
        url = urlsplit(rows["DATABASE_URL"])
        if (url.scheme, url.hostname, url.port, url.username, url.path) != (
            "postgresql", "10.77.0.1", 5432, "admirra_worker", "/saas_project"
        ) or len(url.password or "") < 40:
            raise ValueError("Unexpected database destination")
    elif kind == "redis-api":
        if set(rows) != {"CELERY_BROKER_URL", "RATE_LIMIT_REDIS_URL", "READ_CACHE_REDIS_URL", "TASK_BROKER_PREFIX"}:
            raise ValueError("Unexpected Redis environment")
        for key, user, port in (("CELERY_BROKER_URL", "broker_api", 6379),
                                ("RATE_LIMIT_REDIS_URL", "limiter_api", 6379),
                                ("READ_CACHE_REDIS_URL", "cache_api", 6380)):
            url = urlsplit(rows[key])
            if (url.scheme, url.hostname, url.port, url.username, url.path) != (
                "redis", "10.77.0.2", port, user, "/0"
            ) or len(url.password or "") < 40:
                raise ValueError("Unexpected Redis destination")
        if rows["TASK_BROKER_PREFIX"] != "admirra:task:":
            raise ValueError("Unexpected broker namespace")
    else:
        raise ValueError("Unknown service environment")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("transfer", "receive"))
    parser.add_argument("kind", choices=("db-worker", "redis-api"))
    args = parser.parse_args()
    if args.action == "receive":
        if os.geteuid() != 0:
            raise SystemExit("Root required")
        content = sys.stdin.read(8193)
        if len(content) > 8192:
            raise SystemExit("Unexpected environment size")
        validate(args.kind, content)
        root = Path("/etc/admirra")
        if root.is_symlink() or root.stat().st_mode & 0o077 or root.stat().st_uid != os.geteuid():
            raise SystemExit("Private directory required")
        write_once(root / (args.kind + ".env"), content, 0o600)
        print("Service environment installed privately; no application restarted")
        return
    first = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "root@91.221.68.90"]
    second = ["ssh", "-o", "BatchMode=yes", "-S", "/private/tmp/admirra-devops-worker-ssh", "root@91.221.68.94"]
    source, target = (first, second) if args.kind == "db-worker" else (second, first)
    destination = "/opt/admirra-ops"
    # Both endpoints are owner-provided servers. No file is written locally;
    # secrets never appear in a command argument, environment dump or tool output.
    content = subprocess.check_output([*source, "cat /etc/admirra/" + args.kind + ".env"])
    validate(args.kind, content.decode())
    subprocess.run([*target, f"cd {destination} && python3 -m ops.service_credentials receive {args.kind}"],
                   input=content, check=True)


if __name__ == "__main__":
    main()
