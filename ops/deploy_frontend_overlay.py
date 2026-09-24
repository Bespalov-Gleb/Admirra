"""Scoped frontend activation from a prebuilt, pinned overlay image.

Run on API-1 with ops.render_launch_runtime importable. No build/pull, no app or
worker restart, no env changes. Secrets stay in root-only Compose JSON files.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
import urllib.request

from ops.render_launch_runtime import capture, inspect_config, literal, private_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--expected-image', required=True)
    parser.add_argument('--image', required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--index', required=True, type=Path)
    args = parser.parse_args()
    assert re.fullmatch(r'[0-9a-f]{7,40}', args.source)
    assert re.fullmatch(r'sha256:[0-9a-f]{64}', args.expected_image)
    old, config, service, project = inspect_config('admirra-frontend-1')
    assert old['Image'] == args.expected_image and service == 'frontend' and project == 'admirra'
    image = capture(['docker', 'image', 'inspect', '--format', '{{.Id}}', args.image]).strip()
    assert re.fullmatch(r'sha256:[0-9a-f]{64}', image)
    expected_index = args.index.read_bytes()
    scripts = re.findall(rb'<script[^>]*src="([^"]+)"', expected_index)
    entry = next(value.decode() for value in scripts if value.startswith(b'/assets/index-'))
    release = Path('/etc/admirra/releases') / ('frontend-readiness-' + args.source)
    release.mkdir(mode=0o700)
    private_json(release / 'frontend-previous.json', literal(config))
    active = deepcopy(config)
    active['services']['frontend']['image'] = image
    private_json(release / 'frontend-active.json', literal(active))

    def inspect(name):
        return json.loads(capture(['docker', 'inspect', name]))[0]

    def checksum(path):
        return capture(['docker', 'exec', 'admirra-frontend-1', 'sha256sum', path]).split()[0]

    def start(filename):
        subprocess.run(['docker', 'compose', '-p', project, '-f', str(release / filename),
                        'up', '-d', '--no-deps', '--no-build', '--pull', 'never', 'frontend'], check=True)

    fixed_paths = ['/usr/share/nginx/html/landing-new/index.html', '/etc/nginx/conf.d/default.conf',
                   *['/usr/share/nginx/html/admirra/' + name for name in
                     ('agreement.html', 'user-agreement.html', 'personal-data.html', 'legal.css', 'legal.js')]]
    before = {path: checksum(path) for path in fixed_paths}
    unchanged = {name: inspect(name)['Id'] for name in
                 ('admirra-backend-1', 'admirra-automation-1', 'admirra-db-1')}
    try:
        start('frontend-active.json')
        current = inspect('admirra-frontend-1')
        assert current['Image'] == image and current['State']['Running']
        assert set(current['Config']['Env']) == set(old['Config']['Env'])
        assert current['Mounts'] == old['Mounts']
        assert current['HostConfig']['PortBindings'] == old['HostConfig']['PortBindings']
        assert all(inspect(name)['Id'] == value for name, value in unchanged.items())
        assert all(checksum(path) == value for path, value in before.items())
        assert checksum('/usr/share/nginx/html/index.html') == hashlib.sha256(expected_index).hexdigest()
        capture(['docker', 'exec', 'admirra-frontend-1', 'nginx', '-t'])
        for attempt in range(5):
            try:
                data = urllib.request.urlopen('https://admirra.ru/ai', timeout=10).read()
                assert data == expected_index
                assert urllib.request.urlopen('https://admirra.ru' + entry, timeout=10).status == 200
                assert urllib.request.urlopen('https://admirra.ru', timeout=10).status == 200
                assert json.load(urllib.request.urlopen('http://127.0.0.1:8001/api/health/ready', timeout=10))['status'] == 'ok'
                break
            except Exception:
                if attempt == 4:
                    raise
                time.sleep(1)
    except BaseException:
        start('frontend-previous.json')
        raise
    evidence = dict(source=args.source, image=image, release_root=str(release), entry=entry,
                    public_index_verified=True, landing_documents_nginx_unchanged=True,
                    api_db_legacy_automation_unchanged=True)
    private_json(release / 'acceptance.json', evidence)
    print(json.dumps(evidence))


if __name__ == '__main__':
    main()
