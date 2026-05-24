"""HTTP-тесты API internal_admin (/api/admin/*)."""
import uuid

from core import models
from tests.conftest import admin_auth_header, make_user


class TestAdminAuth:
    def test_login_success(self, client, db):
        make_user(db, email="super@test.com", role=models.UserRole.SUPERADMIN)
        r = client.post("/api/admin/auth/login", json={"email": "super@test.com", "password": "secret123"})
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert data["role"] == "SUPERADMIN"

    def test_login_rejects_saas_manager(self, client, db):
        make_user(db, email="user@test.com", role=models.UserRole.MANAGER)
        r = client.post("/api/admin/auth/login", json={"email": "user@test.com", "password": "secret123"})
        assert r.status_code == 403

    def test_login_rejects_bad_password(self, client, db):
        make_user(db, email="super@test.com", role=models.UserRole.SUPERADMIN)
        r = client.post("/api/admin/auth/login", json={"email": "super@test.com", "password": "wrong"})
        assert r.status_code == 401

    def test_me_requires_auth(self, client):
        assert client.get("/api/admin/auth/me").status_code == 401

    def test_me_returns_permissions(self, client, db):
        staff = make_user(db, email="manager@test.com", role=models.UserRole.STAFF_MANAGER)
        r = client.get("/api/admin/auth/me", headers=admin_auth_header(staff))
        assert r.status_code == 200
        body = r.json()
        assert body["permissions"]["manager"] is True
        assert body["permissions"]["superadmin"] is False

    def test_logout(self, client, db):
        staff = make_user(db, email="super@test.com", role=models.UserRole.SUPERADMIN)
        r = client.post("/api/admin/auth/logout", headers=admin_auth_header(staff))
        assert r.status_code == 200
        assert r.json()["ok"] is True


class TestAdminRbacEndpoints:
    def test_dashboard_superadmin_only(self, client, db):
        superadmin = make_user(db, email="super@test.com", role=models.UserRole.SUPERADMIN)
        manager = make_user(db, email="manager@test.com", role=models.UserRole.STAFF_MANAGER)

        assert client.get("/api/admin/dashboard/overview", headers=admin_auth_header(superadmin)).status_code == 200
        assert client.get("/api/admin/dashboard/overview", headers=admin_auth_header(manager)).status_code == 403

    def test_seo_blog_stats_access(self, client, db):
        seo = make_user(db, email="seo@test.com", role=models.UserRole.SEO)
        r = client.get("/api/seo/articles/summary", headers=admin_auth_header(seo))
        assert r.status_code == 200
        assert "published_count" in r.json()

    def test_settings_superadmin_only(self, client, db):
        superadmin = make_user(db, email="super@test.com", role=models.UserRole.SUPERADMIN)
        seo = make_user(db, email="seo@test.com", role=models.UserRole.SEO)
        assert client.get("/api/admin/settings", headers=admin_auth_header(superadmin)).status_code == 200
        assert client.get("/api/admin/settings", headers=admin_auth_header(seo)).status_code == 403


class TestAdminUsers:
    def test_list_saas_users(self, client, db):
        superadmin = make_user(db, email="super@test.com", role=models.UserRole.SUPERADMIN)
        make_user(db, email="client@test.com", role=models.UserRole.MANAGER, first_name="Ivan")
        r = client.get("/api/admin/users", headers=admin_auth_header(superadmin))
        assert r.status_code == 200
        emails = [u["email"] for u in r.json()["items"]]
        assert "client@test.com" in emails
        assert "super@test.com" not in emails

    def test_block_and_unblock_user(self, client, db):
        superadmin = make_user(db, email="super@test.com", role=models.UserRole.SUPERADMIN)
        saas = make_user(db, email="blocked@test.com", role=models.UserRole.MANAGER)

        block = client.post(
            f"/api/admin/users/{saas.id}/block",
            headers=admin_auth_header(superadmin),
            json={"reason": "Нарушение правил"},
        )
        assert block.status_code == 200
        db.refresh(saas)
        assert saas.is_active is False

        unblock = client.post(f"/api/admin/users/{saas.id}/unblock", headers=admin_auth_header(superadmin))
        assert unblock.status_code == 200
        db.refresh(saas)
        assert saas.is_active is True


class TestManagerPanel:
    def test_manager_sees_all_users(self, client, db):
        manager = make_user(db, email="manager@test.com", role=models.UserRole.STAFF_MANAGER)
        make_user(db, email="client1@test.com", role=models.UserRole.MANAGER)
        make_user(db, email="client2@test.com", role=models.UserRole.MANAGER)

        r = client.get("/api/manager/users", headers=admin_auth_header(manager))
        assert r.status_code == 200
        emails = {u["email"] for u in r.json()["items"]}
        assert "client1@test.com" in emails
        assert "client2@test.com" in emails

    def test_manager_note_on_client(self, client, db):
        manager = make_user(db, email="manager@test.com", role=models.UserRole.STAFF_MANAGER)
        client_user = make_user(db, email="client@test.com", role=models.UserRole.MANAGER)

        r = client.post(
            f"/api/manager/users/{client_user.id}/notes",
            headers=admin_auth_header(manager),
            json={"body": "Позвонить завтра"},
        )
        assert r.status_code == 200
        assert r.json()["body"] == "Позвонить завтра"


