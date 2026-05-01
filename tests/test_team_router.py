from backend_api.team import router as team_router


def test_team_router_endpoints_present():
    paths = {route.path for route in team_router.routes}
    expected = {
        "/team/me-context",
        "/team/members",
        "/team/members/invite",
        "/team/members/{member_id}",
        "/team/members/{member_id}/projects",
        "/team/members/{member_id}/projects/{project_id}",
        "/team/clients",
        "/team/clients/invite",
        "/team/clients/{user_id}",
        "/team/clients/{user_id}/projects",
        "/team/clients/{user_id}/projects/{project_id}",
        "/team/projects",
    }
    for path in expected:
        assert path in paths
