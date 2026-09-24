"""Prepare root-only launch configs; never start, migrate or stop a service.

API1 takes business settings from its running container, never a newer .env.
Transfer `export-api-env` stdout directly over SSH to API2 `api2` stdin:
it contains secrets and MUST NOT be shown or saved on the operator workstation.
"""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlsplit


def capture(args):
    return subprocess.check_output(args, text=True, stderr=subprocess.PIPE)


def literal(value):
    if isinstance(value, str):
        return value.replace('$', '$$')
    if isinstance(value, dict):
        return {k: literal(v) for k, v in value.items()}
    if isinstance(value, list):
        return [literal(v) for v in value]
    return value


def env_file(path):
    path = Path(path)
    if path.is_symlink() or path.stat().st_uid != 0 or path.stat().st_mode & 0o077:
        raise ValueError('Runtime credentials must be root-owned and private')
    lines = [line for line in path.read_text().splitlines() if line and not line.startswith('#')]
    result = dict(line.split('=', 1) for line in lines)
    if len(result) != len(lines):
        raise ValueError('Duplicate runtime settings')
    return result


def private_json(path, value):
    with os.fdopen(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'w') as stream:
        json.dump(value, stream)


def inspect_config(name):
    runtime = json.loads(capture(['docker', 'inspect', name]))[0]
    labels = runtime['Config']['Labels']
    paths = labels['com.docker.compose.project.config_files'].split(',')
    command = ['docker', 'compose', '-p', labels['com.docker.compose.project']]
    for path in paths:
        command += ['-f', path]
    config = json.loads(capture(command + ['config', '--format', 'json']))
    service = labels['com.docker.compose.service']
    env = dict(item.split('=', 1) for item in runtime['Config']['Env'])
    # Preserve exact current env/image for rollback, not re-expanded .env values.
    config['services'][service]['environment'] = env
    config['services'][service]['image'] = runtime['Image']
    config['services'][service].pop('build', None)
    config['services'][service].pop('env_file', None)
    return runtime, config, service, labels['com.docker.compose.project']


def api_environment(business, db, redis, flags, release, *, local_database=False):
    if set(db) != {'DATABASE_URL'}:
        raise ValueError('Unexpected API DB credential fields')
    url = urlsplit(db['DATABASE_URL'])
    if (url.hostname, url.username, url.path) != ('10.77.0.1', 'admirra_api', '/saas_project'):
        raise ValueError('API must use private restricted database role')
    if set(redis) != {'CELERY_BROKER_URL', 'RATE_LIMIT_REDIS_URL', 'READ_CACHE_REDIS_URL', 'TASK_BROKER_PREFIX'}:
        raise ValueError('Unexpected Redis fields')
    for key, username, port in [('CELERY_BROKER_URL', 'broker_api', 6379),
                               ('RATE_LIMIT_REDIS_URL', 'limiter_api', 6379),
                               ('READ_CACHE_REDIS_URL', 'cache_api', 6380)]:
        parsed = urlsplit(redis[key])
        if (parsed.hostname, parsed.username, parsed.port) != ('10.77.0.2', username, port):
            raise ValueError('Unexpected private API Redis destination')
    if redis['TASK_BROKER_PREFIX'] != 'admirra:task:':
        raise ValueError('Unexpected task prefix')
    env = dict(business, **db, **redis, **flags)
    if local_database:
        # API1 and PostgreSQL already share admirra_default. Going out through
        # this host's published WireGuard address hairpins through Docker and
        # is not the tested inter-host gateway path. Keep the restricted role,
        # but use the existing internal DB service, without opening any ports.
        env['DATABASE_URL'] = url._replace(
            netloc=url.netloc.rsplit('@', 1)[0] + '@db:5432').geturl()
    env.pop('API_ONLY_REPLICA', None)  # Legacy canary patch is not a new role.
    env.update(APP_PROCESS_ROLE='api', APP_RELEASE=release,
               EXPECTED_SCHEMA_REVISION='f68b92a3b4c5', DB_POOL_SIZE='5',
               DB_MAX_OVERFLOW='0', DB_POOL_TIMEOUT='5',
               DB_STATEMENT_TIMEOUT_MS='60000', DB_LOCK_TIMEOUT_MS='10000',
               PYTHONDONTWRITEBYTECODE='1', UPLOADS_DIR='/app/uploads',
               REJECTED_LEADS_DIR='/data/rejected-leads',
               ARTIFACT_BASE_URL='https://10.77.0.1:9443',
               ARTIFACT_CA_FILE='/run/artifact/ca.crt',
               ARTIFACT_CERT_FILE='/run/artifact/client.crt',
               ARTIFACT_KEY_FILE='/run/artifact/client.key',
               ARTIFACT_TOKEN_FILE='/run/artifact/token')
    for key in ('SECRET_KEY', 'ENCRYPTION_KEY', 'UNISENDER_API_KEY'):
        if not env.get(key):
            raise ValueError('Missing shared application credential')
    from core.runtime import get_runtime
    if get_runtime(env).role != 'api':
        raise ValueError('Unexpected runtime role')
    return env


