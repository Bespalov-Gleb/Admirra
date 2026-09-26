"""API-only rolling patch. Invoke only after removing the target from ingress.

Preserves the running environment (except release and an explicit optional
read-cache flag), networks, mounts and ports.
Does not migrate, touch workers, retry business requests or silence alerts.
Root-only literal rollback configs; no credential output.
"""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import re
import subprocess
import time
from ops.render_launch_runtime import capture, inspect_config, literal, private_json, save_checked

BASE = 'sha256:ef9e5c40671bf570671ddf7f890d364f4648cf64ed030a91eedd9923b1dd8cb4'


def compose(project, path, service):
    capture(['docker', 'compose', '-p', project, '-f', str(path), 'up', '-d',
             '--no-deps', '--no-build', '--pull', 'never', '--timeout', '90', service])


def ready(container, release):
    code = ("import json,urllib.request; "
            "p=json.load(urllib.request.urlopen('http://127.0.0.1:8001/api/health/ready',timeout=3)); "
            f"assert p==dict(status='ok',role='api',release={release!r})")
    for _ in range(30):
        try:
            capture(['docker', 'exec', container, 'python', '-c', code])
            return
        except subprocess.CalledProcessError:
            time.sleep(1)
    raise RuntimeError('API readiness deadline exceeded')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['prepare', 'activate', 'rollback'])
    p.add_argument('--container', choices=['admirra-backend-1', 'admirra-api2-api-1'], required=True)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--image')
    p.add_argument('--release', required=True)
    p.add_argument('--expected-image', default=BASE)
    p.add_argument('--expected-release', default='2ce9513')
    p.add_argument('--shared-read-cache', choices=['true', 'false'],
                   help='Explicit, separately tested Metrika read-cache rollout only')
    a = p.parse_args()
    assert os.geteuid() == 0 and re.fullmatch('[a-f0-9]{7,40}', a.release)
    a.root.mkdir(parents=True, mode=0o700, exist_ok=True)
    assert not a.root.is_symlink() and a.root.stat().st_mode & 0o077 == 0
    if a.action == 'prepare':
        old, config, service, project = inspect_config(a.container)
        assert old['Image'] == a.expected_image, 'Runtime image drift'
        image = capture(['docker', 'image', 'inspect', '--format', '{{.Id}}', a.image]).strip()
        env = config['services'][service]['environment']
        assert env['APP_PROCESS_ROLE'] == 'api' and env['APP_RELEASE'] == a.expected_release
        private_json(a.root / 'before.json', old)
        private_json(a.root / 'previous.json', literal(config))
        active = deepcopy(config)
        active['services'][service].update(image=image, pull_policy='never')
        active['services'][service]['environment']['APP_RELEASE'] = a.release
        overrides = {}
        if a.shared_read_cache is not None:
            assert env.get('READ_CACHE_REDIS_URL'), 'Cache Redis must already be configured'
            overrides['SHARED_READ_CACHE'] = a.shared_read_cache
        active['services'][service]['environment'].update(overrides)
        save_checked(a.root, 'active', active, service, active['services'][service]['environment'], project)
        private_json(a.root / 'deployment.json', dict(project=project, service=service, image=image,
                                                      release=a.release, container=a.container, previous_release=env['APP_RELEASE'],
                                                      environment_overrides=overrides))
        print('Prepared API-only pinned image and rollback; runtime unchanged')
        return
    meta = json.loads((a.root / 'deployment.json').read_text())
    old = json.loads((a.root / 'before.json').read_text())
    assert meta['release'] == a.release and meta['container'] == a.container
    if a.action == 'rollback':
        compose(meta['project'], a.root / 'previous.json', meta['service'])
        ready(a.container, meta.get('previous_release', '2ce9513'))
        print('Previous API restored')
        return
    current = json.loads(capture(['docker', 'inspect', a.container]))[0]
    assert current['Id'] == old['Id'], 'Prepared runtime changed'
    # Docker removes the old container log during recreate. Retain a bounded,
    # root-only diagnostic snapshot so a pre-cutover failure stays investigable.
    log_path = a.root / 'pre-activation-logs.json'
    if not log_path.exists():
        logs = subprocess.run(['docker', 'logs', '--since', '10m', '--tail', '3000', a.container],
                              text=True, capture_output=True, timeout=15, check=True)
        private_json(log_path, {'stdout':logs.stdout, 'stderr':logs.stderr})
    try:
        compose(meta['project'], a.root / 'active.json', meta['service'])
        ready(a.container, a.release)
        new = json.loads(capture(['docker', 'inspect', a.container]))[0]
        expected_env = dict(item.split('=', 1) for item in old['Config']['Env'])
        expected_env['APP_RELEASE'] = a.release
        expected_env.update(meta.get('environment_overrides', {}))
        checks = {
            'environment': dict(item.split('=', 1) for item in new['Config']['Env']) == expected_env,
            'image': new['Image'] == meta['image'],
            'ports': new['HostConfig']['PortBindings'] == old['HostConfig']['PortBindings'],
            'mounts': sorted(new['Mounts'], key=lambda m: m['Destination']) == sorted(old['Mounts'], key=lambda m: m['Destination']),
            'networks': set(new['NetworkSettings']['Networks']) == set(old['NetworkSettings']['Networks']),
        }
        print(json.dumps({'runtime_checks': checks}), flush=True)
        assert all(checks.values()), 'Runtime drift'
        private_json(a.root / 'accepted.json', dict(image=new['Image'], started_at=new['State']['StartedAt'],
                                                   release=a.release, container=a.container))
    except Exception:
        compose(meta['project'], a.root / 'previous.json', meta['service'])
        ready(a.container, meta.get('previous_release', '2ce9513'))
        raise
    print('API ready; pinned image/release and explicit cache flag verified; rollback retained')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('Deployment stopped:', type(exc).__name__)
        raise SystemExit(1)
