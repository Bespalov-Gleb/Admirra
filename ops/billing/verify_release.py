"""Host-only, read-only release smoke checks; no checkout or payment requests."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[2]

def body(path):
    with urllib.request.urlopen('https://admirra.ru'+path, timeout=20) as r:
        assert r.status == 200, path
        return r.read()

expected=(ROOT/'dist/landing-new/index.html').read_bytes()
assert body('/') == expected, 'Public landing differs from release'
expected_css=(ROOT/'dist/landing-new/assets/css/main.css').read_bytes()
assert body('/landing-new/assets/css/main.css?v=pricing-20260916') == expected_css, 'Landing CSS differs'
expected_app=(ROOT/'dist/index.html').read_bytes()
for path in ('/ai','/settings'):
    assert body(path) == expected_app, 'App HTML differs: '+path
scripts=re.findall(rb'<script[^>]+src="([^"]+)"',expected_app)
for src in scripts:
    url=src.decode()
    if url.startswith('/assets/'):
        asset=body(url)
        assert asset == (ROOT/'dist'/url.lstrip('/')).read_bytes(), 'App bundle differs'
        assert b'createApp' in asset or len(asset)>10000
actual=subprocess.check_output(['docker','exec','admirra-backend-1','sha256sum','/app/backend_api/billing.py'],text=True).split()[0]
assert actual == hashlib.sha256((ROOT/'backend_api/billing.py').read_bytes()).hexdigest()
print(json.dumps({'landing':'exact release','landing_css':'exact release','app_routes':['/ai','/settings'],
                  'js_assets':'exact release','backend_billing':'exact release'}))
