"""Scoped rolling ingress for the dashboard lock fix; retain exact rollback."""
import argparse
import json
from pathlib import Path
from ops.cutover_admission.manage import transact
from ops.render_launch_runtime import private_json

UPSTREAM = Path('/etc/nginx/conf.d/admirra-api2-upstream.conf')
READS = Path('/etc/nginx/snippets/admirra-api2-read-proxy.conf')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage', choices=['prepare', 'drain-api2', 'drain-api1', 'balanced', 'rollback'])
    p.add_argument('--root', type=Path, required=True)
    a = p.parse_args()
    a.root.mkdir(parents=True, exist_ok=True, mode=0o700)
    assert not a.root.is_symlink() and a.root.stat().st_uid == 0 and not a.root.stat().st_mode & 0o077
    snapshot = a.root / 'ingress-before.json'
    if a.stage == 'prepare':
        old = {str(path): path.read_text() for path in (UPSTREAM, READS)}
        assert old[str(UPSTREAM)].count('max_fails=1 fail_timeout=10s;') == 2
        for address in ('127.0.0.1', '10.77.0.2'):
            assert f'server {address}:8001 weight=1 max_fails=1 fail_timeout=10s;' in old[str(UPSTREAM)]
        assert 'proxy_read_timeout 2s;' in old[str(READS)] and 'proxy_next_upstream_timeout 4s;' in old[str(READS)]
        private_json(snapshot, old)
        print('Ingress backup saved; live config unchanged')
        return
    old = json.loads(snapshot.read_text())
    up = old[str(UPSTREAM)].replace('max_fails=1 fail_timeout=10s;', 'max_fails=3 fail_timeout=5s;')
    reads = (old[str(READS)].replace('proxy_read_timeout 2s;', 'proxy_read_timeout 5s;')
             .replace('proxy_next_upstream_timeout 4s;', 'proxy_next_upstream_timeout 12s;'))
    stage_files = {}
    for stage, excluded in [('drain-api2', '10.77.0.2'), ('drain-api1', '127.0.0.1'), ('balanced', None)]:
        text = up
        if excluded:
            text = text.replace(f'server {excluded}:8001 weight=1 max_fails=3 fail_timeout=5s;',
                                f'server {excluded}:8001 weight=1 max_fails=3 fail_timeout=5s down;')
        stage_files[stage] = {str(UPSTREAM): text, str(READS): reads}
    stage_files['rollback'] = old
    # Refuse to overwrite operator edits or an unrelated rollout.
    current = {str(path): path.read_text() for path in (UPSTREAM, READS)}
    assert current in [old, *stage_files.values()], 'Ingress configuration drift'
    transact({Path(path): (text.encode(), 0o644) for path, text in stage_files[a.stage].items()})
    private_json(a.root / f'ingress-{a.stage}.json', stage_files[a.stage])
    print('Ingress validated/reloaded:', a.stage)


if __name__ == '__main__':
    main()
