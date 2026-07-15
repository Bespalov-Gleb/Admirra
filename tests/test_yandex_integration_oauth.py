from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import HTTPException

from backend_api import integrations


def test_yandex_authorize_url_is_code_flow_with_bound_state_and_account_choice():
    with patch.object(integrations, "YANDEX_CLIENT_ID", "test-client"), patch.object(
        integrations, "YANDEX_AUTH_URL", "https://oauth.yandex.ru/authorize"
    ):
        url = integrations._build_yandex_authorize_url(
            "https://admirra.ru/auth/yandex/callback", "one-time-state"
        )

    query = parse_qs(urlparse(url).query)
    assert query["response_type"] == ["code"]
    assert query["client_id"] == ["test-client"]
    assert query["redirect_uri"] == ["https://admirra.ru/auth/yandex/callback"]
    assert "scope" not in query
    assert query["force_confirm"] == ["yes"]
    assert query["state"] == ["one-time-state"]


def test_yandex_organization_authorize_url_requests_business_scope():
    with patch.object(integrations, "YANDEX_ORG_CLIENT_ID", "org-client"), patch.object(
        integrations, "YANDEX_AUTH_URL", "https://oauth.yandex.ru/authorize"
    ):
        url = integrations._build_yandex_authorize_url(
            "https://admirra.ru/auth/yandex/callback", "one-time-state", as_org=True
        )

    query = parse_qs(urlparse(url).query)
    assert query["response_type"] == ["code"]
    assert query["client_id"] == ["org-client"]
    assert query["scope"] == ["passport:business"]
    assert query["force_confirm"] == ["yes"]


def test_yandex_organization_login_is_recognized():
    assert integrations._is_yandex_organization_login("porg-example")
    assert integrations._is_yandex_organization_login(" PORG-example ")
    assert not integrations._is_yandex_organization_login("ordinary-yandex-login")


def test_yandex_redirect_is_limited_to_active_deployment_callback():
    with patch.object(integrations, "resolve_frontend_url", return_value="https://admirra.ru"):
        assert integrations._validate_yandex_integration_redirect_uri(
            "https://admirra.ru/auth/yandex/callback/"
        ) == "https://admirra.ru/auth/yandex/callback"
        with pytest.raises(HTTPException, match="Redirect URI"):
            integrations._validate_yandex_integration_redirect_uri(
                "https://admirra.online/auth/yandex/callback"
            )


def test_yandex_state_hash_is_stable_but_does_not_equal_raw_state():
    raw_state = "state-that-never-belongs-in-the-database"
    state_hash = integrations._yandex_integration_state_hash(raw_state)
    assert state_hash == integrations._yandex_integration_state_hash(raw_state)
    assert state_hash != raw_state
    assert len(state_hash) == 64
