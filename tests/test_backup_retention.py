import datetime as dt
from pathlib import Path

from ops.backup.prune import KINDS, LEGACY_KINDS, deletion_plan, is_complete, retention_set


def backup_id(value: dt.datetime, suffix: str = "deadbeef") -> str:
    return value.strftime("%Y%m%dT%H%M%SZ-") + suffix


def write_set(root: Path, value: dt.datetime, *, complete: bool = True) -> str:
    identifier = backup_id(value)
    kinds = KINDS if complete else {"database"}
    for kind in kinds:
        path = root / f"{identifier}.{kind}.age"
        path.write_bytes(b"encrypted")
        timestamp = value.timestamp()
        path.touch()
        path.chmod(0o600)
        import os
        os.utime(path, (timestamp, timestamp))
    return identifier


def test_retention_keeps_daily_weekly_monthly_and_latest():
    now = dt.datetime(2026, 9, 20, 12, tzinfo=dt.timezone.utc)
    ids = [backup_id(now - dt.timedelta(days=offset)) for offset in range(120)]
    keep = retention_set(ids)
    assert ids[0] in keep
    assert len(keep) <= 14
    assert {backup_time[:8] for backup_time in keep} >= {value[:8] for value in ids[:7]}
    assert is_complete(LEGACY_KINDS)
    assert is_complete(KINDS)
    assert not is_complete({"database", "globals"})


def test_deletion_plan_removes_only_expired_sets_and_old_incomplete(tmp_path):
    root = tmp_path / "repository"
    root.mkdir(mode=0o700)
    now = dt.datetime(2026, 9, 20, 12, tzinfo=dt.timezone.utc)
    newest = write_set(root, now)
    for offset in range(1, 130):
        write_set(root, now - dt.timedelta(days=offset))
    incomplete = write_set(root, now - dt.timedelta(days=2, hours=1), complete=False)

    plan = deletion_plan(root, now)
    names = {path.name for path in plan}
    assert not any(name.startswith(newest) for name in names)
    assert f"{incomplete}.database.age" in names
    assert all(path.parent == root for path in plan)
