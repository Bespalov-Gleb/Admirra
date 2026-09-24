"""Scoped notifications/read transport fix. No app restart or upstream changes."""
import argparse
import json
import re
from pathlib import Path

from ops.cutover_admission.manage import transact
from ops.render_launch_runtime import private_json

SITE = Path('/etc/nginx/sites-enabled/admirra.ru')
READS = Path('/etc/nginx/snippets/admirra-api2-read-proxy.conf')
NOTIFICATIONS = '''    location = /api/notifications/ {
        error_page 418 = @admirra_primary_api;
        if ($request_method !~ ^(GET|HEAD)$) { return 418; }
        include /etc/nginx/snippets/admirra-api2-read-proxy.conf;
    }

'''


def patch_site(source):
    """Preserve weights, admission gate, TLS, headers, all mutation policies."""
    named = re.search(r'location @admirra_primary_api \{([^{}]*)\}', source)
    if not named or 'proxy_next_upstream off;' not in named[1]:
        raise ValueError('Missing non-GET no-retry destination')
    anchor = '    location /api/ {'
    if source.count(anchor) != 1:
        raise ValueError('Generic API location drift')
    if 'location = /api/notifications/ {' not in source:
        source = source.replace(anchor, NOTIFICATIONS + anchor, 1)
    elif source.count(NOTIFICATIONS.strip()) != 1:
        raise ValueError('Notifications location drift')
    for pattern in (r'(location /api/ \{)([^{}]*)(\})',
                    r'(location ~ \^/api/assistant/conversations/ \{)([^{}]*)(\})'):
        def replace(match):
            body = match[2]
            if ('proxy_pass http://admirra_api_read_canary;' not in body
                    or body.count('proxy_next_upstream off;') != 1):
                raise ValueError('Business API upstream/retry policy drift')
            body, count = re.subn(r'proxy_connect_timeout (?:1|3)s;',
                                 'proxy_connect_timeout 3s;', body)
            if count != 1:
                raise ValueError('Business connect timeout drift')
            return match[1] + body + match[3]
        source, count = re.subn(pattern, replace, source)
        if count != 1:
            raise ValueError('Business API location drift')
    return source


def patch_reads(source):
    for directive in ('proxy_read_timeout 5s;', 'proxy_send_timeout 2s;',
                      'proxy_next_upstream_tries 2;', 'proxy_next_upstream_timeout 12s;'):
        if directive not in source:
            raise ValueError('Safe-read policy drift')
    result, count = re.subn(r'proxy_connect_timeout (?:1|3)s;',
                            'proxy_connect_timeout 3s;', source)
    if count != 1 or 'non_idempotent' in source:
        raise ValueError('Safe-read connect/retry policy drift')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['apply', 'rollback'])
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    root = args.root
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if root.is_symlink() or root.stat().st_uid != 0 or root.stat().st_mode & 0o077:
        raise ValueError('Root-owned private release directory required')
    before, after = root / 'before.json', root / 'after.json'
    if not before.exists():
        if args.action != 'apply':
            raise ValueError('No saved configuration to roll back')
        old = {str(p.resolve()): p.read_text() for p in (SITE, READS)}
        new = {str(SITE.resolve()): patch_site(SITE.read_text()),
               str(READS.resolve()): patch_reads(READS.read_text())}
        private_json(before, old)
        private_json(after, new)
    old, new = json.loads(before.read_text()), json.loads(after.read_text())
    current = {p: Path(p).read_text() for p in old}
    if current not in (old, new):
        raise ValueError('Live configuration drift: refusing to overwrite')
    target = new if args.action == 'apply' else old
    transact({Path(p): (text.encode(), 0o644) for p, text in target.items()})
    print('Nginx validated and gracefully reloaded:', args.action)


if __name__ == '__main__':
    main()
