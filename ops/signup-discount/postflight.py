"""Read-only rollout evidence; never print environment values or raw logs."""
import json
import argparse
from pathlib import Path
import re
import subprocess
import urllib.request

parser=argparse.ArgumentParser()
parser.add_argument('--expect-enabled',action='store_true')
args=parser.parse_args()

def run(args):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT)

for service in ('backend', 'automation', 'frontend'):
    name='admirra-' + service + '-1'
    row=json.loads(run(['docker','inspect',name]))[0]
    config=Path(row['Config']['Labels']['com.docker.compose.project.config_files'])
    release=json.loads((config.parent/'metadata.json').read_text())
    assert row['Image']==release['active'][service]
    assert row['State']['Running'] and row['RestartCount']==0
    if service!='frontend':
        env=dict(v.split('=',1) for v in row['Config']['Env'])
        assert env['SIGNUP_DISCOUNT_ENABLED']==('true' if args.expect_enabled else 'false') and not env['SIGNUP_DISCOUNT_PILOT_USER_IDS']
    logs=run(['docker','logs','--since',row['State']['StartedAt'],name])
    errors=sum(bool(re.search(r'(?i)(traceback|\berror\b|\bfatal\b)', line)) for line in logs.splitlines())
    print(service, 'running, restarts=0, error-like log lines=', errors)
    if errors:
        raise RuntimeError('Review private container logs before acceptance')

html=urllib.request.urlopen('https://admirra.ru/tariffs',timeout=10).read().decode()
asset=re.search(r'<script[^>]+src="(/assets/index-[^\"]+\.js)"',html).group(1)
with urllib.request.urlopen('https://admirra.ru'+asset,timeout=10) as response:
    assert response.status==200
print('Production app entry is reachable:', asset)
