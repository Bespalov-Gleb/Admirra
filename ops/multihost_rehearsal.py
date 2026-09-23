"""Run bounded SYNTHETIC load on both hosts, never against production data.

Application image is immutable. Only the test driver/helpers are mounted.
DB lives on host 1, API on both, Redis/driver on host 2. Dedicated bridges
are egress-restricted to each other's test ports; no public ports, real keys,
real calendars, customer deliveries or charges. Always removes its resources.
"""
import argparse
import base64
import json
from pathlib import Path
import re
import shlex
import subprocess
import time

HOSTS = {1: 'root@91.221.68.90', 2: 'root@91.221.68.94'}
ROOT = '/opt/admirra-staging/multihost-final'
PREFIX = 'admr-final-'
SSH_OPTIONS = ['-o', 'BatchMode=yes', '-o', 'ConnectTimeout=12', '-o', 'ServerAliveInterval=15',
    '-o', 'ServerAliveCountMax=2', '-o', 'ControlMaster=auto', '-o', 'ControlPersist=600',
    '-o', 'ControlPath=/tmp/admr-final-ssh-%C']
PG = 'postgres:15.18-alpine@sha256:3d0f7584ed7d04e27fa050d6683a74746608faf21f202be78460d679cc56461f'
REDIS = 'redis:7.4-alpine@sha256:ff02b58f971e7d7d156a1267e283fcbbeee91773b6aa36c49dac28ecfe28eadf'


def remote(node, args, *, check=True, timeout=60):
    result = subprocess.run(['ssh', *SSH_OPTIONS,
        HOSTS[node], shlex.join([str(x) for x in args])], capture_output=True, text=True, timeout=timeout)
    if check and result.returncode:
        raise RuntimeError(f'Host {node} command failed: {result.stderr[-1500:]}')
    return (result.stdout + (result.stderr if args[:2] == ['docker', 'logs'] else '')).strip()


def rules(node):
    bridge = f'admrtest{node}'
    peer = f'10.77.0.{3-node}'
    # These rules apply ONLY to our test bridge. Existing SSH/web/private
    # services and default policy are not touched. Peer ingress is WireGuard.
    return [
        ['-m', 'conntrack', '--ctstate', 'ESTABLISHED,RELATED', '-j', 'ACCEPT'],
        ['-i', bridge, '-o', bridge, '-j', 'ACCEPT'],
        ['-i', 'admirra0', '-s', peer, '-o', bridge, '-j', 'ACCEPT'],
        ['-i', bridge, '-d', peer, '-p', 'tcp', '-m', 'multiport', '--dports',
         '26379' if node == 1 else '25432,18081', '-j', 'ACCEPT'],
        ['-j', 'DROP'],
    ]


def firewall(node, cleanup=False):
    bridge, chain = f'admrtest{node}', 'ADMR-FINAL-TEST'
    hooks = [['-i', bridge, '-j', chain], ['-o', bridge, '-j', chain]]
    if cleanup:
        for hook in hooks:
            remote(node, ['iptables', '-w', '5', '-D', 'DOCKER-USER', *hook], check=False)
        remote(node, ['iptables', '-w', '5', '-F', chain], check=False)
        remote(node, ['iptables', '-w', '5', '-X', chain], check=False)
        return
    remote(node, ['iptables', '-w', '5', '-N', chain])
    for rule in rules(node):
        remote(node, ['iptables', '-w', '5', '-A', chain, *rule])
    for hook in hooks:
        remote(node, ['iptables', '-w', '5', '-I', 'DOCKER-USER', '1', *hook])


def docker(node, name, image, args=(), env=None, options=(), memory='768m'):
    command = ['docker', 'run', '-d', '--name', PREFIX + name, '--network', PREFIX + f'net{node}',
        '--memory', memory, '--cpus', '1.5', '--pids-limit', '256',
        '--security-opt', 'no-new-privileges:true', '--cap-drop', 'ALL',
        '--tmpfs', '/tmp:size=256m', *options]
    for key, value in (env or {}).items():
        command += ['-e', f'{key}={value}']
    return remote(node, command + [image, *args])


