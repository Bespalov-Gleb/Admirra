import hashlib
import io
from pathlib import Path

import pytest

from ops.backup.receive import parse_command, receive


BACKUP_ID = "20260920T120000Z-deadbeef"


def private_repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir(mode=0o700)
    return root


def test_receiver_accepts_only_fixed_object_names(tmp_path):
    root = private_repository(tmp_path)
    payload = b"age-encrypted-test-payload"
    receipt = receive(root, f"put {BACKUP_ID} database", io.BytesIO(payload))

    stored = root / f"{BACKUP_ID}.database.age"
    assert stored.read_bytes() == payload
    assert stored.stat().st_mode & 0o777 == 0o600
    assert receipt.sha256 == hashlib.sha256(payload).hexdigest()
    assert not list(root.glob("*.partial"))


@pytest.mark.parametrize("command", [
    "", "list", "put ../escape database", f"put {BACKUP_ID} unknown",
    f"put {BACKUP_ID} database extra", f"rm {BACKUP_ID} database", f"put {BACKUP_ID} secrets",
])
def test_receiver_rejects_shell_and_path_injection(command):
    with pytest.raises(ValueError, match="unsupported"):
        parse_command(command)


def test_receiver_never_overwrites_and_cleans_failed_partial(tmp_path):
    root = private_repository(tmp_path)
    receive(root, f"put {BACKUP_ID} globals", io.BytesIO(b"first"))
    with pytest.raises(FileExistsError):
        receive(root, f"put {BACKUP_ID} globals", io.BytesIO(b"second"))

    other = "20260920T120001Z-feedface"
    with pytest.raises(ValueError, match="exceeds"):
        receive(
            root,
            f"put {other} manifest",
            io.BytesIO(b"too large"),
            limits={"manifest": 2},
        )
    assert not (root / f"{other}.manifest.age").exists()
    assert not list(root.glob("*.partial"))


def test_receiver_rejects_empty_and_public_repository(tmp_path):
    root = private_repository(tmp_path)
    with pytest.raises(ValueError, match="empty"):
        receive(root, f"put {BACKUP_ID} manifest", io.BytesIO(b""))
    root.chmod(0o755)
    with pytest.raises(RuntimeError, match="private"):
        receive(root, f"put {BACKUP_ID} manifest", io.BytesIO(b"x"))
