"""Synthetic two-host acceptance driver; no production credentials or provider calls.

Run via ops.run_isolated_tests on the private rehearsal network. A host-side
orchestrator starts the two immutable APIs after reading schema.json and writes
ready.json. No code or commands are accepted through that handshake.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import time

import httpx

from tests.test_durable_work import pg
from tests import test_mixed_read_workload as mixed


@contextmanager
def external_apis(engine, schema, tmp_path):
    assert os.getenv('WW_TEST') == '1' and os.getenv('WW_TEST_ID') == 'multihost-final'
    assert re.fullmatch(r'work_[0-9a-f]{32}', schema)
    root = Path('/handshake')
    assert not (root / 'schema.json').exists() and not (root / 'ready.json').exists()
    (root / 'schema.json').write_text(json.dumps({'schema': schema}))
    deadline = time.monotonic() + 100
    while not (root / 'ready.json').exists():
        if time.monotonic() > deadline:
            raise AssertionError('Remote API startup deadline exceeded')
        time.sleep(.2)
    endpoints = ['http://10.77.0.1:18081', 'http://test-api2:8001']
    for endpoint in endpoints:
        assert httpx.get(endpoint + '/api/health/live', timeout=5, trust_env=False).status_code == 200
    yield endpoints


def test_real_two_host_mixed_read(pg, monkeypatch, tmp_path):
    monkeypatch.setattr(mixed, 'http_apis', external_apis)
    mixed.run_mixed_read_workload(pg, monkeypatch, tmp_path, http_replicas=True, iterations=150)
