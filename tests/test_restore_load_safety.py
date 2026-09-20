import pytest

from ops.backup.api_load_smoke import assert_isolated_restore, selected_user_email


@pytest.fixture
def isolated(monkeypatch):
    monkeypatch.setenv("WW_TEST", "1")
    monkeypatch.setenv("WW_TEST_ID", "restore-synthetic")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@127.0.0.1:5432/restore")


def test_isolated_restore_is_accepted(isolated):
    assert_isolated_restore()


@pytest.mark.parametrize("key,value", [
    ("WW_TEST", "0"), ("WW_TEST_ID", "production"),
    ("DATABASE_URL", "postgresql://test:test@database:5432/restore"),
    ("DATABASE_URL", "postgresql://test:test@127.0.0.1:5432/production"),
])
def test_non_restore_target_rejected_before_sql(isolated, monkeypatch, key, value):
    monkeypatch.setenv(key, value)
    with pytest.raises(RuntimeError, match="isolated restore"):
        selected_user_email()


def test_account_must_be_explicit_before_sql(isolated, monkeypatch):
    monkeypatch.delenv("ADMIRRA_TEST_ACCOUNT_EMAIL", raising=False)
    with pytest.raises(RuntimeError, match="approved test account"):
        selected_user_email()
