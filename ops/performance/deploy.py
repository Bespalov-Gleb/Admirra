"""Scoped read-performance rollout; does not enable pending DevOps migrations.

Production configuration is copied from the running containers, kept root-only,
and checked after replacement. Automation, API-2, prices and secrets unchanged.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone, timedelta
import fcntl
import json
from pathlib import Path
import subprocess

from ops.deploy_assistant_quota import capture, compose, literal, write, ready, start

EXPECTED = {
    "backend": "sha256:6321c5fb910e9f8e4ff942deffd6bbe63d6285efd05b35b670a192ce780d365d",
    "frontend": "sha256:680b8893a1dcfa00460d0c2f591b5e7cb415d047cd9780d566535e6419a04af1",
}


def inspect(service):
    return json.loads(capture(["docker", "inspect", f"admirra-{service}-1"]))[0]


def mount_config(container):
    # Docker inspect does not guarantee mount array order across recreation.
    # Compare every property, keyed by the unique container destination.
    mounts = container["Mounts"]
    result = {mount["Destination"]: mount for mount in mounts}
    if len(result) != len(mounts):
        raise RuntimeError("Duplicate mount destinations")
    return result


def deploy(backend, frontend, email):
    moscow = datetime.now(timezone(timedelta(hours=3)))
    minutes = moscow.hour * 60 + moscow.minute
    if any(abs(minutes - scheduled) <= 15 for scheduled in (180, 300)):
        raise RuntimeError("Do not restart API during nightly scheduler windows")
    old = {service: inspect(service) for service in EXPECTED}
    if any(old[service]["Image"] != image for service, image in EXPECTED.items()):
        raise RuntimeError("Runtime image drift; re-review required")
    preflight = '''
import sqlalchemy as sa
from core.database import SessionLocal
with SessionLocal() as db:
    db.execute(sa.text("SET TRANSACTION READ ONLY"))
    db.execute(sa.text("SET LOCAL statement_timeout='5s'"))
    assert db.scalar(sa.text("SELECT count(*) FROM sync_jobs WHERE status IN ('RUNNING','QUEUED')")) == 0, 'sync busy'
    assert db.scalar(sa.text("SELECT count(*) FROM report_deliveries WHERE status='sending'")) == 0, 'reports busy'
    assert db.scalar(sa.text("SELECT count(*) FROM ai_messages WHERE created_at > now() - interval '10 minutes'")) == 0, 'AI recently active'
    assert db.scalar(sa.text("SELECT version_num FROM alembic_version")) == 'cc3d4e5f6a7b', 'schema drift'
'''
    capture(["docker", "exec", "-i", "admirra-backend-1", "python", "-"], input=preflight)
    directory = Path("/etc/admirra/releases") / ("summary-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    directory.mkdir(mode=0o700, parents=True)
    write(directory / "runtime-before.json", old)
    images = dict(backend=backend, frontend=frontend)
    for service in EXPECTED:
        images[service] = capture(["docker", "image", "inspect", "--format", "{{.Id}}", images[service]]).strip()
        source = old[service]["Config"]["Labels"]["com.docker.compose.project.config_files"]
        if "," in source:
            raise RuntimeError("Expected a single captured literal config")
        config = json.loads(capture(compose(source) + ["config", "--format", "json"]))
        target = config["services"][service]
        target.pop("build", None)
        target.pop("env_file", None)
        target["image"] = old[service]["Image"]
        target["environment"] = dict(item.split("=", 1) for item in old[service]["Config"]["Env"])
        write(directory / f"{service}-previous.json", literal(config))
        new = deepcopy(config)
        new["services"][service]["image"] = images[service]
        write(directory / f"{service}-active.json", literal(new))
        resolved = json.loads(capture(compose(directory / f"{service}-active.json") + ["config", "--format", "json"]))
        if resolved["services"][service]["environment"] != target["environment"]:
            raise RuntimeError("Literal environment roundtrip mismatch")
    write(directory / "metadata.json", {"previous": EXPECTED, "active": images})
    print("Rollback configs:", directory, flush=True)
    try:
        start(directory / "backend-active.json", "backend")
        ready()
        # Tests only the approved account; no external sync/AI/recipient effects.
        code = (Path(__file__).parent / "smoke.py").read_text()
        print(capture(["docker", "exec", "-i", "admirra-backend-1", "python", "-", "--email", email], input=code).strip())
        start(directory / "frontend-active.json", "frontend")
        for service in EXPECTED:
            new = inspect(service)
            checks = {
                "image": new["Image"] == images[service],
                "environment": set(new["Config"]["Env"]) == set(old[service]["Config"]["Env"]),
                "mounts": mount_config(new) == mount_config(old[service]),
                "ports": new["HostConfig"]["PortBindings"] == old[service]["HostConfig"]["PortBindings"],
            }
            if not all(checks.values()):
                print("Runtime check failed:", service, [key for key, ok in checks.items() if not ok], flush=True)
                raise RuntimeError("Runtime environment/mount/port drift")
        capture(["curl", "-fsS", "--max-time", "10", "-o", "/dev/null", "https://admirra.ru/"])
    except BaseException:
        print("Rolling back summary release", flush=True)
        for service in EXPECTED:
            start(directory / f"{service}-previous.json", service)
        ready()
        raise
    print("Summary release active; automation, schema, API-2 and environment unchanged")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend-image", required=True)
    parser.add_argument("--frontend-image", required=True)
    parser.add_argument("--email", required=True)
    args = parser.parse_args()
    with open("/var/lock/admirra-summary-release.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            deploy(args.backend_image, args.frontend_image, args.email)
        except Exception as error:
            # CalledProcessError may contain rendered credentials: never print it.
            print("Summary deployment blocked or rolled back:", type(error).__name__)
            raise SystemExit(1)
