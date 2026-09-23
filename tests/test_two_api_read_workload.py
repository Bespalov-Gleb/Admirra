"""Explicit higher-memory HTTP rehearsal, not part of the 1 GiB unit manifest."""
from tests.test_durable_work import pg
from tests.test_mixed_read_workload import run_mixed_read_workload


def test_two_real_apis_with_sync_and_reports(pg, monkeypatch, tmp_path):
    run_mixed_read_workload(pg, monkeypatch, tmp_path, http_replicas=True)
