"""Enable 25 MiB only for assistant conversation endpoints on admirra.ru."""
from datetime import datetime, timezone
from pathlib import Path
import subprocess

path = Path('/etc/nginx/sites-available/admirra.ru')
original = path.read_text()
marker = '    location ^~ /api/assistant/conversations/ {'
if marker in original:
    raise SystemExit('Assistant location already exists; review manually')
needle = '    location /api/ {'
assert original.count(needle) == 1
block = '''    location ^~ /api/assistant/conversations/ {
        client_max_body_size 25m;
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

'''
backup = Path('/root') / ('admirra-ru-before-files25-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '.conf')
backup.write_text(original)
backup.chmod(0o600)
try:
    path.write_text(original.replace(needle, block + needle))
    subprocess.run(['nginx', '-t'], check=True)
    subprocess.run(['systemctl', 'reload', 'nginx'], check=True)
except BaseException:
    path.write_text(original)
    subprocess.run(['nginx', '-t'], check=True)
    subprocess.run(['systemctl', 'reload', 'nginx'], check=True)
    raise
print('Nginx updated. Backup:', backup)
