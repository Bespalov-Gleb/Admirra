"""Scoped Nginx + alert wording rollout. No API/worker restart or retry policy change."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.request

from ops.cutover_admission.manage import transact

UPSTREAM = Path('/etc/nginx/conf.d/admirra-api2-upstream.conf')
SUMMARIES = {
    'API-2 canary health guard is failing': 'AdMirra API pool health guard is failing (API-1/API-2)',
    'API-2 canary produced final 5xx responses': 'AdMirra API pool returned final 5xx responses (API-1/API-2)',
}


def patch_upstream(source):
    if source.count('upstream admirra_api_read_canary {') != 1:
        raise ValueError('Unexpected upstream')
    if source.count('keepalive 16;') != 1 or re.search(r'^\s*keepalive_timeout\s', source, re.M):
        raise ValueError('Unexpected existing keepalive settings')
    if ' down;' in source:
        raise ValueError('Refusing rollout during an API drain')
    return source.replace('    keepalive 16;', '    keepalive 16;\n'
        '    # Retire idle pooled connections before Uvicorn closes them at 5s.\n'
        '    keepalive_timeout 3s;')


def patch_rules(source):
    for old, new in SUMMARIES.items():
        old, new = f'summary: "{old}"', f'summary: "{new}"'
        if source.count(old) != 1:
            raise ValueError('Alert summary drift')
        source = source.replace(old, new)
    return source


def write_bound_file(path, contents):
    # Prometheus has a file bind mount: preserve its inode, then explicit reload.
    with path.open('w') as handle:
        handle.write(contents)
        handle.flush()
        os.fsync(handle.fileno())


def reload_prometheus():
    subprocess.run(['docker', 'exec', 'admirra-prometheus', 'promtool',
        'check', 'rules', '/etc/prometheus/rules.yml'], check=True, timeout=30)
    request = urllib.request.Request('http://127.0.0.1:9090/-/reload', method='POST')
    with urllib.request.urlopen(request, timeout=10) as response:
        assert response.status == 200


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backup', type=Path, required=True)
    args = parser.parse_args()
    assert os.geteuid() == 0
    mounts = json.loads(subprocess.check_output(['docker', 'inspect', 'admirra-prometheus']))[0]['Mounts']
    rules = Path(next(m['Source'] for m in mounts if m['Destination'] == '/etc/prometheus/rules.yml'))
    old_upstream, old_rules = UPSTREAM.read_text(), rules.read_text()
    new_upstream, new_rules = patch_upstream(old_upstream), patch_rules(old_rules)
    args.backup.mkdir(mode=0o700, parents=True, exist_ok=False)
    (args.backup / 'upstream.conf').write_text(old_upstream)
    (args.backup / 'rules.yml').write_text(old_rules)
    (args.backup / 'paths.json').write_text(json.dumps({'upstream': str(UPSTREAM), 'rules': str(rules)}))
    try:
        transact({UPSTREAM: (new_upstream.encode(), UPSTREAM.stat().st_mode & 0o777)})
        write_bound_file(rules, new_rules)
        reload_prometheus()
    except BaseException:
        write_bound_file(rules, old_rules)
        transact({UPSTREAM: (old_upstream.encode(), UPSTREAM.stat().st_mode & 0o777)})
        reload_prometheus()
        raise
    print(json.dumps({'keepalive_timeout': '3s', 'weights_and_retries_unchanged': True,
        'alert_conditions_unchanged': True, 'backup': str(args.backup)}))


if __name__ == '__main__':
    main()
