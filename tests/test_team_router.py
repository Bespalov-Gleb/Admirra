from pathlib import Path


def test_team_router_endpoints_present():
    text = Path(__file__).resolve().parents[1].joinpath("backend_api", "team.py").read_text(encoding="utf-8")
    expected = [
        '"/me-context"',
        '"/members/invite"',
        '"/members/{member_id}/projects"',
        '"/projects/{project_id}/members"',
        '"/invites/preview"',
        '"/invites/accept"',
    ]
    for path in expected:
        assert path in text, f"missing route {path}"


def test_team_invite_token_fields_in_model():
    text = Path(__file__).resolve().parents[1].joinpath("core", "models.py").read_text(encoding="utf-8")
    assert "invite_token" in text
    assert "invite_token_expires_at" in text
