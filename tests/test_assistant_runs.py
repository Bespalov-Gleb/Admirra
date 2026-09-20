from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from types import SimpleNamespace
import uuid

import pytest
import sqlalchemy as sa
from fastapi import HTTPException

from ai.assistant import runs
from core import models
from tests.assistant_pg import pg


@pytest.fixture
def ledger(pg, monkeypatch):
    factory, engine = pg
    models.Base.metadata.create_all(engine)
    runs.metadata.create_all(engine)
    monkeypatch.setattr(runs.Subscriptions, "is_admin_bypass", lambda user: False)
    monkeypatch.setattr(runs.Subscriptions, "require_active_subscription", lambda db, user: None)
    monkeypatch.setattr(runs.Subscriptions, "billing_enforced", lambda: True)
    monkeypatch.setattr(runs.Subscriptions, "get_user_plan", lambda db, user: SimpleNamespace(
        period_days=30, max_ai_requests_per_period=2, code="start", name="Старт"))
    with factory.begin() as db:
        user = models.User(email="approved@example.test", password_hash="synthetic")
        db.add(user)
        db.flush()
        uid = user.id
    return factory, uid


def reserve(ledger, key=None, hash="a" * 64, conversation=None):
    factory, uid = ledger
    with factory() as db:
        return runs.reserve(db, db.get(models.User, uid), request_id=key or uuid.uuid4(),
            request_hash=hash, conversation_id=conversation, client_id=None, model="test")


def used(ledger):
    factory, uid = ledger
    with factory() as db:
        return db.get(models.User, uid).ai_requests_used


def test_concurrent_same_request_reserves_and_creates_conversation_once(ledger):
    key = uuid.uuid4()
    with ThreadPoolExecutor(6) as pool:
        values = list(pool.map(lambda _: reserve(ledger, key), range(6)))
    assert sum(created for row, created in values) == 1
    assert len({row["conversation_id"] for row, created in values}) == 1
    assert used(ledger) == 1


def test_parallel_different_requests_cannot_exceed_last_quota(ledger):
    factory, uid = ledger
    with factory.begin() as db:
        user = db.get(models.User, uid)
        user.ai_requests_used = 1
        user.ai_requests_period_started_at = runs.Subscriptions._now()
    def submit(_):
        try:
            return reserve(ledger)[1]
        except HTTPException as exc:
            assert exc.status_code == 429
            return False
    with ThreadPoolExecutor(6) as pool:
        assert sum(pool.map(submit, range(6))) == 1
    assert used(ledger) == 2


def test_conflicting_payload_does_not_charge_again(ledger):
    key = uuid.uuid4()
    reserve(ledger, key)
    with pytest.raises(HTTPException) as error:
        reserve(ledger, key, hash="b" * 64)
    assert error.value.status_code == 409
    assert used(ledger) == 1


def test_failure_before_provider_refunds_once(ledger):
    factory, _ = ledger
    row, _ = reserve(ledger)
    runs.finish(factory, row, "interrupted")
    runs.finish(factory, row, "failed")
    assert used(ledger) == 0


def test_unknown_provider_outcome_keeps_one_unit_and_prevents_replay(ledger):
    factory, _ = ledger
    key = uuid.uuid4()
    row, _ = reserve(ledger, key)
    with runs.execution(factory, row):
        runs.before_provider()
        runs.record_usage({"type": "message", "request_id": "provider-test", "usage": {
            "prompt_tokens": 12, "completion_tokens": 8, "private": "must not persist"}}, provider="test", model="test")
    runs.finish(factory, row, "uncertain")
    again, created = reserve(ledger, key)
    assert not created and again["state"] == "uncertain"
    assert used(ledger) == 1
    assert "private" not in str(again["usage"])
    with runs.execution(factory, row), pytest.raises(RuntimeError):
        runs.before_provider()


def test_tool_iterations_are_one_product_unit(ledger):
    factory, _ = ledger
    row, _ = reserve(ledger)
    with runs.execution(factory, row):
        for _ in range(4):
            runs.before_provider()
            runs.record_usage({"type": "message", "usage": {"total_tokens": 8}}, provider="test", model="test")
    runs.finish(factory, row, "succeeded")
    assert used(ledger) == 1
    with factory() as db:
        result = db.execute(sa.select(runs.runs)).mappings().one()
        assert result["provider_calls"] == 4 and len(result["usage"]) == 4


def test_same_conversation_cannot_run_twice(ledger):
    row, _ = reserve(ledger)
    with pytest.raises(HTTPException) as error:
        reserve(ledger, conversation=row["conversation_id"])
    assert error.value.status_code == 409
    assert used(ledger) == 1


def test_refund_does_not_subtract_from_new_period(ledger):
    factory, uid = ledger
    row, _ = reserve(ledger)
    with factory.begin() as db:
        user = db.get(models.User, uid)
        user.ai_requests_period_started_at += timedelta(days=30)
        user.ai_requests_used = 1
    runs.finish(factory, row, "failed")
    assert used(ledger) == 1


