"""Verify shared paths with synthetic files; never modify user uploads."""
import argparse
import hashlib
import json
from pathlib import Path

NAME = ".admirra-shared-smoke-20260924"
DATA = b"AdMirra synthetic cross-host file acceptance\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("inventory", "put", "read", "remove"))
    parser.add_argument("root", choices=("/root/Admirra/uploads", "/srv/admirra/shared/uploads",
                                        "/srv/admirra/shared/rejected-leads", "/data/uploads", "/data/rejected-leads"))
    args = parser.parse_args()
    root = Path(args.root)
    path = root / NAME
    if args.action == "inventory":
        digest, count, size = hashlib.sha256(), 0, 0
        for file in sorted(root.rglob("*")):
            if file.name == NAME or not file.is_file() or file.is_symlink():
                continue
            data = file.read_bytes()
            digest.update(str(file.relative_to(root)).encode() + b"\0" + hashlib.sha256(data).digest())
            count += 1
            size += len(data)
        print(json.dumps({"files": count, "bytes": size, "manifest_sha256": digest.hexdigest()}))
        return
    if args.action == "put":
        with path.open("xb") as stream:
            stream.write(DATA)
            stream.flush()
            __import__("os").fsync(stream.fileno())
    else:
        assert path.read_bytes() == DATA, "Unexpected synthetic marker contents"
        if args.action == "remove":
            path.unlink()
    print(json.dumps({"action": args.action, "passed": True}))


if __name__ == "__main__":
    main()
