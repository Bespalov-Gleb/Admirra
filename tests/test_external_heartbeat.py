import io
import json
import urllib.error

import pytest

from ops.monitoring.external_heartbeat import atomic_write, probe_once, run, validate_base_url


class Response:
    def __init__(self, status, body=b""):
        self.status = status
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, maximum):
        return self.body[:maximum]


def opener(root_status=200, auth_status=401, root_body=b"AdMirra"):
    def open_url(request, timeout):
        if request.full_url.endswith("/api/auth/me"):
            if auth_status >= 400:
                raise urllib.error.HTTPError(request.full_url, auth_status, "expected", {}, io.BytesIO(b"auth"))
            return Response(auth_status, b"auth")
        return Response(root_status, root_body)
    return open_url


def test_probe_requires_frontend_and_auth_guard():
    result = probe_once("https://admirra.ru", open_url=opener())
    assert result["ok"] is True
    assert result["root_status"] == 200
    assert result["auth_status"] == 401


@pytest.mark.parametrize(
    "open_url",
    [opener(root_status=503), opener(root_body=b""), opener(auth_status=200)],
)
def test_probe_rejects_false_healthy_responses(open_url):
    with pytest.raises(RuntimeError):
        probe_once("https://admirra.ru", open_url=open_url)


def test_run_retries_without_serializing_error_text(monkeypatch):
    outcomes = iter([RuntimeError("secret detail"), {"ok": True, "root_status": 200, "auth_status": 401}])
    sleeps = []

    def probe(*_, **__):
        value = next(outcomes)
        if isinstance(value, Exception):
            raise value
        return value

    result = run("https://admirra.ru", attempts=3, delay=2, timeout=8, probe=probe, sleep=sleeps.append)
    assert result["status"] == "ok"
    assert result["attempts"][0] == {"ok": False, "error_type": "RuntimeError"}
    assert "secret detail" not in json.dumps(result)
    assert sleeps == [2]


def test_run_is_critical_only_after_all_attempts_fail():
    result = run(
        "https://admirra.ru",
        attempts=3,
        delay=0,
        timeout=8,
        probe=lambda *_, **__: (_ for _ in ()).throw(OSError("offline")),
        sleep=lambda *_: None,
    )
    assert result["status"] == "critical"
    assert len(result["attempts"]) == 3


@pytest.mark.parametrize(
    "value",
    ["http://admirra.ru", "https://user:pass@admirra.ru", "https://admirra.ru/path", "not-a-url"],
)
def test_base_url_is_a_bounded_https_origin(value):
    with pytest.raises(ValueError):
        validate_base_url(value)


def test_atomic_state_is_world_readable_and_contains_no_body(tmp_path):
    path = tmp_path / "status.json"
    atomic_write(path, {"status": "ok", "checked_at": "2026-09-20T17:00:00Z"})
    assert path.stat().st_mode & 0o777 == 0o644
    assert json.loads(path.read_text())["status"] == "ok"
