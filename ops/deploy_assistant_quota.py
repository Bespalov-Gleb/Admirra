"""Scoped backend/frontend image rollout preserving current literal config.

Run on server 1 after backup and image tests. No price/env changes, no pending
DevOps migrations. Exact prior configs retained root-only for rollback.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path('/root/Admirra')
EXPECTED = {
    'backend': 'sha256:047c8019bbbeec83c0c8cd11b39c03b31af2931d8e2f0b415196199f8768afe0',
    'frontend': 'sha256:1b36b676b9cadca75befb5d03c66ac4c1177b0a7099e652af46360163eba4767',
}


def capture(args, **kwargs):
    return subprocess.check_output(args, cwd=ROOT, text=True, stderr=subprocess.PIPE, **kwargs)


def compose(path):
    return ['docker', 'compose', '-p', 'admirra', '--project-directory', str(ROOT), '-f', str(path)]


def write(path, value):
    with os.fdopen(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'w') as file:
        json.dump(value, file)


def literal(value):
    if isinstance(value, str): return value.replace('$', '$$')
    if isinstance(value, dict): return {key: literal(item) for key, item in value.items()}
    if isinstance(value, list): return [literal(item) for item in value]
    return value


def start(path, service):
    capture(compose(path) + ['up', '-d', '--no-deps', '--no-build', '--pull', 'never', '--timeout', '60', service])


def ready():
    for _ in range(30):
        try:
            capture(['docker', 'exec', 'admirra-backend-1', 'python', '-c',
                "import urllib.request; assert urllib.request.urlopen('http://127.0.0.1:8001/openapi.json',timeout=2).status==200"])
            return
        except subprocess.CalledProcessError:
            time.sleep(2)
    raise RuntimeError('Backend readiness failed')


def deploy(backend_image, frontend_image):
    old = {service: json.loads(capture(['docker', 'inspect', 'admirra-' + service + '-1']))[0] for service in EXPECTED}
    if any(old[service]['Image'] != image for service, image in EXPECTED.items()):
        raise RuntimeError('Runtime image drift: re-review before deploying')
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
    capture(['docker', 'exec', '-i', 'admirra-backend-1', 'python', '-'], input=preflight)
    backup = Path('/root/admirra-assistant-quota') / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup.mkdir(parents=True, mode=0o700)
    images = {'backend': backend_image, 'frontend': frontend_image}
    for service in EXPECTED:
        image = capture(['docker', 'image', 'inspect', '--format', '{{.Id}}', images[service]]).strip()
        path = old[service]['Config']['Labels']['com.docker.compose.project.config_files']
        if ',' in path:
            raise RuntimeError('Expected one captured literal compose file')
        config = json.loads(capture(compose(path) + ['config', '--format', 'json']))
        config['services'][service]['image'] = old[service]['Image']
        config['services'][service].pop('build', None)
        config['services'][service].pop('env_file', None)
        config['services'][service]['environment'] = dict(item.split('=', 1) for item in old[service]['Config']['Env'])
        write(backup / f'{service}-previous.json', literal(config))
        active = deepcopy(config)
        active['services'][service]['image'] = image
        write(backup / f'{service}-active.json', literal(active))
    print('Rollback configs:', backup, flush=True)
    # Additive table only, executed in an unexposed one-off process.
    capture(compose(backup / 'backend-active.json') + ['run', '--rm', '--no-deps', '-T', 'backend',
            'python', '-m', 'ops.migrate_assistant_runs'])
    try:
        start(backup / 'backend-active.json', 'backend')
        ready()
        start(backup / 'frontend-active.json', 'frontend')
        for service in EXPECTED:
            new = json.loads(capture(['docker', 'inspect', 'admirra-' + service + '-1']))[0]
            if (set(new['Config']['Env']) != set(old[service]['Config']['Env'])
                    or new['HostConfig']['PortBindings'] != old[service]['HostConfig']['PortBindings']
                    or new['Mounts'] != old[service]['Mounts']):
                raise RuntimeError('Environment/port/mount drift after rollout')
        capture(['curl', '-fsS', '--max-time', '10', '-o', '/dev/null', 'https://admirra.ru/'])
    except Exception:
        for service in EXPECTED:
            start(backup / f'{service}-previous.json', service)
        ready()
        raise
    print('Backend/frontend updated; original environment, ports and mounts preserved; automation unchanged')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--backend-image', required=True)
    parser.add_argument('--frontend-image', required=True)
    args = parser.parse_args()
    with open('/var/lock/admirra-assistant-quota.lock', 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            deploy(args.backend_image, args.frontend_image)
        except Exception as error:
            print('Deploy blocked/rolled back:', type(error).__name__)
            raise SystemExit(1)
