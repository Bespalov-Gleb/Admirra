"""Frontend-only follow-up to the reviewed signup release; no billing changes.

Run on API-1 from a context containing dist/ and ops/signup-discount/.
Preserve the literal runtime configuration and all previous static chunks.
"""
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import re
import time

from release import compose, inspect, literal, private_json, run, start

EXPECTED = 'sha256:5e4c43b88ba4b73f1a3a5342b996fc02602c124ea64f23986918a9788901983c'
CONTEXT = Path(__file__).resolve().parents[2]
TAG = 'admirra-frontend:signup-ui-compact-20260922'


def containers():
    return {r['Names']: r['ID'] for r in (json.loads(line) for line in run(['docker', 'ps', '--format', '{{json .}}']).splitlines())}


def main():
    before = inspect('frontend')
    assert before['Image'] == EXPECTED, 'Runtime drift; review before redeploy'
    before_ids = containers()
    old_html = run(['docker', 'exec', 'admirra-frontend-1', 'cat', '/usr/share/nginx/html/index.html'])
    new_html = (CONTEXT / 'dist/index.html').read_text()
    entry = r'<script[^>]+src="(/assets/index-[^\"]+\.js)"'
    assets = [re.search(entry, html).group(1) for html in (old_html, new_html)]
    assert assets[0] != assets[1], 'No frontend change'
    run(['docker', 'tag', EXPECTED, 'admirra-signup-ui-base:frontend'])
    run(['docker', 'build', '--network=none', '--pull=false', '--build-arg', 'BASE_IMAGE=admirra-signup-ui-base:frontend',
         '--build-arg', 'APP_RELEASE=signup-ui-compact-20260922', '-t', TAG,
         '-f', str(CONTEXT / 'ops/signup-discount/Dockerfile.frontend'), str(CONTEXT)])
    image = run(['docker', 'image', 'inspect', '--format', '{{.Id}}', TAG]).strip()
    assert inspect('frontend')['Image'] == EXPECTED
    source = before['Config']['Labels']['com.docker.compose.project.config_files']
    assert ',' not in source
    config = json.loads(run(compose(source) + ['config', '--format', 'json']))
    target = config['services']['frontend']
    target.pop('build', None)
    target.pop('env_file', None)
    target['image'] = EXPECTED
    target['environment'] = dict(value.split('=', 1) for value in before['Config']['Env'])
    directory = Path('/etc/admirra/releases') / ('signup-ui-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    directory.mkdir(mode=0o700)
    previous = directory / 'frontend-previous.json'
    active = directory / 'frontend-active.json'
    private_json(previous, literal(config))
    new = deepcopy(config)
    new['services']['frontend']['image'] = image
    private_json(active, literal(new))
    private_json(directory / 'metadata.json', {'active': {'frontend': image}, 'previous': {'frontend': EXPECTED}})
    try:
        start(active, 'frontend')
        for attempt in range(15):
            try:
                run(['curl', '-fsS', '--max-time', '8', '-o', '/dev/null', 'https://admirra.ru/tariffs'])
                break
            except Exception:
                if attempt == 14:
                    raise
                time.sleep(2)
        current = inspect('frontend')
        assert current['Image'] == image and current['State']['Running'] and current['RestartCount'] == 0
        assert current['Config']['Env'] == before['Config']['Env'] or dict(v.split('=', 1) for v in current['Config']['Env']) == target['environment']
        assert current['Mounts'] == before['Mounts']
        assert current['HostConfig']['PortBindings'] == before['HostConfig']['PortBindings']
        assert run(['docker', 'exec', 'admirra-frontend-1', 'sha256sum', '/usr/share/nginx/html/index.html']).split()[0] == hashlib.sha256(new_html.encode()).hexdigest()
        for asset in assets:
            run(['curl', '-fsS', '--max-time', '10', '-o', '/dev/null', 'https://admirra.ru' + asset])
        public = run(['curl', '-fsS', '--max-time', '10', 'https://admirra.ru/tariffs'])
        assert assets[1] in public, 'Public entry is stale'
        after_ids = containers()
        assert all(after_ids.get(name) == cid for name, cid in before_ids.items() if name != 'admirra-frontend-1')
    except BaseException:
        start(previous, 'frontend')
        assert inspect('frontend')['Image'] == EXPECTED
        print('Previous frontend restored', flush=True)
        raise
    print('Frontend updated:', image, '\nEntry:', assets[1], '\nRollback:', previous, flush=True)
    print('Backend/automation/other containers unchanged; old app entry retained', flush=True)


if __name__ == '__main__':
    with open('/var/lock/admirra-summary-release.lock', 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        main()
