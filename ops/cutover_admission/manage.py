#!/usr/bin/env python3
"""Install and switch the Nginx cutover admission gate atomically."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


INCLUDE = "    include /etc/nginx/snippets/admirra-cutover-admission.conf;"
ANCHOR = "    client_max_body_size 20m;"
DEFAULT_SITES = (
    Path("/etc/nginx/sites-enabled/admirra.ru"),
    Path("/etc/nginx/sites-enabled/admirra.online"),
)
ACTIVE_MAP = Path("/etc/nginx/conf.d/admirra-cutover-map.conf")
ACTIVE_SNIPPET = Path("/etc/nginx/snippets/admirra-cutover-admission.conf")
ACTIVE_STATE = Path("/var/lib/admirra-cutover-admission/state.json")


def patch_site(text: str) -> str:
    count = text.count(INCLUDE.strip())
    if count == 1:
        return text
    if count:
        raise ValueError("cutover admission include is duplicated")
    if text.count(ANCHOR) != 1:
        raise ValueError("expected exactly one HTTPS client_max_body_size anchor")
    return text.replace(ANCHOR, ANCHOR + "\n" + INCLUDE, 1)


def atomic_write(path: Path, data: bytes, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def nginx(command: tuple[str, ...]) -> None:
    result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=20)
    if result.returncode:
        raise RuntimeError("Nginx validation or reload failed")


def _snapshot(paths: list[Path]) -> dict[Path, tuple[bytes, int] | None]:
    saved = {}
    for path in paths:
        resolved = path.resolve(strict=False)
        if resolved.exists():
            saved[resolved] = (resolved.read_bytes(), resolved.stat().st_mode & 0o777)
        else:
            saved[resolved] = None
    return saved


def _restore(saved: dict[Path, tuple[bytes, int] | None]) -> None:
    for path, state in saved.items():
        if state is None:
            if path.exists():
                path.unlink()
        else:
            atomic_write(path, state[0], state[1])


def transact(writes: dict[Path, tuple[bytes, int]], *, validate_only: bool = False) -> None:
    targets = [path.resolve(strict=False) for path in writes]
    saved = _snapshot(targets)
    try:
        for path, (data, mode) in writes.items():
            atomic_write(path.resolve(strict=False), data, mode)
        nginx(("nginx", "-t"))
        if not validate_only:
            nginx(("systemctl", "reload", "nginx"))
    except Exception:
        _restore(saved)
        try:
            nginx(("nginx", "-t"))
            if not validate_only:
                nginx(("systemctl", "reload", "nginx"))
        except Exception:
            pass
        raise


def release_files(root: Path) -> tuple[Path, Path, Path]:
    return (
        root / "admirra-cutover-map.open.conf",
        root / "admirra-cutover-map.closed.conf",
        root / "admirra-cutover-admission.conf",
    )


def preserve_install_backup(sites: tuple[Path, ...]) -> Path:
    backup_root = Path(os.getenv("ADMIRRA_CUTOVER_BACKUP_DIR", "/root/admirra-cutover-admission-backups"))
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = backup_root / stamp
    backup.mkdir(parents=True, mode=0o700, exist_ok=False)
    os.chmod(backup, 0o700)
    for index, site in enumerate(sites, start=1):
        resolved = site.resolve(strict=True)
        shutil.copy2(resolved, backup / f"site-{index}.conf")
    for name, path in (
        ("active-map.conf", ACTIVE_MAP),
        ("active-snippet.conf", ACTIVE_SNIPPET),
        ("active-state.json", ACTIVE_STATE),
    ):
        if path.exists():
            shutil.copy2(path.resolve(), backup / name)
    (backup / "paths.txt").write_text("\n".join(str(site.resolve()) for site in sites) + "\n")
    os.chmod(backup / "paths.txt", 0o600)
    return backup


def state_payload(mode: str, now: dt.datetime | None = None) -> bytes:
    if mode not in {"open", "closed"}:
        raise ValueError("invalid admission mode")
    now = (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)
    return (json.dumps(
        {
            "format": "admirra-cutover-admission-v1",
            "mode": mode,
            "switched_at": now.isoformat().replace("+00:00", "Z"),
        },
        sort_keys=True,
    ) + "\n").encode()


def install(root: Path, sites: tuple[Path, ...]) -> Path:
    open_map, _, snippet = release_files(root)
    for path in (open_map, snippet, *sites):
        if not path.exists():
            raise ValueError("required admission-gate file is missing")
    backup = preserve_install_backup(sites)
    writes: dict[Path, tuple[bytes, int]] = {
        ACTIVE_MAP: (open_map.read_bytes(), 0o644),
        ACTIVE_SNIPPET: (snippet.read_bytes(), 0o644),
        ACTIVE_STATE: (state_payload("open"), 0o644),
    }
    for site in sites:
        resolved = site.resolve(strict=True)
        writes[resolved] = (patch_site(resolved.read_text()).encode(), resolved.stat().st_mode & 0o777)
    transact(writes)
    return backup


def set_mode(root: Path, mode: str) -> None:
    open_map, closed_map, _ = release_files(root)
    source = open_map if mode == "open" else closed_map
    if not source.is_file() or not ACTIVE_SNIPPET.is_file():
        raise ValueError("admission gate is not installed")
    transact({
        ACTIVE_MAP: (source.read_bytes(), 0o644),
        ACTIVE_STATE: (state_payload(mode), 0o644),
    })


def current_mode(root: Path) -> str:
    open_map, closed_map, _ = release_files(root)
    try:
        active = ACTIVE_MAP.read_bytes()
    except OSError:
        return "not-installed"
    if active == open_map.read_bytes():
        return "open"
    if active == closed_map.read_bytes():
        return "closed"
    return "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "open", "closed", "status"))
    parser.add_argument("--site", action="append", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    if args.action == "status":
        print(current_mode(root))
        return 0
    if os.geteuid() != 0:
        raise SystemExit("cutover admission changes require root")
    try:
        if args.action == "install":
            backup = install(root, tuple(args.site or DEFAULT_SITES))
        else:
            set_mode(root, args.action)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
        raise SystemExit("cutover admission change failed and was rolled back") from None
    print(f"install backup={backup}" if args.action == "install" else args.action)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
