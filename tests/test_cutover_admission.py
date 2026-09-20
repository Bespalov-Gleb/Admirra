from pathlib import Path

import pytest

from ops.cutover_admission import manage
from ops.cutover_admission.manage import patch_site


def site(text=""):
    return """server {
    server_name admirra.ru www.admirra.ru;
    client_max_body_size 20m;
%s
    location /api/ { proxy_pass http://127.0.0.1:8001; }
}
""" % text


def test_site_patch_is_exact_and_idempotent():
    patched = patch_site(site())
    assert patched.count("include /etc/nginx/snippets/admirra-cutover-admission.conf;") == 1
    assert patch_site(patched) == patched


@pytest.mark.parametrize(
    "invalid",
    [
        "server { server_name admirra.ru; }",
        site("    client_max_body_size 20m;"),
        site("    include /etc/nginx/snippets/admirra-cutover-admission.conf;\n"
             "    include /etc/nginx/snippets/admirra-cutover-admission.conf;"),
    ],
)
def test_site_patch_fails_on_ambiguous_structure(invalid):
    with pytest.raises(ValueError):
        patch_site(invalid)


def test_closed_map_blocks_only_reviewed_side_effect_routes():
    root = Path(__file__).parents[1] / "ops" / "cutover_admission"
    closed = (root / "admirra-cutover-map.closed.conf").read_text()
    rules = "\n".join(line for line in closed.splitlines() if not line.lstrip().startswith("#"))
    for route in (
        "/api/assistant",
        "/api/ai/",
        "/api/reports",
        "/api/integrations/sync/jobs",
        "/api/integrations/[^/]+/sync",
        "/api/dashboard/dynamics/backfill",
    ):
        assert route in rules
    assert "/api/billing" not in rules
    assert "webhook" not in rules.lower()
    assert "default 0;" in rules


def test_open_map_has_no_blocking_route():
    root = Path(__file__).parents[1] / "ops" / "cutover_admission"
    opened = (root / "admirra-cutover-map.open.conf").read_text()
    assert opened.count(" 1;") == 0
    assert "default 0;" in opened


def test_install_backup_preserves_resolved_sites_and_existing_gate(tmp_path, monkeypatch):
    available = tmp_path / "sites-available"
    enabled = tmp_path / "sites-enabled"
    available.mkdir()
    enabled.mkdir()
    target = available / "admirra.ru"
    target.write_text(site())
    link = enabled / "admirra.ru"
    link.symlink_to(target)
    active_map = tmp_path / "active-map.conf"
    active_snippet = tmp_path / "active-snippet.conf"
    active_map.write_text("old-map")
    active_snippet.write_text("old-snippet")
    monkeypatch.setattr(manage, "ACTIVE_MAP", active_map)
    monkeypatch.setattr(manage, "ACTIVE_SNIPPET", active_snippet)
    monkeypatch.setenv("ADMIRRA_CUTOVER_BACKUP_DIR", str(tmp_path / "backups"))

    backup = manage.preserve_install_backup((link,))

    assert (backup / "site-1.conf").read_text() == site()
    assert (backup / "active-map.conf").read_text() == "old-map"
    assert (backup / "active-snippet.conf").read_text() == "old-snippet"
    assert (backup / "paths.txt").read_text().strip() == str(target)
