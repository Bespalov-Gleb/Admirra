from pathlib import Path


def test_internal_admin_package_separate_from_backend_api():
    root = Path(__file__).resolve().parents[1]
    assert (root / "internal_admin" / "router.py").is_file()
    assert not (root / "backend_api" / "admin.py").exists()


def test_internal_admin_routes_present():
    root = Path(__file__).resolve().parents[1]
    router_text = root.joinpath("internal_admin", "router.py").read_text(encoding="utf-8")
    manager_router_text = root.joinpath("internal_admin", "manager_router.py").read_text(encoding="utf-8")
    seo_router_text = root.joinpath("internal_admin", "seo_router.py").read_text(encoding="utf-8")
    auth_text = root.joinpath("internal_admin", "routers", "auth.py").read_text(encoding="utf-8")
    dashboard_text = root.joinpath("internal_admin", "routers", "dashboard.py").read_text(encoding="utf-8")
    manager_text = root.joinpath("internal_admin", "routers", "manager.py").read_text(encoding="utf-8")
    seo_text = root.joinpath("internal_admin", "routers", "seo.py").read_text(encoding="utf-8")

    for fragment in [
        "auth_router",
        "dashboard_router",
        "users_router",
        "staff_router",
    ]:
        assert fragment in router_text, f"missing include {fragment}"

    expected = [
        '"/login"',
        '"/me"',
        '"/users/{user_id}/impersonate"',
        '"/overview"',
        '"/users"',
        '"/users/{user_id}"',
        '"/blog/stats"',
        '"/pages"',
    ]
    assert "manager_routes" in manager_router_text
    assert 'prefix="/seo"' in seo_router_text
    combined = auth_text + dashboard_text + manager_text + seo_text
    for path in expected:
        assert path in combined, f"missing route {path}"


def test_main_includes_internal_admin_router():
    main_text = Path(__file__).resolve().parents[1].joinpath("backend_api", "main.py").read_text(encoding="utf-8")
    assert "internal_admin.router" in main_text
    assert "internal_manager_router" in main_text
    assert "internal_seo_router" in main_text
    assert "internal_auth_public_router" in main_text
    assert "backend_api.admin" not in main_text