def save_checked(root, name, config, service, expected_env, project):
    path = root / (name + '.json')
    private_json(path, literal(config))
    resolved = json.loads(capture(['docker', 'compose', '-p', project, '-f', str(path),
                                   'config', '--format', 'json']))
    if resolved['services'][service]['environment'] != expected_env:
        raise ValueError('Literal Compose roundtrip mismatch')
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['api1', 'api2', 'workers', 'export-api-env'])
    parser.add_argument('--image')
    parser.add_argument('--release')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise ValueError('Root required')
    if args.action == 'export-api-env':
        path = args.out / 'api-business-env.json'
        if path.stat().st_mode & 0o077:
            raise ValueError('Private source required')
        sys.stdout.write(path.read_text())
        return
    if not re.fullmatch(r'[a-f0-9]{7,40}', args.release or ''):
        raise ValueError('Explicit release required')
    image = capture(['docker', 'image', 'inspect', '--format', '{{.Id}}', args.image]).strip()
    if not re.fullmatch(r'sha256:[a-f0-9]{64}', image):
        raise ValueError('Immutable image required')
    args.out.mkdir(parents=True, mode=0o700, exist_ok=True)
    if args.out.is_symlink() or args.out.stat().st_mode & 0o077:
        raise ValueError('Private output directory required')
    source = Path(__file__).resolve().parent
    flags = json.loads((source / 'launch_flags.json').read_text())
    if args.action == 'workers':
        # Resolve the prepared mounts/networks with the tested immutable image.
        process_env = dict(os.environ, ADMIRRA_IMAGE=image, ADMIRRA_SCHEMA_REVISION='f68b92a3b4c5')
        config = json.loads(subprocess.check_output(
            ['docker', 'compose', '-f', str(source / 'compose.workers.yml'), 'config', '--format', 'json'],
            env=process_env, text=True, stderr=subprocess.PIPE))
        from core.runtime import get_runtime
        for name in ('sync-manual', 'sync-nightly', 'reports', 'maintenance', 'scheduler'):
            service = config['services'][name]
            service['environment'].update(flags, APP_RELEASE=args.release)
            role = 'scheduler' if name == 'scheduler' else 'worker'
            if get_runtime(service['environment']).role != role:
                raise ValueError('Worker role mismatch')
            service.pop('env_file', None)
        path = args.out / 'workers-prepared.json'
        private_json(path, literal(config))
        resolved = json.loads(capture(['docker', 'compose', '-p', 'admirra-workers', '-f', str(path), 'config', '--format', 'json']))
        for name in config['services']:
            if resolved['services'][name].get('environment') != config['services'][name].get('environment'):
                raise ValueError('Worker environment roundtrip mismatch')
        print('Prepared workers/scheduler configuration; no services started')
        return
    container = 'admirra-backend-1' if args.action == 'api1' else 'admirra-api2-api-1'
    runtime, previous, service_name, project = inspect_config(container)
    private_json(args.out / (args.action + '-runtime-before.json'), runtime)
    private_json(args.out / (args.action + '-previous.json'), literal(previous))
    if args.action == 'api1':
        business = previous['services'][service_name]['environment']
        private_json(args.out / 'api-business-env.json', business)
    else:
        raw = sys.stdin.read(131073)
        if len(raw) > 131072:
            raise ValueError('API environment too large')
        business = json.loads(raw)
        old_env = previous['services'][service_name]['environment']
        if any(old_env.get(key) != business.get(key) for key in ('SECRET_KEY', 'ENCRYPTION_KEY')):
            raise ValueError('Cross-replica auth/encryption mismatch')
    env = api_environment(business, env_file('/etc/admirra/db-api.env'),
                          env_file('/etc/admirra/redis-api.env'), flags, args.release,
                          local_database=args.action == 'api1')
    active = deepcopy(previous)
    service = active['services'][service_name]
    service.update(image=image, environment=env)
    volumes = [v for v in service.get('volumes', []) if v['target'] not in
               {'/app/uploads', '/run/artifact', '/data/rejected-leads'}]
    volumes.append({'type': 'bind', 'source': '/etc/admirra/artifact-' + args.action,
                    'target': '/run/artifact', 'read_only': True})
    if args.action == 'api1':
        volumes += [{'type': 'bind', 'source': '/root/Admirra/uploads', 'target': '/app/uploads'},
                    {'type': 'bind', 'source': '/srv/admirra/rejected-leads', 'target': '/data/rejected-leads'}]
    else:
        for name, export, target in [('shared-api-uploads', 'uploads', '/app/uploads'),
                                      ('shared-api-rejected', 'rejected-leads', '/data/rejected-leads')]:
            active.setdefault('volumes', {})[name] = {'driver': 'local', 'driver_opts': {
                'type': 'nfs', 'o': 'addr=10.77.0.1,nfsvers=4.2,proto=tcp,hard,nosuid,nodev,noexec',
                'device': ':/' + export}}
            volumes.append({'type': 'volume', 'source': name, 'target': target, 'volume': {'nocopy': True}})
    service['volumes'] = volumes
    save_checked(args.out, args.action + '-prepared', active, service_name, env, project)
    print('Prepared ' + args.action + ' configuration; no service started')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # Command failures can contain rendered secrets. Keep stdout sanitized.
        print('Runtime preparation failed: ' + type(exc).__name__, file=sys.stderr)
        raise SystemExit(1)
