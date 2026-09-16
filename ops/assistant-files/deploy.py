"""Host-only targeted image rollout. Never prints/resolves secrets to terminal.

Build the two overlay images first. --activate IMAGE_SUFFIX or --rollback SNAPSHOT.
Leaves .env, Git checkout, database schema, automation and gateways unchanged.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path('/root/Admirra')
BACKUPS = Path('/root/admirra-assistant-files-backups')
SERVICES = ('backend', 'frontend')
EXPECTED = {
    'backend': 'sha256:778c896e65f79be3fb33748c1c819d22dc7fd3ffb677505bf2fe987b43bbb2c8',
    'frontend': 'sha256:b5f76a05f74f55b37b5c5314591b249e2188cc229a2c729b969987bcdee1a60b',
}


def capture(args):
    return subprocess.check_output(args, cwd=ROOT, text=True)


def inspect():
    return {s: json.loads(capture(['docker', 'inspect', 'admirra-' + s + '-1']))[0] for s in SERVICES}


def env(row):
    return dict(v.split('=', 1) for v in row['Config']['Env'])


def write(path, obj):
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as f:
        json.dump(obj, f)


def literal(value):
    if isinstance(value, str): return value.replace('$', '$$')
    if isinstance(value, dict): return {k: literal(v) for k, v in value.items()}
    if isinstance(value, list): return [literal(v) for v in value]
    return value


def compose(path):
    return ['docker', 'compose', '-p', 'admirra', '--project-directory', str(ROOT), '-f', str(path)]


def start(path, service):
    subprocess.run(compose(path) + ['up', '-d', '--no-deps', '--no-build', '--pull', 'never', '--timeout', '45', service],
                   cwd=ROOT, check=True)


def healthy():
    for _ in range(30):
        check = subprocess.run(['docker', 'exec', 'admirra-backend-1', 'python', '-c',
            "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/openapi.json',timeout=3)"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if check.returncode == 0: return
        time.sleep(2)
    raise RuntimeError('Backend health check failed')


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def activate(suffix):
    old = inspect()
    if any(old[s]['Image'] != EXPECTED[s] for s in SERVICES):
        raise RuntimeError('Production images changed; review before deployment')
    images = {s: capture(['docker', 'image', 'inspect', '--format', '{{.Id}}', f'admirra-{s}:files-{suffix}']).strip() for s in SERVICES}
    base = json.loads(capture(['docker', 'compose', 'config', '--format', 'json']))
    for s in SERVICES:
        service = base['services'][s]
        service.pop('build', None)
        service.pop('env_file', None)
        service['environment'] = env(old[s])
        service['image'] = old[s]['Image']
    snapshot = BACKUPS / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    snapshot.mkdir(mode=0o700)
    write(snapshot / 'original.json', literal(base))
    for s in SERVICES: base['services'][s]['image'] = images[s]
    write(snapshot / 'active.json', literal(base))
    meta = {'previous': {s: old[s]['Image'] for s in SERVICES}, 'active': images,
            'env_sha256': file_hash(ROOT / '.env'), 'nginx_sha256': file_hash(ROOT / 'nginx.conf')}
    write(snapshot / 'metadata.json', meta)
    resolved = json.loads(capture(compose(snapshot / 'active.json') + ['config', '--format', 'json']))
    for s in SERVICES:
        if resolved['services'][s]['environment'] != env(old[s]):
            raise RuntimeError('Environment drift in resolved configuration: ' + s)
    print('Snapshot:', snapshot, flush=True)
    try:
        start(snapshot / 'active.json', 'backend')
        healthy()
        start(snapshot / 'active.json', 'frontend')
        current = inspect()
        for s in SERVICES:
            if env(current[s]) != env(old[s]) or current[s]['Image'] != images[s]:
                raise RuntimeError('Runtime image/environment mismatch: ' + s)
        subprocess.run(['curl', '-fsS', '--retry', '6', '--retry-delay', '2', '--retry-all-errors',
                        '-o', '/dev/null', 'https://admirra.ru/'], check=True)
        print('Activated. Environments preserved; backend and public HTTP healthy.', flush=True)
    except BaseException:
        print('Activation failed; restoring previous images.', flush=True)
        start(snapshot / 'original.json', 'backend')
        healthy()
        start(snapshot / 'original.json', 'frontend')
        raise


def rollback(snapshot):
    meta = json.loads((snapshot / 'metadata.json').read_text())
    current = inspect()
    if file_hash(ROOT / '.env') != meta['env_sha256'] or file_hash(ROOT / 'nginx.conf') != meta['nginx_sha256']:
        raise RuntimeError('Configuration changed since rollout; review rollback manually')
    if any(current[s]['Image'] != meta['active'][s] for s in SERVICES):
        raise RuntimeError('Images changed since rollout; review rollback manually')
    start(snapshot / 'original.json', 'backend')
    healthy()
    start(snapshot / 'original.json', 'frontend')
    print('Previous images restored; uploaded text remains in the database.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--activate')
    group.add_argument('--rollback', type=Path)
    args = parser.parse_args()
    BACKUPS.mkdir(mode=0o700, exist_ok=True)
    with (BACKUPS / 'deploy.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.rollback: rollback(args.rollback)
        else: activate(args.activate)
