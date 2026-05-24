"""Unit-тесты RBAC, security и сервисов internal_admin."""
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException
from jose import jwt

from core import models
from internal_admin.rbac import (
    STAFF_ROLES,
    can_access_manager,
    can_access_seo,
    is_staff,
    is_superadmin,
    staff_role_label,
)
from internal_admin.security import (
    AUDIENCE,
    create_admin_access_token,
    decode_admin_token,
    hash_session_token,
    new_session_token,
)
from internal_admin.services import (
    DEFAULT_SETTINGS,
    estimate_tokens_from_text,
    get_all_settings,
    log_ai_usage,
    month_ai_cost_usd,
)
from internal_admin.usage import record_ai_call


def _user(role: models.UserRole) -> models.User:
    return models.User(email="staff@test.com", role=role)


class TestRbac:
    def test_staff_roles_set(self):
        assert models.UserRole.SUPERADMIN in STAFF_ROLES
        assert models.UserRole.MANAGER not in STAFF_ROLES

    def test_is_staff(self):
        assert is_staff(_user(models.UserRole.SUPPORT)) is True
        assert is_staff(_user(models.UserRole.MANAGER)) is False

    def test_is_superadmin_legacy_admin(self):
        assert is_superadmin(_user(models.UserRole.ADMIN)) is True
        assert is_superadmin(_user(models.UserRole.SUPERADMIN)) is True
        assert is_superadmin(_user(models.UserRole.SUPPORT)) is False

    def test_manager_access(self):
        from internal_admin.rbac import can_access_manager

        assert can_access_manager(_user(models.UserRole.STAFF_MANAGER)) is True
        assert can_access_manager(_user(models.UserRole.SUPPORT)) is True
        assert can_access_manager(_user(models.UserRole.SEO)) is False
        assert can_access_manager(_user(models.UserRole.SUPERADMIN)) is True

    def test_seo_access(self):
        assert can_access_seo(_user(models.UserRole.SEO)) is True
        assert can_access_seo(_user(models.UserRole.SUPPORT)) is False

    def test_staff_role_label(self):
        assert staff_role_label(models.UserRole.SUPPORT) == "Менеджер"
        assert staff_role_label(models.UserRole.STAFF_MANAGER) == "Менеджер"
        assert staff_role_label(models.UserRole.SUPERADMIN) == "Super Admin"


class TestSecurity:
    def test_admin_token_roundtrip(self):
        uid = uuid.uuid4()
        token = create_admin_access_token(uid, "admin@test.com", "SUPERADMIN", session_id="sess-1")
        payload = decode_admin_token(token)
        assert payload["sub"] == "admin@test.com"
        assert payload["uid"] == str(uid)
        assert payload["aud"] == AUDIENCE
        assert payload["sid"] == "sess-1"

    def test_rejects_app_token_without_admin_audience(self):
        from core.config import get_config

        cfg = get_config()
        bad = jwt.encode(
            {"sub": "admin@test.com", "aud": "other", "exp": datetime.now(timezone.utc).timestamp() + 3600},
            cfg.internal_admin.jwt_secret,
            algorithm="HS256",
        )
        with pytest.raises(HTTPException) as exc:
            decode_admin_token(bad)
        assert exc.value.status_code == 401

    def test_session_token_hash_stable(self):
        assert hash_session_token("abc") == hash_session_token("abc")
        assert hash_session_token("abc") != hash_session_token("xyz")

    def test_new_session_token_unique(self):
        assert new_session_token() != new_session_token()


class TestServices:
    def test_estimate_tokens_from_text(self):
        assert estimate_tokens_from_text("") == 0
        assert estimate_tokens_from_text("abcd") == 1
        assert estimate_tokens_from_text("a" * 40) == 10

    def test_log_ai_usage_cost(self, db):
        user = models.User(
            email="u@test.com",
            password_hash="x",
            role=models.UserRole.MANAGER,
        )
        db.add(user)
        db.commit()

        row = log_ai_usage(
            db,
            user_id=user.id,
            action="ai_chat",
            tokens_input=1000,
            tokens_output=500,
        )
        db.commit()
        assert row.tokens_total == 1500
        assert row.cost_usd == "0.0030"

    def test_get_all_settings_defaults(self, db):
        settings = get_all_settings(db)
        for key, default in DEFAULT_SETTINGS.items():
            assert key in settings
            assert settings[key] == default

    def test_month_ai_cost_usd(self, db):
        log_ai_usage(db, user_id=None, action="t", tokens_input=2000, tokens_output=0)
        db.commit()
        dt_from = datetime.now(timezone.utc).replace(year=2000)
        assert month_ai_cost_usd(db, dt_from) == 0.0

    def test_record_ai_call_swallows_errors(self, db):
        with patch("internal_admin.usage.log_ai_usage", side_effect=RuntimeError("boom")):
            record_ai_call(db, user_id=None, action="x", prompt_text="hi", response_text="bye")
