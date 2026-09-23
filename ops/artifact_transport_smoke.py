"""Cross-host smoke using only explicitly labelled synthetic objects; no SQL."""
import argparse
import hashlib
import json
from pathlib import Path
import uuid

from core.artifact_client import RemoteObjects
from core.artifact_storage import ObjectInfo, ObjectMissing

DATA = b"ADMIRRA SYNTHETIC SHARED STORAGE ACCEPTANCE\n" * 1024


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("put", "read", "deny-delete", "delete", "missing", "health"))
    parser.add_argument("key", type=uuid.UUID)
    args = parser.parse_args()
    root = Path("/run/artifact")
    client = RemoteObjects("https://10.77.0.1:9443", (root / "token").read_text().strip(),
        ca_file=str(root / "ca.crt"), cert_file=str(root / "client.crt"), key_file=str(root / "client.key"))
    info = ObjectInfo(str(args.key), len(DATA), hashlib.sha256(DATA).hexdigest())
    try:
        if args.action == "put":
            assert client.put(info, [DATA]) == info
        elif args.action == "read":
            assert client.stat(info.key) == info
            with client.open(info.key, info) as (stream, _):
                assert stream.read() == DATA
        elif args.action == "delete":
            client.delete(info.key)
        elif args.action == "deny-delete":
            assert client.client.delete("/objects/" + info.key).status_code == 403
            assert client.stat(info.key) == info
        elif args.action == "missing":
            try:
                client.stat(info.key)
            except ObjectMissing:
                pass
            else:
                raise AssertionError("Deleted object still visible")
        else:
            assert client.client.get("/health").status_code == 200
            assert client.client.get("/health", headers={"Authorization": ""}).status_code == 401
        print(json.dumps({"action": args.action, "passed": True, "synthetic_bytes": len(DATA)}))
    finally:
        client.close()


if __name__ == "__main__":
    main()
