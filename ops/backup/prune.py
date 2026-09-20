#!/usr/bin/env python3
"""Bounded retention for complete encrypted logical backup sets."""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path
import re


OBJECT = re.compile(
    r"(?P<id>[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8})\.(?P<kind>database|globals|manifest)\.age\Z"
)
KINDS = {"database", "globals", "manifest"}


def backup_time(backup_id: str) -> dt.datetime:
    return dt.datetime.strptime(backup_id[:16], "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc)


def inventory(root: Path) -> dict[str, dict[str, Path]]:
    result: dict[str, dict[str, Path]] = {}
    for path in root.iterdir():
        if not path.is_file() or path.is_symlink():
            continue
        match = OBJECT.fullmatch(path.name)
        if match:
            result.setdefault(match.group("id"), {})[match.group("kind")] = path
    return result


def retention_set(complete: list[str], daily: int = 7, weekly: int = 4, monthly: int = 3) -> set[str]:
    ordered = sorted(complete, key=backup_time, reverse=True)
    keep: set[str] = set()
    for limit, key in (
        (daily, lambda value: value.date()),
        (weekly, lambda value: value.isocalendar()[:2]),
        (monthly, lambda value: (value.year, value.month)),
    ):
        buckets = set()
        for backup_id in ordered:
            bucket = key(backup_time(backup_id))
            if bucket in buckets or len(buckets) >= limit:
                continue
            buckets.add(bucket)
            keep.add(backup_id)
    if ordered:
        keep.add(ordered[0])
    return keep


def deletion_plan(root: Path, now: dt.datetime | None = None) -> list[Path]:
    now = now or dt.datetime.now(dt.timezone.utc)
    objects = inventory(root)
    complete = [backup_id for backup_id, kinds in objects.items() if set(kinds) == KINDS]
    keep = retention_set(complete)
    delete: list[Path] = []
    for backup_id, kinds in objects.items():
        if set(kinds) == KINDS:
            if backup_id not in keep:
                delete.extend(kinds.values())
            continue
        age = (now - backup_time(backup_id)).total_seconds()
        if age > 24 * 3600:
            delete.extend(kinds.values())
    return sorted(delete)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path("/var/lib/admirra-backup/postgres"))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    plan = deletion_plan(args.repository)
    if len(plan) > 100:
        raise RuntimeError("refusing to delete more than 100 backup objects in one run")
    for path in plan:
        print(f"{'delete' if args.apply else 'would-delete'} {path.name}")
        if args.apply:
            path.unlink()
    print(f"backup retention complete: objects={len(plan)} applied={args.apply}")


if __name__ == "__main__":
    main()
