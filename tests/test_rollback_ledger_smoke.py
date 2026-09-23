import pytest
from ops.backup.rollback_ledger_smoke import isolated


@pytest.mark.parametrize('url', ['postgresql://x:y@10.77.0.1/restore',
    'postgresql://x:y@127.0.0.1/saas_project', ''])
def test_rollback_probe_refuses_any_live_or_ambiguous_target(monkeypatch, url):
    monkeypatch.setenv('WW_TEST', '1')
    monkeypatch.setenv('WW_TEST_ID', 'restore-synthetic')
    monkeypatch.setenv('DATABASE_URL', url)
    with pytest.raises(RuntimeError):
        isolated()


def test_rollback_probe_requires_explicit_restore_marker(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'postgresql://test:test@127.0.0.1:5432/restore')
    monkeypatch.setenv('WW_TEST', '1')
    monkeypatch.setenv('WW_TEST_ID', 'restore-synthetic')
    isolated()
    monkeypatch.setenv('WW_TEST_ID', 'production')
    with pytest.raises(RuntimeError):
        isolated()
