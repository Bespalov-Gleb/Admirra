"""Narrow release on API-1. Never enables offers or calls payment providers.

Separate --build / --audit / --activate steps. Captured literal runtime settings
are retained root-only; unrelated services and the pending Alembic head stay put.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path('/root/Admirra')
CONTEXT = Path(__file__).resolve().parents[2]
EXPECTED = {
    'backend': 'sha256:4ca866ebddc4c3af8b1ef4d2905e099453c6e8b6b768192508991b89e8421219',
    'frontend': 'sha256:274aad1d3027412d1a600927f0a388c02f76b487cbeee8ce3670804f73c28a1a',
    'automation': 'sha256:33b4ca03408c55cd11093fa3c4f9b86ecf1f323f50636222a43ea71bb4217ab8',
}
TAG = 'signup-20260922'

def run(args, **kwargs):
    return subprocess.check_output(args, text=True, stderr=subprocess.PIPE, **kwargs)

def inspect(service):
    return json.loads(run(['docker', 'inspect', 'admirra-' + service + '-1']))[0]

def env(row):
    return dict(value.split('=', 1) for value in row['Config']['Env'])

def literal(value):
    if isinstance(value, str): return value.replace('$', '$$')
    if isinstance(value, dict): return {key: literal(item) for key, item in value.items()}
    if isinstance(value, list): return [literal(item) for item in value]
    return value

def private_json(path, value):
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as out:
        json.dump(value, out)

def compose(path):
    return ['docker', 'compose', '-p', 'admirra', '--project-directory', str(ROOT), '-f', str(path)]

def start(path, service):
    run(compose(path) + ['up', '-d', '--no-deps', '--no-build', '--pull', 'never', '--timeout', '60', service])

def runtime():
    state = {service: inspect(service) for service in EXPECTED}
    if any(state[s]['Image'] != EXPECTED[s] for s in EXPECTED):
        raise RuntimeError('Runtime drift; re-review required')
    return state

def build():
    runtime()
    for service in ('backend', 'automation', 'frontend'):
        base = 'admirra-signup-base:' + service
        run(['docker', 'tag', EXPECTED[service], base])
        assert run(['docker', 'image', 'inspect', '--format', '{{.Id}}', base]).strip() == EXPECTED[service]
        run(['docker', 'build', '--network=none', '--pull=false', '--build-arg', 'BASE_IMAGE=' + base,
             '--build-arg', 'APP_RELEASE=' + TAG, '-t', 'admirra-' + service + ':' + TAG,
             '-f', str(CONTEXT / 'ops/signup-discount' / ('Dockerfile.' + service)), str(CONTEXT)])
        print('Built:', service, run(['docker', 'image', 'inspect', '--format', '{{.Id}}', 'admirra-' + service + ':' + TAG]).strip(), flush=True)

AUDIT = '''
import json
import sqlalchemy as sa
from core.database import SessionLocal
with SessionLocal() as db:
    db.execute(sa.text("SET TRANSACTION READ ONLY"))
    db.execute(sa.text("SET LOCAL statement_timeout='5s'"))
    print(json.dumps({
        'schema': db.scalar(sa.text("SELECT version_num FROM alembic_version")),
        'running_sync': db.scalar(sa.text("SELECT count(*) FROM sync_jobs WHERE status='RUNNING'")),
        'sending_reports': db.scalar(sa.text("SELECT count(*) FROM report_deliveries WHERE status='sending'")),
        'recent_ai': db.scalar(sa.text("SELECT count(*) FROM ai_messages WHERE created_at > now() - interval '5 minutes'")),
        'recent_payment_intents': db.scalar(sa.text("SELECT count(*) FROM billing_events WHERE event_type='intent' AND created_at > now() - interval '10 minutes'")),
    }))
'''

def audit():
    state = runtime()
    raw = run(['docker', 'exec', '-i', 'admirra-backend-1', 'python', '-'], input=AUDIT)
    result = json.loads(next(line for line in raw.splitlines() if line.startswith('{')))
    print('Preflight:', json.dumps(result), flush=True)
    return state, result

def ready():
    code = "import urllib.request,json; p=json.load(urllib.request.urlopen('http://127.0.0.1:8001/openapi.json',timeout=3)); assert '/api/billing/cloudpayments/check' in p['paths']"
    for _ in range(30):
        try:
            run(['docker', 'exec', 'admirra-backend-1', 'python', '-c', code])
            return
        except subprocess.CalledProcessError:
            time.sleep(2)
    raise RuntimeError('Candidate API not ready')

def activate(backup_id):
    old, evidence = audit()
    if evidence['schema'] != 'cc3d4e5f6a7b' or any(v for k, v in evidence.items() if k != 'schema'):
        raise RuntimeError('Schema drift or activity; retry at a quiet moment')
    if not backup_id or not backup_id.startswith(datetime.now(timezone.utc).strftime('%Y%m%d')):
        raise RuntimeError('A verified same-day backup ID is required')
    if run(['systemctl', 'show', 'admirra-logical-backup.service', '-p', 'Result', '--value']).strip() != 'success':
        raise RuntimeError('Last backup did not complete')
    before_ids = {row['Names']: row['ID'] for row in (json.loads(line) for line in run(['docker', 'ps', '--format', '{{json .}}']).splitlines())}
    directory = Path('/etc/admirra/releases') / ('signup-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    directory.mkdir(mode=0o700, parents=True)
    private_json(directory / 'runtime-before.json', old)
    images, wanted = {}, {}
    for service in EXPECTED:
        images[service] = run(['docker', 'image', 'inspect', '--format', '{{.Id}}', 'admirra-' + service + ':' + TAG]).strip()
        source = old[service]['Config']['Labels']['com.docker.compose.project.config_files']
        if ',' in source: raise RuntimeError('Expected one literal compose source')
        config = json.loads(run(compose(source) + ['config', '--format', 'json']))
        target = config['services'][service]
        target.pop('build', None); target.pop('env_file', None)
        target['image'] = old[service]['Image']; target['environment'] = env(old[service])
        private_json(directory / (service + '-previous.json'), literal(config))
        active = deepcopy(config)
        active['services'][service]['image'] = images[service]
        if service != 'frontend':
            active['services'][service]['environment'].update(SIGNUP_DISCOUNT_ENABLED='false', SIGNUP_DISCOUNT_PILOT_USER_IDS='')
        wanted[service] = active['services'][service]['environment']
        path = directory / (service + '-active.json')
        private_json(path, literal(active))
        resolved = json.loads(run(compose(path) + ['config', '--format', 'json']))
        assert resolved['services'][service]['environment'] == wanted[service]
    private_json(directory / 'metadata.json', {'backup_id': backup_id, 'previous': EXPECTED, 'active': images})
    print('Rollback configs:', directory, flush=True)
    source = (CONTEXT / 'alembic/versions/ef1a2b3c4d5e_signup_discount.py').read_text()
    schema = '''
import sqlalchemy as sa
from core.database import engine
from alembic.migration import MigrationContext
from alembic.operations import Operations
namespace={}
exec(SOURCE, namespace)
with engine.begin() as db:
    db.execute(sa.text("SET LOCAL lock_timeout='2s'; SET LOCAL statement_timeout='15s'"))
    assert db.scalar(sa.text("SELECT version_num FROM alembic_version")) == 'cc3d4e5f6a7b'
    assert db.scalar(sa.text("SELECT pg_try_advisory_xact_lock(20260922, 20)"))
    namespace['op']=Operations(MigrationContext.configure(db))
    namespace['upgrade']()
print('Additive signup schema verified/applied; Alembic head unchanged')
'''.replace('SOURCE', repr(source))
    print(run(['docker', 'exec', '-i', 'admirra-backend-1', 'python', '-'], input=schema).strip(), flush=True)
    try:
        for service in ('backend', 'automation', 'frontend'):
            start(directory / (service + '-active.json'), service)
            if service == 'backend': ready()
        for service in EXPECTED:
            current = inspect(service)
            assert current['Image'] == images[service] and env(current) == wanted[service]
            assert current['State']['Running'] and not current['State']['Restarting']
            assert {m['Destination']: m for m in current['Mounts']} == {m['Destination']: m for m in old[service]['Mounts']}
            assert current['HostConfig']['PortBindings'] == old[service]['HostConfig']['PortBindings']
        after_ids = {row['Names']: row['ID'] for row in (json.loads(line) for line in run(['docker', 'ps', '--format', '{{json .}}']).splitlines())}
        for name, value in before_ids.items():
            if name not in {'admirra-' + service + '-1' for service in EXPECTED}:
                assert after_ids.get(name) == value, 'Unrelated container changed'
        for path in ('/', '/tariffs', '/projects', '/ai'):
            run(['curl', '-fsS', '--max-time', '15', '-o', '/dev/null', 'https://admirra.ru' + path])
        # This legacy runtime predates /api/health/ready. Check actual protected
        # routes plus a readonly ORM query, not a route from pending DevOps code.
        auth_status = run(['curl', '-sS', '--max-time', '10', '-o', '/dev/null', '-w', '%{http_code}',
                           'https://admirra.ru/api/auth/me']).strip()
        assert auth_status in {'401', '403'}
        expected_index = hashlib.sha256((CONTEXT / 'dist/index.html').read_bytes()).hexdigest()
        actual_index = run(['docker','exec','admirra-frontend-1','sha256sum','/usr/share/nginx/html/index.html']).split()[0]
        assert actual_index == expected_index
        schema_probe = "from core.database import SessionLocal; from core.models import User; import sqlalchemy as s; db=SessionLocal(); db.execute(s.text('SET TRANSACTION READ ONLY')); db.query(User).limit(1).all(); db.rollback(); print('New ORM read passed')"
        print(run(['docker','exec','admirra-backend-1','python','-c',schema_probe]).strip(), flush=True)
        status = run(['curl', '-sS', '--max-time', '10', '-o', '/dev/null', '-w', '%{http_code}', '-X', 'POST',
                      '-H', 'Content-Type: application/json', '--data', '{}', 'https://admirra.ru/api/billing/cloudpayments/check']).strip()
        assert status == '401', 'Unsigned Check must be rejected'
    except BaseException:
        rollback_errors = []
        for service in ('backend', 'automation', 'frontend'):
            try:
                start(directory / (service + '-previous.json'), service)
                assert inspect(service)['Image'] == EXPECTED[service]
            except Exception:
                rollback_errors.append(service)
        if rollback_errors:
            print('Rollback requires intervention: ' + ', '.join(rollback_errors), flush=True)
        else:
            print('Previous images restored; additive schema retained', flush=True)
        raise
    print('Release active, offers disabled globally and pilot list empty; payment settings unchanged', flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--build', action='store_true')
    mode.add_argument('--audit', action='store_true')
    mode.add_argument('--activate', action='store_true')
    parser.add_argument('--backup-id')
    args = parser.parse_args()
    with open('/var/lock/admirra-summary-release.lock', 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            if args.build: build()
            elif args.audit: audit()
            else: activate(args.backup_id)
        except Exception as error:
            print('Release blocked:', type(error).__name__, flush=True)
            raise SystemExit(1)
