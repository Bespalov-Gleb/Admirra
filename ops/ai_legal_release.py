"""Scoped hotfix on the reviewed legacy runtime; no DevOps migration/cutover.

Run on API1 with --context PATH --backend IMAGE --frontend IMAGE. Preserve
literal env and mounts, except the intentional versioned frontend nginx mount.
Never render captured Compose secrets to stdout.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone, timedelta
import fcntl
import json
from pathlib import Path
import shutil

from ops.deploy_assistant_quota import capture, compose, literal, write, start, ready
from ops.performance.deploy import mount_config

EXPECTED = {
    "backend": "sha256:d497fa5d99258cf7cb36858984bdd1f18d0371a2e368807972cecfedfb613a93",
    "frontend": "sha256:09aaa07dec7a855b98bdc52007b3e1838b925ba2c3167192242f81395663e929",
}
NGINX_SHA = "08e107907c783930ffca7a6693e4241d7138d3cf7fcd1411a9084b9b4be69c05"


def inspect(service):
    return json.loads(capture(["docker", "inspect", f"admirra-{service}-1"]))[0]


AUDIT = '''
import json
import sqlalchemy as sa
from core.database import SessionLocal
with SessionLocal() as db:
    db.execute(sa.text("SET TRANSACTION READ ONLY"))
    db.execute(sa.text("SET LOCAL statement_timeout='5s'"))
    print(json.dumps({
        'schema': db.scalar(sa.text("SELECT version_num FROM alembic_version")),
        'sync_busy': db.scalar(sa.text("SELECT count(*) FROM sync_jobs WHERE status IN ('RUNNING','QUEUED')")),
        'reports_busy': db.scalar(sa.text("SELECT count(*) FROM report_deliveries WHERE status='sending'")),
        'recent_ai': db.scalar(sa.text("SELECT count(*) FROM ai_messages WHERE created_at > now() - interval '10 minutes'")),
        'recent_payments': db.scalar(sa.text("SELECT count(*) FROM billing_events WHERE event_type='intent' AND created_at > now() - interval '10 minutes'")),
    }))
'''


def deploy(context, backend, frontend):
    now = datetime.now(timezone(timedelta(hours=3)))
    if any(abs(now.hour * 60 + now.minute - minute) < 20 for minute in (180, 300)):
        raise RuntimeError("Nightly scheduler window; defer hotfix")
    old = {s: inspect(s) for s in EXPECTED}
    assert all(old[s]["Image"] == EXPECTED[s] for s in EXPECTED), "Runtime drift"
    unchanged = {s: inspect(s)["Id"] for s in ("automation", "admin_frontend")}
    audit = capture(["docker", "exec", "-i", "admirra-backend-1", "python", "-"], input=AUDIT)
    evidence = json.loads(next(line for line in audit.splitlines() if line.startswith("{")))
    print("Read-only preflight:", evidence, flush=True)
    assert evidence.pop("schema") == "cc3d4e5f6a7b", "Schema drift"
    assert not any(evidence.values()), "Production is busy; defer hotfix"
    assert capture(["systemctl", "show", "admirra-logical-backup.service", "-p", "Result", "--value"]).strip() == "success"
    assert capture(["docker", "exec", "admirra-frontend-1", "sha256sum", "/etc/nginx/conf.d/default.conf"]).split()[0] == NGINX_SHA
    directory = Path("/etc/admirra/releases") / ("ai-legal-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    directory.mkdir(mode=0o700, parents=True)
    shutil.copyfile(context / "nginx.conf", directory / "nginx.conf")
    (directory / "nginx.conf").chmod(0o644)
    write(directory / "runtime-before.json", old)
    images = {"backend": backend, "frontend": frontend}
    for service, row in old.items():
        images[service] = capture(["docker", "image", "inspect", "--format", "{{.Id}}", images[service]]).strip()
        path = row["Config"]["Labels"]["com.docker.compose.project.config_files"]
        assert "," not in path
        config = json.loads(capture(compose(path) + ["config", "--format", "json"]))
        target = config["services"][service]
        target.pop("build", None)
        target.pop("env_file", None)
        target["image"] = row["Image"]
        target["environment"] = dict(item.split("=", 1) for item in row["Config"]["Env"])
        write(directory / f"{service}-previous.json", literal(config))
        active = deepcopy(config)
        active["services"][service]["image"] = images[service]
        if service == "frontend":
            mounts = [v for v in active["services"][service]["volumes"] if v["target"] == "/etc/nginx/conf.d/default.conf"]
            assert len(mounts) == 1 and mounts[0]["type"] == "bind"
            mounts[0]["source"] = str(directory / "nginx.conf")
        write(directory / f"{service}-active.json", literal(active))
        resolved = json.loads(capture(compose(directory / f"{service}-active.json") + ["config", "--format", "json"]))
        assert resolved["services"][service]["environment"] == target["environment"], "Environment roundtrip drift"
    write(directory / "metadata.json", {"previous": EXPECTED, "active": images})
    print("Rollback configs:", directory, flush=True)
    try:
        start(directory / "backend-active.json", "backend")
        ready()
        start(directory / "frontend-active.json", "frontend")
        for service, previous in old.items():
            current = inspect(service)
            assert current["Image"] == images[service] and current["State"]["Running"]
            assert set(current["Config"]["Env"]) == set(previous["Config"]["Env"])
            assert current["HostConfig"]["PortBindings"] == previous["HostConfig"]["PortBindings"]
            expected_mounts = deepcopy(mount_config(previous))
            if service == "frontend":
                expected_mounts["/etc/nginx/conf.d/default.conf"]["Source"] = str(directory / "nginx.conf")
            assert mount_config(current) == expected_mounts
        assert all(inspect(s)["Id"] == value for s, value in unchanged.items())
        capture(["docker", "exec", "admirra-frontend-1", "nginx", "-t"])
        for path in ("/", "/ai", "/signin", "/admirra/agreement.html", "/admirra/user-agreement.html", "/admirra/personal-data.html", "/admirra/legal.css"):
            capture(["curl", "-fsS", "--retry", "3", "--retry-all-errors", "--max-time", "10", "-o", "/dev/null", "https://admirra.ru" + path])
        capture(["docker", "exec", "admirra-backend-1", "python", "-c",
            "from ai.comment_llm import require_comment_provider; require_comment_provider(); from ai.report_generator import generate_report"])
    except BaseException:
        print("Hotfix failed; restoring previous images/configuration", flush=True)
        for service in EXPECTED:
            start(directory / f"{service}-previous.json", service)
        ready()
        raise
    print("Hotfix active; schema, automation, admin frontend and worker topology unchanged", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--backend", required=True)
    parser.add_argument("--frontend", required=True)
    args = parser.parse_args()
    with open("/var/lock/admirra-summary-release.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            deploy(args.context, args.backend, args.frontend)
        except Exception as exc:
            print("Hotfix blocked/rolled back:", type(exc).__name__, flush=True)
            raise SystemExit(1)
