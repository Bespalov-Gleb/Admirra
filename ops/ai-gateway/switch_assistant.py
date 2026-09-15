"""Controlled env-only production switch; pinned existing image, no build/pull.

Run on app host. Saves root-only rollback snapshot. Never prints secrets.
Refuses unrelated env drift; rollback refuses intervening .env modifications.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from datetime import datetime, timezone

ROOT = Path('/root/Admirra')
ENV = ROOT / '.env'
BACKUPS = Path('/root/admirra-ai-switch-backups')
VALUES = {'AI_ASSISTANT_PROVIDER': 'openrouter', 'OPENROUTER_BASE_URL': 'http://10.78.0.3:8080/api/v1'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write(path, data):
    tmp = path.with_name(path.name + '.tmp')
    with os.fdopen(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def compose(override):
    subprocess.run(['docker', 'compose', '-f', 'docker-compose.yml', '-f', str(override),
                    'up', '-d', '--no-deps', '--no-build', '--pull', 'never', 'backend'], cwd=ROOT, check=True)


def rollback(snapshot):
    metadata = json.loads((snapshot / 'metadata.json').read_text())
    if digest(ENV.read_bytes()) != metadata['activated_env_sha256']:
        raise SystemExit('Environment changed since activation; review rollback manually')
    write(ENV, (snapshot / 'original.env').read_bytes())
    compose(snapshot / 'image.json')
    print('Rolled back assistant env with original image; no build or pull')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument('--activate', action='store_true')
    group.add_argument('--rollback', type=Path)
    a = p.parse_args()
    BACKUPS.mkdir(mode=0o700, exist_ok=True)
    with (BACKUPS / 'switch.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if a.rollback:
            rollback(a.rollback)
            return
        inspect = json.loads(subprocess.check_output(['docker', 'inspect', 'admirra-backend-1']))[0]
        actual = dict(entry.split('=', 1) for entry in inspect['Config']['Env'] if '=' in entry)
        config = json.loads(subprocess.check_output(['docker', 'compose', 'config', '--format', 'json'], cwd=ROOT))
        expected = config['services']['backend'].get('environment', {})
        drift = [key for key, value in expected.items() if str(value or '') != actual.get(key, '')]
        if drift:
            raise SystemExit('Unexpected environment drift (names only): ' + ', '.join(sorted(drift)))
        if all(actual.get(key) == value for key, value in VALUES.items()):
            print('Assistant already uses gateway; no changes')
            return
        original = ENV.read_bytes()
        content = original.decode()
        for key, value in VALUES.items():
            pattern = re.compile(r'^(?:export\s+)?' + re.escape(key) + r'=.*$', re.MULTILINE)
            if len(pattern.findall(content)) > 1:
                raise SystemExit('Duplicate configuration key: ' + key)
            if pattern.search(content):
                content = pattern.sub(key + '=' + value, content)
            else:
                content = content.rstrip('\n') + '\n' + key + '=' + value + '\n'
        snapshot = BACKUPS / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        snapshot.mkdir(mode=0o700)
        write(snapshot / 'original.env', original)
        write(snapshot / 'image.json', json.dumps({'services': {'backend': {'image': inspect['Image']}}}).encode())
        write(snapshot / 'metadata.json', json.dumps({'original_image': inspect['Image'],
            'original_env_sha256': digest(original), 'activated_env_sha256': digest(content.encode())}).encode())
        write(ENV, content.encode())
        try:
            compose(snapshot / 'image.json')
        except subprocess.CalledProcessError:
            rollback(snapshot)
            raise
        print('Activated assistant gateway; rollback snapshot: ' + str(snapshot))


if __name__ == '__main__':
    main()
