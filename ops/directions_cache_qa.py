"""Isolated Redis cache regression. No production mounts/env or outbound network."""
import os
from pathlib import Path
import subprocess
import uuid


def run(*args, **kwargs):
    return subprocess.run(args, check=True, text=True, **kwargs)


def main():
    assert os.getenv('WW_TEST') == '1' and os.getenv('WW_TEST_ID')
    root = Path(__file__).resolve().parent.parent
    name = 'admirra-directions-qa-' + uuid.uuid4().hex[:8]
    image = os.environ['QA_IMAGE']
    redis_image = os.environ['QA_REDIS_IMAGE']
    run('docker', 'network', 'create', '--internal', name, capture_output=True)
    try:
        run('docker', 'run', '--pull', 'never', '-d', '--name', name, '--network', name,
            '--network-alias', 'test-redis', '--memory', '96m', '--cpus', '0.5',
            '--tmpfs', '/data:rw,size=32m', redis_image, 'redis-server', '--save', '',
            '--appendonly', 'no', capture_output=True)
        run('docker', 'run', '--pull', 'never', '--rm', '--network', name,
            '--memory', '512m', '--cpus', '1', '--read-only', '--tmpfs', '/tmp:rw,size=64m',
            '--cap-drop', 'ALL', '-e', 'WW_TEST=1', '-e', 'WW_TEST_ID=' + name,
            '-e', 'DATABASE_URL=postgresql://test:test@test-db/unused',
            '-e', 'ISOLATED_REDIS_URL=redis://test-redis:6379/15',
            '-e', 'PYTHONPATH=/qa:/app', '-v', str(root) + ':/qa:ro', '-w', '/qa',
            '--entrypoint', 'python', image, '-B', 'ops/run_isolated_tests.py',
            'tests/test_shared_read_cache.py', '--disable-warnings')
    finally:
        subprocess.run(['docker', 'rm', '-f', '-v', name], capture_output=True)
        subprocess.run(['docker', 'network', 'rm', name], capture_output=True)


if __name__ == '__main__':
    main()