def wait_for(fn, seconds=60):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        value = fn()
        if value:
            return value
        time.sleep(1)
    raise RuntimeError('Bounded rehearsal deadline exceeded')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', args.image):
        raise SystemExit('Immutable image required')
    local = Path(__file__).resolve().parents[1]
    args.output.mkdir(parents=True, exist_ok=True)
    owned, networks, guards = [], [], []
    started = time.time()
    try:
        for node in (1, 2):
            if remote(node, ['docker', 'ps', '-a', '--filter', f'name={PREFIX}', '--format', '{{.Names}}']):
                raise RuntimeError('Existing rehearsal containers: inspect before retry')
            remote(node, ['docker', 'image', 'inspect', args.image, '--format', '{{.Id}}'])
            if remote(node, ['iptables', '-w', '5', '-S', 'ADMR-FINAL-TEST'], check=False):
                raise RuntimeError('Existing test firewall chain; inspect before retry')
            remote(node, ['docker', 'network', 'create', '--driver', 'bridge',
                '--opt', f'com.docker.network.bridge.name=admrtest{node}', PREFIX + f'net{node}'])
            networks.append(node)
            guards.append(node)
            firewall(node)
        remote(2, ['mkdir', '-p', ROOT + '/handshake'])
        if remote(2, ['find', ROOT + '/handshake', '-type', 'f']):
            raise RuntimeError('Old handshake exists; choose/clean reviewed test state')
        remote(2, ['chmod', '777', ROOT + '/handshake'])  # Synthetic schema name only.
        for path in ('ops/multihost_driver.py', 'tests/test_mixed_read_workload.py'):
            subprocess.run(['scp', '-q', *SSH_OPTIONS, str(local / path), HOSTS[2] + ':' + ROOT + '/' + Path(path).name], check=True)
        owned.append((1, 'db'))
        docker(1, 'db', PG, ['postgres', '-c', 'max_connections=40', '-c', 'shared_buffers=128MB',
            '-c', 'max_wal_size=128MB', '-c', 'min_wal_size=32MB'],
            env={'POSTGRES_DB': 'test', 'POSTGRES_USER': 'test', 'POSTGRES_PASSWORD': 'isolated-test-only',
                'PGDATA': '/var/lib/postgresql/data/pgdata'},
            options=['--user', '70:70', '--tmpfs', '/var/lib/postgresql/data:size=768m,mode=1777', '--shm-size', '128m',
                '-p', '10.77.0.1:25432:5432'], memory='1g')
        wait_for(lambda: remote(1, ['docker', 'exec', PREFIX + 'db', 'pg_isready', '-U', 'test', '-d', 'test'], check=False).endswith('accepting connections'))
        owned.append((2, 'redis'))
        docker(2, 'redis', REDIS, ['redis-server', '--dir', '/tmp', '--maxmemory', '64mb', '--maxmemory-policy', 'noeviction'],
            options=['--user', '999:999', '--network-alias', 'test-redis', '-p', '10.77.0.2:26379:6379'], memory='192m')
        test_env = {'WW_TEST': '1', 'WW_TEST_ID': 'multihost-final',
            'DATABASE_URL': 'postgresql://test:isolated-test-only@test-db:25432/test',
            'ISOLATED_POSTGRES_URL': 'postgresql://test:isolated-test-only@test-db:25432/test',
            'ISOLATED_REDIS_URL': 'redis://test-redis:6379/15'}
        owned.append((2, 'driver'))
        docker(2, 'driver', args.image, ['python', '-m', 'ops.run_isolated_tests', '-s',
            'ops/multihost_driver.py', 'tests/test_celery_recovery.py',
            'tests/test_shared_read_cache.py', 'tests/test_assistant_streaming.py',
            'tests/test_billing_provider_work.py'],
            test_env, ['--read-only', '--user', '10001:10001', '--add-host', 'test-db:10.77.0.1',
                '-v', ROOT + '/handshake:/handshake',
                '-v', ROOT + '/multihost_driver.py:/app/ops/multihost_driver.py:ro',
                '-v', ROOT + '/test_mixed_read_workload.py:/app/tests/test_mixed_read_workload.py:ro'], memory='1g')
        raw = wait_for(lambda: remote(2, ['cat', ROOT + '/handshake/schema.json'], check=False))
        schema = json.loads(raw)['schema']
        if not re.fullmatch(r'work_[0-9a-f]{32}', schema):
            raise RuntimeError('Invalid synthetic schema')
        for node in (1, 2):
            env = {**test_env, 'DATABASE_URL': test_env['DATABASE_URL'] + '?options=-csearch_path%3D' + schema,
                'SECRET_KEY': 'isolated-tests-not-a-production-secret',
                'ENCRYPTION_KEY': base64.urlsafe_b64encode(b'0' * 32).decode(),
                'APP_PROCESS_ROLE': 'api', 'DB_AUTO_BOOTSTRAP': 'false', 'RUN_SYNC_WORKER': 'false',
                'RUN_API_SCHEDULER': 'false', 'DURABLE_TASKS': 'false', 'REDIS_ENABLED': 'false',
                'SHARED_READ_CACHE': 'false', 'SMTP_ENABLED': 'false', 'DB_POOL_SIZE': '2',
                'DB_MAX_OVERFLOW': '0', 'DB_POOL_TIMEOUT': '5', 'LOG_TO_STDOUT': 'true',
                'UPLOADS_DIR': '/tmp/uploads', 'REJECTED_LEADS_DIR': '/tmp/rejected'}
            options = ['--read-only', '--user', '10001:10001', '--add-host', 'test-db:10.77.0.1']
            if node == 1:
                # Local DB is reached directly in this isolated bridge.
                env['DATABASE_URL'] = env['DATABASE_URL'].replace('test-db:25432', PREFIX + 'db:5432')
                options += ['-p', '10.77.0.1:18081:8001']
            else:
                options += ['--network-alias', 'test-api2']
            owned.append((node, f'api{node}'))
            docker(node, f'api{node}', args.image, ['uvicorn', 'backend_api.main:app', '--host', '0.0.0.0',
                '--port', '8001', '--no-access-log'], env, options)
            wait_for(lambda: remote(node, ['docker', 'exec', PREFIX + f'api{node}', 'python', '-c',
                "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8001/api/health/live',timeout=2).status)"], check=False) == '200')
        remote(2, ['touch', ROOT + '/handshake/ready.json'])
        deadline = time.monotonic() + 300
        samples = []
        while time.monotonic() < deadline:
            for node in (1, 2):
                names = [PREFIX + name for n, name in owned if n == node]
                samples.append({'node': node, 'at': time.time(), 'stats': remote(node,
                    ['docker', 'stats', '--no-stream', '--format', '{{json .}}', *names])})
            state = json.loads(remote(2, ['docker', 'inspect', PREFIX + 'driver', '--format', '{{json .State}}']))
            if not state['Running']:
                break
        else:
            raise RuntimeError('Mixed-load timeout')
        log = remote(2, ['docker', 'logs', PREFIX + 'driver'])
        (args.output / 'mixed.log').write_text(log)
        (args.output / 'resources.json').write_text(json.dumps(samples, indent=2))
        if state['ExitCode'] != 0 or 'MIXED_READ_EVIDENCE ' not in log:
            raise RuntimeError('Mixed-load failed; see saved evidence')
        print(next(line for line in log.splitlines() if line.startswith('MIXED_READ_EVIDENCE ')))
        print(f'Two-host synthetic mixed-load passed in {time.time()-started:.1f}s; providers were controlled stubs')
    finally:
        for node, name in reversed(owned):
            log = remote(node, ['docker', 'logs', PREFIX + name], check=False)
            (args.output / f'{node}-{name}.log').write_text(log)
            remote(node, ['docker', 'rm', '-f', PREFIX + name], check=False)
        if (2, 'driver') in owned:
            remote(2, ['rm', '-f', ROOT + '/handshake/schema.json', ROOT + '/handshake/ready.json'], check=False)
        for node in networks:
            remote(node, ['docker', 'network', 'rm', PREFIX + f'net{node}'], check=False)
        for node in guards:
            firewall(node, cleanup=True)


if __name__ == '__main__':
    main()
