"""Frontend-only read lifecycle release; never restarts API/workers or migrates."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path

from ops.deploy_assistant_quota import capture, compose, literal, write, start
from ops.performance.deploy import mount_config

EXPECTED_FRONTEND = 'sha256:019ae4025bf17f9d4412b78946ebfb4a74a2aac6628c4dde9803a1ecbb31ec80'


def inspect(name):
    return json.loads(capture(['docker', 'inspect', name]))[0]


def deploy(image):
    old = inspect('admirra-frontend-1')
    if old['Image'] != EXPECTED_FRONTEND:
        raise RuntimeError('Frontend drift: re-review required')
    unchanged = {name: inspect(name)['Id'] for name in ('admirra-backend-1', 'admirra-automation-1')}
    image = capture(['docker', 'image', 'inspect', '--format', '{{.Id}}', image]).strip()
    source = old['Config']['Labels']['com.docker.compose.project.config_files']
    if ',' in source:
        raise RuntimeError('Expected a single captured config')
    config = json.loads(capture(compose(source) + ['config', '--format', 'json']))
    target = config['services']['frontend']
    target.pop('build', None)
    target.pop('env_file', None)
    target['image'] = old['Image']
    target['environment'] = dict(item.split('=', 1) for item in old['Config']['Env'])
    directory = Path('/etc/admirra/releases') / ('frontend-reads-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    directory.mkdir(mode=0o700, parents=True)
    write(directory / 'previous.json', literal(config))
    active = deepcopy(config)
    active['services']['frontend']['image'] = image
    write(directory / 'active.json', literal(active))
    resolved = json.loads(capture(compose(directory / 'active.json') + ['config', '--format', 'json']))
    if resolved['services']['frontend']['environment'] != target['environment']:
        raise RuntimeError('Environment roundtrip mismatch')
    print('Rollback directory:', directory, flush=True)
    try:
        start(directory / 'active.json', 'frontend')
        new = inspect('admirra-frontend-1')
        assert new['Image'] == image
        assert set(new['Config']['Env']) == set(old['Config']['Env'])
        assert mount_config(new) == mount_config(old)
        assert new['HostConfig']['PortBindings'] == old['HostConfig']['PortBindings']
        assert all(inspect(name)['Id'] == value for name, value in unchanged.items())
        for path in ('/', '/projects', '/dashboard/general-3', '/reports'):
            capture(['curl', '-fsS', '--max-time', '10', '-o', '/dev/null', 'https://admirra.ru' + path])
    except BaseException:
        start(directory / 'previous.json', 'frontend')
        print('Frontend rolled back', flush=True)
        raise
    print('Frontend active; backend/automation container IDs unchanged:', image)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--image', required=True)
    args = parser.parse_args()
    with open('/var/lock/admirra-summary-release.lock', 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            deploy(args.image)
        except Exception as error:
            print('Frontend deployment blocked/rolled back:', type(error).__name__)
            raise SystemExit(1)