def test_stale_quota_read_cannot_reset_new_reservation(ledger):
    factory, uid = ledger
    with factory() as reader:
        stale = reader.get(models.User, uid)
        assert stale.ai_requests_period_started_at is None
        reserve(ledger)
        runs.Subscriptions._ensure_ai_period(stale, SimpleNamespace(period_days=30))
        reader.commit()
    assert used(ledger) == 1


def test_hotfix_migration_is_repeatable_without_moving_alembic(ledger):
    from ops.migrate_assistant_runs import migrate
    factory, _ = ledger
    with factory.begin() as db:
        migrate(db.connection())
        migrate(db.connection())


def test_expired_reservation_is_refunded_but_started_is_uncertain(ledger):
    factory, _ = ledger
    first, _ = reserve(ledger)
    second, _ = reserve(ledger)
    with runs.execution(factory, second):
        runs.before_provider()
    with factory.begin() as db:
        db.execute(runs.runs.update().values(expires_at=sa.func.now() - timedelta(minutes=1)))
    reserve(ledger)
    assert used(ledger) == 2
    with factory() as db:
        states = dict(db.execute(sa.select(runs.runs.c.id, runs.runs.c.state)).all())
        assert states[first["id"]] == "failed" and states[second["id"]] == "uncertain"


def test_team_uses_owner_quota(ledger):
    factory, uid = ledger
    with factory.begin() as db:
        member = models.User(email="member@example.test", password_hash="synthetic")
        db.add(member)
        db.flush()
        mid = member.id
        db.add(models.TeamMember(account_id=uid, user_id=mid, email=member.email,
                                status=models.TeamMemberStatus.ACTIVE))
    row, _ = reserve((factory, mid))
    assert row["account_id"] == uid and used(ledger) == 1 and used((factory, mid)) == 0


def test_success_replays_and_deleted_conversation_never_reexecutes(ledger):
    factory, _ = ledger
    key = uuid.uuid4()
    row, _ = reserve(ledger, key)
    runs.finish(factory, row, "succeeded")
    with factory.begin() as db:
        db.delete(db.get(models.AiConversation, row["conversation_id"]))
    again, created = reserve(ledger, key)
    assert not created and again["state"] == "succeeded" and again["conversation_id"] is None
    assert used(ledger) == 1


@pytest.fixture
def http_client(ledger, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from ai.assistant import router
    factory, uid = ledger
    app = FastAPI()
    app.include_router(router.router)
    def get_db():
        with factory() as db:
            yield db
    app.dependency_overrides[router.get_db] = get_db
    app.dependency_overrides[router.security.get_current_user] = lambda: SimpleNamespace(id=uid)
    monkeypatch.setattr(router.llm, "is_configured", lambda: True)
    with TestClient(app) as client:
        yield client, router


def test_http_success_replay_and_conflict_never_call_provider_again(ledger, http_client, monkeypatch):
    client, router = http_client
    calls = []
    async def agent(db, conv, *args, **kwargs):
        runs.before_provider()
        calls.append(1)
        message = models.AiMessage(conversation_id=conv.id, role="assistant", content="Test answer")
        db.add(message)
        db.commit()
        yield {"type": "done", "message_id": str(message.id), "content": message.content}
    monkeypatch.setattr(router.agent, "run", agent)
    body = {"request_id": str(uuid.uuid4()), "message": "Question"}
    assert client.post("/assistant/chat", json=body).status_code == 200
    replay = client.post("/assistant/chat", json=body)
    assert replay.status_code == 200 and '"replayed": true' in replay.text
    assert client.post("/assistant/chat", json={**body, "message": "Other"}).status_code == 409
    assert len(calls) == 1 and used(ledger) == 1


@pytest.mark.parametrize("provider_started", [True, False])
def test_http_error_settles_before_stream_ends(ledger, http_client, monkeypatch, provider_started):
    client, router = http_client
    async def agent(*args, **kwargs):
        if provider_started:
            runs.before_provider()
        raise RuntimeError("PRIVATE")
        yield
    monkeypatch.setattr(router.agent, "run", agent)
    body = {"request_id": str(uuid.uuid4()), "message": "Question"}
    response = client.post("/assistant/chat", json=body)
    assert response.status_code == 200 and '"type": "error"' in response.text and "PRIVATE" not in response.text
    assert used(ledger) == int(provider_started)
    assert client.post("/assistant/chat", json=body).status_code == 409


def test_http_missing_id_and_exhausted_quota_are_rejected(ledger, http_client):
    client, _ = http_client
    assert client.post("/assistant/chat", json={"message": "Question"}).status_code == 428
    reserve(ledger)
    reserve(ledger)
    response = client.post("/assistant/chat", json={"request_id": str(uuid.uuid4()), "message": "Question"})
    assert response.status_code == 429 and used(ledger) == 2
