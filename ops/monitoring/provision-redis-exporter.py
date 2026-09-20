#!/usr/bin/env python3
"""Prepare redis_exporter password maps without exposing Redis credentials."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile


SOURCE = Path("/etc/admirra/redis-credentials.json")
DESTINATION = Path("/etc/admirra/monitoring")
TARGETS = {
    # redis_exporter rewrites the lookup URI with REDIS_USER before reading
    # PasswordMap, so the ACL username is part of the exact map key.
    "redis_broker_passwords.json": "redis://monitor@10.77.0.2:6379",
    "redis_cache_passwords.json": "redis://monitor@10.77.0.2:6380",
}


def atomic_secret(path: Path, value: str) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(descriptor, 0o400)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.chown(temporary, 59000, 59000)
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def main() -> None:
    if os.geteuid() != 0:
        raise SystemExit("root required")
    credentials = json.loads(SOURCE.read_text(encoding="utf-8"))
    password = credentials.get("monitor")
    if not isinstance(password, str) or len(password) < 40:
        raise RuntimeError("monitor credential is missing or invalid")
    DESTINATION.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(DESTINATION, 0o700)
    for filename, address in TARGETS.items():
        atomic_secret(DESTINATION / filename, json.dumps({address: password}))
    print("redis_exporter credentials prepared; no secrets emitted")


if __name__ == "__main__":
    main()
