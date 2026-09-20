import io
import json
import urllib.error

import pytest

from ops.monitoring.external_heartbeat import atomic_write, notify_status, probe_once, run, telegram_send, validate_base_url


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


def observation(status):
    return {"status": status, "checked_at": "2026-09-20T20:00:00Z"}


def test_notifications_initial_health_silent_and_restart_deduplication(tmp_path):
    path = tmp_path / "notifications.json"
    calls = []
    send = lambda *args: calls.append(args)
    assert notify_status(observation("ok"), {}, path, send=send, now=100)["status"] == "not_due"
    notify_status(observation("critical"), {}, path, send=send, now=200)
    assert notify_status(observation("critical"), {}, path, send=send, now=201)["status"] == "not_due"
    notify_status(observation("critical"), {}, path, send=send, now=14600)
    notify_status(observation("ok"), {}, path, send=send, now=14601)
    notify_status(observation("ok"), {}, path, send=send, now=14602)
    assert len(calls) == 3
    assert "восстановлена" in calls[-1][1]
    assert json.loads(path.read_text())["incident_pending"] is False


def test_failed_firing_retries_and_eventually_recovers(tmp_path):
    path = tmp_path / "notifications.json"
    def fail(*_):
        raise RuntimeError("network")
    with pytest.raises(RuntimeError):
        notify_status(observation("critical"), {}, path, send=fail, now=100)
    assert json.loads(path.read_text())["incident_pending"] is True
    calls = []
    notify_status(observation("critical"), {}, path, send=lambda *a: calls.append(a), now=101)
    assert len(calls) == 1
    with pytest.raises(RuntimeError):
        notify_status(observation("ok"), {}, path, send=fail, now=102)
    assert json.loads(path.read_text())["incident_pending"] is True
    notify_status(observation("ok"), {}, path, send=lambda *a: calls.append(a), now=103)
    assert len(calls) == 2


def test_uncertain_firing_followed_by_recovery_is_not_lost(tmp_path):
    path = tmp_path / "notifications.json"
    with pytest.raises(RuntimeError):
        notify_status(observation("critical"), {}, path, send=lambda *_: (_ for _ in ()).throw(RuntimeError()))
    calls = []
    notify_status(observation("ok"), {}, path, send=lambda *a: calls.append(a))
    assert len(calls) == 1


def test_heartbeat_smoke_labels_test_messages(tmp_path):
    calls = []
    for status in ("critical", "ok"):
        notify_status(observation(status), {}, tmp_path / "smoke.json", send=lambda *a: calls.append(a), test=True)
    assert len(calls) == 2
    assert all("[ТЕСТ — сайт не отключался]" in text for _, text in calls)


def test_pending_state_persisted_before_network_call(tmp_path):
    path = tmp_path / "notifications.json"
    def send(*_):
        assert json.loads(path.read_text())["incident_pending"] is True
    notify_status(observation("critical"), {}, path, send=send)


def token_config(tmp_path):
    path = tmp_path / "token"
    path.write_text("123:synthetic-test-token")
    path.chmod(0o600)
    return {"token_file": str(path), "chat_id": -1234}


def test_telegram_reads_file_secret_and_posts_only_needed_fields(tmp_path):
    config = token_config(tmp_path)
    config["message_thread_id"] = 42
    def open_url(request, timeout):
        assert timeout == 10
        assert request.full_url == "https://api.telegram.org/bot123:synthetic-test-token/sendMessage"
        assert json.loads(request.data) == {
            "chat_id": -1234, "text": "test", "message_thread_id": 42,
            "link_preview_options": {"is_disabled": True},
        }
        return Response(200, b'{"ok":true}')
    telegram_send(config, "test", open_url=open_url)


@pytest.mark.parametrize("response", [Response(200, b'{"ok":false}'), Response(200, b'bad'), Response(500), Response(200, b'x' * 16385)])
def test_telegram_rejection_sanitized(tmp_path, response):
    with pytest.raises(RuntimeError, match="Telegram notification failed") as error:
        telegram_send(token_config(tmp_path), "test", open_url=lambda *_, **__: response)
    assert "synthetic-test-token" not in str(error.value)


def test_telegram_network_exception_never_exposes_token(tmp_path):
    def fail(request, **_):
        raise urllib.error.URLError(request.full_url)
    with pytest.raises(RuntimeError) as error:
        telegram_send(token_config(tmp_path), "test", open_url=fail)
    assert "synthetic-test-token" not in str(error.value)
    assert error.value.__suppress_context__


@pytest.mark.parametrize("unsafe", ["world-readable", "symlink", "invalid-token", "invalid-chat"])
def test_telegram_rejects_unsafe_secret_or_configuration(tmp_path, unsafe):
    config = token_config(tmp_path)
    path = tmp_path / "token"
    if unsafe == "world-readable":
        path.chmod(0o644)
    elif unsafe == "symlink":
        link = tmp_path / "link"
        link.symlink_to(path)
        config["token_file"] = str(link)
    elif unsafe == "invalid-token":
        path.write_text("injected/path")
    else:
        config["chat_id"] = 0
    with pytest.raises(RuntimeError):
        telegram_send(config, "test", open_url=lambda *_: pytest.fail("must not send"))
