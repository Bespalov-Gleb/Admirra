import pytest

from core.runtime import env_bool, env_int, get_runtime


def test_legacy_is_backward_compatible():
    r = get_runtime({})
    assert r.auto_bootstrap and r.sync_worker and r.api_scheduler


@pytest.mark.parametrize("role", ["api", "scheduler", "test"])
def test_explicit_roles_have_no_embedded_side_effects(role):
    r = get_runtime({"APP_PROCESS_ROLE": role})
    assert not r.auto_bootstrap and not r.sync_worker and not r.api_scheduler


def test_worker_is_not_a_scheduler_or_schema_migrator():
    r = get_runtime({"APP_PROCESS_ROLE": "sync"})
    assert r.sync_worker and not r.auto_bootstrap and not r.api_scheduler


@pytest.mark.parametrize("key", ["DB_AUTO_BOOTSTRAP", "RUN_SYNC_WORKER", "RUN_API_SCHEDULER"])
def test_api_cannot_accidentally_enable_legacy_side_effects(key):
    with pytest.raises(ValueError):
        get_runtime({"APP_PROCESS_ROLE": "api", key: "true"})


def test_bad_configuration_fails_closed():
    with pytest.raises(ValueError):
        get_runtime({"APP_PROCESS_ROLE": "ap1"})
    with pytest.raises(ValueError):
        env_bool("FLAG", False, {"FLAG": "tru"})
    with pytest.raises(ValueError):
        get_runtime({"APP_PROCESS_ROLE": "api", "CONSUMER_REFRESH_ENABLED": "true"})


def test_pool_bounds(monkeypatch):
    monkeypatch.setenv("DB_POOL_SIZE", "0")
    with pytest.raises(ValueError):
        env_int("DB_POOL_SIZE", 5, 1, 100)
    monkeypatch.setenv("DB_POOL_SIZE", "5")
    assert env_int("DB_POOL_SIZE", 20, 1, 100) == 5
