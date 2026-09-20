#!/usr/bin/env python3
"""Restricted SSH receiver for encrypted AdMirra backup streams."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import sys


ROOT = Path("/var/lib/admirra-backup/postgres")
COMMAND = re.compile(r"put ([0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}) (database|globals|manifest)\Z")
LIMITS = {
    "database": 4 * 1024 * 1024 * 1024,
    "globals": 64 * 1024 * 1024,
    "manifest": 1024 * 1024,
}


@dataclass(frozen=True)
class Receipt:
    backup_id: str
    kind: str
    size: int
    sha256: str


def parse_command(value: str) -> tuple[str, str]:
    match = COMMAND.fullmatch(value)
    if not match:
        raise ValueError("unsupported backup command")
    return match.group(1), match.group(2)


def _safe_root(root: Path) -> None:
    if root.is_symlink() or not root.is_dir():
        raise RuntimeError("backup repository must be a real directory")
    mode = root.stat().st_mode & 0o777
    if mode & 0o077:
        raise RuntimeError("backup repository must be private")


def receive(root: Path, command: str, stream, limits: dict[str, int] | None = None) -> Receipt:
    backup_id, kind = parse_command(command)
    _safe_root(root)
    limit = (limits or LIMITS)[kind]
    destination = root / f"{backup_id}.{kind}.age"
    partial = root / f".{backup_id}.{kind}.{os.getpid()}.partial"
    if destination.exists():
        raise FileExistsError("backup object already exists")

    digest = hashlib.sha256()
    total = 0
    descriptor = os.open(partial, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as output:
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > limit:
                    raise ValueError("backup object exceeds configured limit")
                digest.update(chunk)
                output.write(chunk)
            if total == 0:
                raise ValueError("empty backup object")
            output.flush()
            os.fsync(output.fileno())
        os.link(partial, destination)
        partial.unlink()
        directory = os.open(root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except BaseException:
        try:
            partial.unlink()
        except FileNotFoundError:
            pass
        raise
    return Receipt(backup_id, kind, total, digest.hexdigest())


def main() -> None:
    command = os.environ.get("SSH_ORIGINAL_COMMAND", "")
    receipt = receive(ROOT, command, sys.stdin.buffer)
    print(f"stored {receipt.kind} bytes={receipt.size} sha256={receipt.sha256}")


if __name__ == "__main__":
    main()
