"""Create a reviewed backend source artifact, without git/credentials/user edits.

Only tracked files from explicitly allowed directories, plus explicitly named
new files. This is NOT a dump of the dirty working tree or a production backup.
"""
import argparse
import io
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = {"core", "backend_api", "automation", "ai", "lead_validator", "internal_admin", "alembic", "certs", "tests", "ops"}
ROOT_FILES = {"Dockerfile", ".dockerignore", "requirements.txt", "requirements.lock", "alembic.ini"}
FORBIDDEN_PARTS = {".git", "secrets", "uploads", "seo_uploads", "node_modules", "__pycache__"}


def allowed(path: str) -> bool:
    p = Path(path)
    if not p.parts or p.is_absolute() or ".." in p.parts:
        return False
    if p.parts[0] not in DIRECTORIES and path not in ROOT_FILES:
        return False
    return not any(part in FORBIDDEN_PARTS or part.startswith(".env") for part in p.parts) and not path.endswith(
        (".pem", ".key", ".dump", ".sql.gz", ".pyc", ".log", "_probe.py", "service_account.json", "google-service-account.json")
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--include", action="append", default=[])
    parser.add_argument("--revision", help="Package tracked sources from a commit for baseline testing")
    args = parser.parse_args()
    revision = None
    if args.revision:
        revision = subprocess.check_output(["git", "rev-parse", "--verify", args.revision + "^{commit}"], cwd=ROOT).decode().strip()
    listing = ["git", "ls-tree", "-r", "--name-only", "-z", revision] if revision else ["git", "ls-files", "-z"]
    tracked = set(subprocess.check_output(listing, cwd=ROOT).decode().split("\0"))
    paths = set(tracked)
    for path in args.include:
        if not allowed(path):
            raise SystemExit(f"Refusing non-runtime path: {path}")
        paths.add(path)
    with tarfile.open(args.output, "w:gz") as archive:
        count = 0
        for path in sorted(paths):
            if not path or not allowed(path):
                continue
            source = ROOT / path
            if revision and path in tracked:
                content = subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)
                info = tarfile.TarInfo(path)
                info.size = len(content)
                info.mode = 0o644
                archive.addfile(info, io.BytesIO(content))
                count += 1
                continue
            if source.is_symlink():
                raise SystemExit(f"Refusing symlink: {path}")
            if source.is_file():
                archive.add(source, arcname=path, recursive=False)
                count += 1
    print(f"Packaged {count} source files; excluded frontend, secrets, uploads, dumps and git")


if __name__ == "__main__":
    main()
