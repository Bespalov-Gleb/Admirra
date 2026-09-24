import json
from pathlib import Path

import pytest

from ops.render_launch_runtime import api_environment, literal


def inputs():
    return (
        {'SECRET_KEY': 'synthetic', 'ENCRYPTION_KEY': 'synthetic',
         'UNISENDER_API_KEY': 'synthetic', 'SMTP_PASSWORD': 'literal$secret',
         'DATABASE_URL': 'postgresql://postgres:old@db/saas_project',
         'API_ONLY_REPLICA': 'true', 'RUN_SYNC_WORKER': 'true',
         'APP_RELEASE': 'old', 'APP_PROCESS_ROLE': 'legacy'},
        {'DATABASE_URL': 'postgresql://admirra_api:synthetic@10.77.0.1:5432/saas_project'},
        {'CELERY_BROKER_URL': 'redis://broker_api:synthetic@10.77.0.2:6379/0',
         'RATE_LIMIT_REDIS_URL': 'redis://limiter_api:synthetic@10.77.0.2:6379/0',
         'READ_CACHE_REDIS_URL': 'redis://cache_api:synthetic@10.77.0.2:6380/0',
         'TASK_BROKER_PREFIX': 'admirra:task:'},
        json.loads((Path(__file__).parents[1] / 'ops/launch_flags.json').read_text()),
        '2ce9513',
    )


def test_role_database_flags_override_old_env_without_changing_business_secrets():
    args = inputs()
    result = api_environment(*args)
    assert result['APP_RELEASE'] == '2ce9513'
    assert result['APP_PROCESS_ROLE'] == 'api'
    assert result['RUN_SYNC_WORKER'] == result['RUN_API_SCHEDULER'] == 'false'
    assert result['DURABLE_TASKS'] == 'true'
    assert result['DATABASE_URL'] == args[1]['DATABASE_URL']
    assert result['SMTP_PASSWORD'] == 'literal$secret'
    assert result['EXPECTED_SCHEMA_REVISION'] == 'f68b92a3b4c5'
    assert 'API_ONLY_REPLICA' not in result
    assert args[0]['APP_PROCESS_ROLE'] == 'legacy'


@pytest.mark.parametrize('source,key,value', [
    (1, 'DATABASE_URL', 'postgresql://postgres:synthetic@10.77.0.1:5432/saas_project'),
    (1, 'DATABASE_URL', 'postgresql://admirra_api:synthetic@public.example:5432/saas_project'),
    (1, 'UNEXPECTED', 'x'),
    (2, 'CELERY_BROKER_URL', 'redis://broker_worker:synthetic@10.77.0.2:6379/0'),
    (2, 'READ_CACHE_REDIS_URL', 'redis://cache_api:synthetic@10.77.0.2:6379/0'),
    (2, 'TASK_BROKER_PREFIX', 'other:'),
    (0, 'SECRET_KEY', ''),
    (0, 'ENCRYPTION_KEY', ''),
    (0, 'UNISENDER_API_KEY', ''),
    (3, 'RUN_SYNC_WORKER', 'true'),
])
def test_invalid_runtime_is_rejected(source, key, value):
    args = inputs()
    args[source][key] = value
    with pytest.raises(ValueError):
        api_environment(*args)


def test_compose_literals_preserve_dollars_in_nested_settings():
    value = {'environment': {'KEY': '$a${OTHER}$$'}, 'command': ['echo', '$HOME'], 'n': 1}
    assert literal(value) == {
        'environment': {'KEY': '$$a$${OTHER}$$$$'}, 'command': ['echo', '$$HOME'], 'n': 1}
    assert value['environment']['KEY'] == '$a${OTHER}$$'
