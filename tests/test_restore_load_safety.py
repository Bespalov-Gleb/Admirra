import pytest

from ops.backup.api_load_smoke import assert_isolated_restore, selected_user_email, response_profile
import json


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


@pytest.mark.parametrize('label', ['clients', 'project_cards', 'project_tree'])
def test_profile_outputs_counts_not_customer_data(label):
    rows = [{'name': 'private-project', 'integrations': [{'account_id': 'private-account',
        'campaigns': [{'name': 'private-campaign', 'id': 'private-id'}]}]}]
    body = {'root_projects': [], 'folders': [{'projects': rows}]} if label == 'project_tree' else rows
    result = response_profile(label, json.dumps(body).encode())
    assert result['projects'] == result['integrations'] == result['campaigns'] == 1
    assert result['campaign_json_bytes'] > 0
    assert 'private' not in str(result)
    assert response_profile('auth', b'not parsed') == {}
