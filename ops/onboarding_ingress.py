"""Temporarily drain one API during a compatible rolling release; no retries added.

Restore from the exact private snapshot. Refuse drift rather than overwrite it.
Old Nginx workers must drain before restarting the removed API.
"""
import argparse
import json
import re
from pathlib import Path
from ops.cutover_admission.manage import transact
from ops.render_launch_runtime import private_json

UPSTREAM = Path('/etc/nginx/conf.d/admirra-api2-upstream.conf')
SITE = Path('/etc/nginx/sites-enabled/admirra.ru')


def drained(source, site, target):
    address = '10.77.0.2:8001' if target == 'api2' else '127.0.0.1:8001'
    pattern = r'(server ' + re.escape(address) + r' weight=1 max_fails=3 fail_timeout=5s);'
    updated, n = re.subn(pattern, r'\1 down;', source)
    if n != 1 or source.count(' down;'):
        raise ValueError('Unexpected live upstream topology')
    if target == 'api1':
        if site.count('proxy_pass http://127.0.0.1:8001') != 3:
            raise ValueError('Primary API locations drift')
        site = site.replace('proxy_pass http://127.0.0.1:8001', 'proxy_pass http://10.77.0.2:8001')
    return updated, site


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['api1', 'api2', 'restore'])
    p.add_argument('--root', type=Path, required=True)
    a = p.parse_args()
    a.root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if a.root.is_symlink() or a.root.stat().st_uid != 0 or a.root.stat().st_mode & 0o077:
        raise ValueError('Private root required')
    saved = a.root / 'ingress-before.json'
    if not saved.exists():
        if a.action == 'restore': raise ValueError('Missing snapshot')
        private_json(saved, {str(p.resolve()): p.read_text() for p in (UPSTREAM, SITE)})
    before = json.loads(saved.read_text())
    upath, spath = str(UPSTREAM.resolve()), str(SITE.resolve())
    allowed = [before]
    for target in ('api1', 'api2'):
        u, s = drained(before[upath], before[spath], target)
        allowed.append({upath:u, spath:s})
    current = {p:Path(p).read_text() for p in before}
    if current not in allowed: raise ValueError('Ingress drift')
    selected = allowed[0 if a.action == 'restore' else 1 if a.action == 'api1' else 2]
    transact({Path(p):(content.encode(), 0o644) for p, content in selected.items()})
    print('Ingress gracefully reloaded:', a.action)


if __name__ == '__main__': main()
