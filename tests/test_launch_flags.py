"""The reviewed launch profile must be identical on both APIs and workers.

This tests prepared configuration, not deployed state or provider availability.
"""
import json
from pathlib import Path

import pytest

from core.runtime import get_runtime


def profile():
    return json.loads((Path(__file__).parents[1] / 'ops/launch_flags.json').read_text())


@pytest.mark.parametrize('role', ['api', 'worker', 'scheduler'])
def test_launch_profile_has_no_legacy_producer_or_schema_writer(role):
    runtime = get_runtime(dict(profile(), APP_PROCESS_ROLE=role))
    assert runtime.role == role
    assert not runtime.auto_bootstrap and not runtime.sync_worker and not runtime.api_scheduler


def test_launch_profile_keeps_irreversible_guards_and_defers_cache_expansion():
    flags = profile()
    for name in ('DURABLE_TASKS', 'REPORT_DELIVERY_GUARDS', 'BILLING_PROVIDER_QUEUE',
                 'LEAD_DELIVERY_GUARDS', 'DURABLE_REPORT_LINKS', 'DURABLE_REPORT_FILES',
                 'SHARED_REPORT_ARTIFACTS', 'DISTRIBUTED_RATE_LIMITS'):
        assert flags[name] == 'true'
    assert flags['SHARED_READ_CACHE'] == 'false'
    assert flags['AI_PREWARM_ENABLED'] == 'false'
    assert flags['LEGACY_REPORT_LINK_READS'] == 'true'
    assert all(value in ('true', 'false') for value in flags.values())


@pytest.mark.parametrize('role', ['legacy', 'sync'])
def test_launch_profile_refuses_old_producer_roles(role):
    with pytest.raises(ValueError):
        get_runtime(dict(profile(), APP_PROCESS_ROLE=role))
