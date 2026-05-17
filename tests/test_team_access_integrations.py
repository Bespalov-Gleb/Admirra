from pathlib import Path


def test_integrations_use_accessible_clients():
    text = Path(__file__).resolve().parents[1].joinpath("backend_api", "integrations.py").read_text(encoding="utf-8")
    assert "get_accessible_client_ids" in text
    assert "ensure_integrations_allowed" in text


def test_access_control_helpers_defined():
    text = Path(__file__).resolve().parents[1].joinpath("backend_api", "access_control.py").read_text(encoding="utf-8")
    assert "def assert_client_in_accessible" in text
    assert "def ensure_integrations_allowed" in text


def test_ai_reports_assert_project_access():
    ai = Path(__file__).resolve().parents[1].joinpath("ai", "router.py").read_text(encoding="utf-8")
    reports = Path(__file__).resolve().parents[1].joinpath("backend_api", "reports", "router.py").read_text(encoding="utf-8")
    assert "assert_project_access" in ai
    assert "_parse_report_client_id" in reports