class TestAdminSeo:
    def test_create_and_list_blog_post(self, client, db):
        seo = make_user(db, email="seo@test.com", role=models.UserRole.SEO)
        headers = admin_auth_header(seo)

        created = client.post(
            "/api/seo/articles",
            headers=headers,
            json={
                "slug": "testovaya-statya",
                "title": "Тестовая статья",
                "content_html": "<p>Hello</p>",
            },
        )
        assert created.status_code == 200
        post_id = created.json()["id"]

        listed = client.get("/api/seo/articles", headers=headers)
        assert listed.status_code == 200
        ids = [p["id"] for p in listed.json()["items"]]
        assert post_id in ids

    def test_patch_site_page(self, client, db):
        from internal_admin.bootstrap import ensure_default_seo_pages

        seo = make_user(db, email="seo@test.com", role=models.UserRole.SEO)
        ensure_default_seo_pages(db)

        pages = client.get("/api/seo/pages", headers=admin_auth_header(seo))
        assert pages.status_code == 200
        home = next(p for p in pages.json()["items"] if p["path"] == "/")

        patched = client.patch(
            f"/api/seo/pages/{home['id']}",
            headers=admin_auth_header(seo),
            json={"meta_title": "AdMirra — главная", "meta_description": "Описание главной"},
        )
        assert patched.status_code == 200
        assert patched.json()["ok"] is True

        pages_after = client.get("/api/seo/pages", headers=admin_auth_header(seo))
        home_after = next(p for p in pages_after.json()["items"] if p["path"] == "/")
        assert home_after["meta_title"] == "AdMirra — главная"


class TestAdminSettings:
    def test_patch_settings(self, client, db):
        superadmin = make_user(db, email="super@test.com", role=models.UserRole.SUPERADMIN)
        headers = admin_auth_header(superadmin)

        r = client.patch(
            "/api/admin/settings",
            headers=headers,
            json={"maintenance_mode": True, "trial_days": 21},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["maintenance_mode"] is True
        assert body["trial_days"] == 21


class TestPublicAuthAnd2fa:
    def test_public_invite_accept(self, client, db):
        from internal_admin.services.staff_invite import invite_staff

        superadmin = make_user(db, email="super@test.com", role=models.UserRole.SUPERADMIN)
        user, raw = invite_staff(
            db,
            email="newstaff@test.com",
            first_name="New",
            last_name="Staff",
            role=models.UserRole.SEO,
            invited_by=superadmin.id,
        )
        db.commit()

        r = client.post("/api/auth/invite/accept", json={"token": raw, "password": "newpass123"})
        assert r.status_code == 200
        assert r.json()["role"] == "SEO"
        db.refresh(user)
        assert user.staff_status == models.StaffStatus.ACTIVE

    def test_2fa_enable_flow(self, client, db):
        staff = make_user(db, email="staff2fa@test.com", role=models.UserRole.STAFF_MANAGER)
        headers = admin_auth_header(staff)

        started = client.post("/api/auth/2fa/enable", headers=headers)
        assert started.status_code == 200
        secret = started.json()["secret"]

        import pyotp

        code = pyotp.TOTP(secret).now()
        confirmed = client.post(
            "/api/auth/2fa/verify",
            headers=headers,
            json={"code": code, "setup_confirm": True},
        )
        assert confirmed.status_code == 200
        assert len(confirmed.json()["recovery_codes"]) == 10


class TestAdminTzEndpoints:
    def test_admin_events_and_audit(self, client, db):
        superadmin = make_user(db, email="super@test.com", role=models.UserRole.SUPERADMIN)
        headers = admin_auth_header(superadmin)
        assert client.get("/api/admin/events", headers=headers).status_code == 200
        assert client.get("/api/admin/audit-log", headers=headers).status_code == 200
        assert client.get("/api/admin/sessions", headers=headers).status_code == 200
        assert client.get("/api/admin/integrations", headers=headers).status_code == 200

    def test_manager_staff_and_integrations(self, client, db):
        manager = make_user(db, email="mgr@test.com", role=models.UserRole.STAFF_MANAGER)
        headers = admin_auth_header(manager)
        assert client.get("/api/manager/staff", headers=headers).status_code == 200
        r = client.get("/api/manager/integrations", headers=headers)
        assert r.status_code == 200
        for provider in r.json()["providers"]:
            assert "spend_usd_month" not in provider


class TestAdminDisabled:
    def test_returns_404_when_disabled(self, client, db, monkeypatch):
        from core.config import get_config

        cfg = get_config()
        monkeypatch.setattr(cfg.internal_admin, "enabled", False)
        make_user(db, email="super@test.com", role=models.UserRole.SUPERADMIN)
        r = client.post("/api/admin/auth/login", json={"email": "super@test.com", "password": "secret123"})
        assert r.status_code == 404
