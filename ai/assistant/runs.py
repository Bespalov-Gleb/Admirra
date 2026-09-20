"""Account-serialized quota reservations and durable request deduplication.

One product request, not one tool/model iteration. No bank/card operations.
Unknown provider outcomes are never refunded or retried automatically.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import timedelta
import hashlib
import json
import uuid

from fastapi import HTTPException
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

from core import models
from backend_api.services.subscription import SubscriptionService as Subscriptions

metadata = sa.MetaData()
runs = sa.Table("assistant_request_runs", metadata,
    sa.Column("id", UUID(as_uuid=True), primary_key=True),
    sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey(models.User.id, ondelete="CASCADE"), nullable=False),
    sa.Column("account_id", UUID(as_uuid=True), sa.ForeignKey(models.User.id, ondelete="CASCADE"), nullable=False),
    sa.Column("request_id", UUID(as_uuid=True), nullable=False),
    sa.Column("request_hash", sa.String(64), nullable=False),
    sa.Column("conversation_id", UUID(as_uuid=True), sa.ForeignKey(models.AiConversation.id, ondelete="SET NULL")),
    sa.Column("message_id", UUID(as_uuid=True), sa.ForeignKey(models.AiMessage.id, ondelete="SET NULL")),
    sa.Column("state", sa.String(16), nullable=False),
    sa.Column("charged", sa.Boolean, nullable=False),
    sa.Column("quota_period", sa.DateTime(timezone=True)),
    sa.Column("provider_calls", sa.Integer, nullable=False, server_default="0"),
    sa.Column("usage", JSONB, nullable=False, server_default="[]"),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("finished_at", sa.DateTime(timezone=True)),
    sa.UniqueConstraint("user_id", "request_id", name="uq_assistant_user_request"),
    sa.CheckConstraint("state IN ('reserved','running','succeeded','failed','interrupted','uncertain')"),
    sa.CheckConstraint("provider_calls >= 0"),
)
sa.Index("ix_assistant_runs_account_active", runs.c.account_id, runs.c.state, runs.c.expires_at)
sa.Index("ix_assistant_runs_conversation", runs.c.conversation_id)
ACTIVE = ("reserved", "running")
MAX_RUN_SECONDS = 900
_scope = ContextVar("assistant_request_scope", default=None)


def fingerprint(payload):
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def _locked_account(db, account_id):
    return db.query(models.User).filter(models.User.id == account_id).populate_existing().with_for_update().one()


def _finish(db, row, account, state, message_id=None):
    if row["state"] not in ACTIVE:
        return
    charged = row["charged"]
    if state != "succeeded" and row["provider_calls"] == 0:
        if charged and account.ai_requests_period_started_at == row["quota_period"]:
            account.ai_requests_used = max(0, int(account.ai_requests_used or 0) - 1)
        charged = False
        state = "failed"
    db.execute(runs.update().where(runs.c.id == row["id"]).values(
        state=state, charged=charged, message_id=message_id, finished_at=sa.func.clock_timestamp()))


def reserve(db, user, *, request_id, request_hash, conversation_id, client_id, model):
    account_id = Subscriptions._resolve_ai_quota_user(db, user).id
    account = _locked_account(db, account_id)
    now = db.scalar(sa.select(sa.func.clock_timestamp()))
    # Recover abandoned reservations without repeating a provider call. The SQL
    # account lock serializes this with new reservations and normal settlement.
    stale = db.execute(sa.select(runs).where(runs.c.account_id == account_id,
        runs.c.state.in_(ACTIVE), runs.c.expires_at <= now).with_for_update()).mappings().all()
    for row in stale:
        _finish(db, row, account, "uncertain")
    db.flush()
    existing = db.execute(sa.select(runs).where(runs.c.user_id == user.id,
        runs.c.request_id == request_id)).mappings().first()
    if existing:
        if existing["request_hash"] != request_hash:
            raise HTTPException(409, "Этот идентификатор уже использован для другого запроса.")
        db.commit()
        return dict(existing), False
    active = sa.select(runs.c.id).where(runs.c.account_id == account_id, runs.c.state.in_(ACTIVE))
    if conversation_id and db.scalar(sa.select(sa.exists(active.where(runs.c.conversation_id == conversation_id)))):
        raise HTTPException(409, "В этом диалоге уже формируется ответ. Дождитесь завершения.")
    if db.scalar(sa.select(sa.func.count()).select_from(active.subquery())) >= 3:
        raise HTTPException(429, "У аккаунта уже три активных AI-запроса. Дождитесь завершения.")
    Subscriptions.ensure_can_use_ai(db, account)
    charged = not Subscriptions.is_admin_bypass(account)
    if charged:
        account.ai_requests_used = int(account.ai_requests_used or 0) + 1
    if conversation_id is None:
        conv = models.AiConversation(user_id=user.id, client_id=client_id, model=model)
        db.add(conv)
        db.flush()
        conversation_id = conv.id
    row = dict(id=uuid.uuid4(), user_id=user.id, account_id=account_id, request_id=request_id,
        request_hash=request_hash, conversation_id=conversation_id, state="reserved", charged=charged,
        quota_period=account.ai_requests_period_started_at, provider_calls=0, usage=[],
        expires_at=now + timedelta(seconds=MAX_RUN_SECONDS + 120))
    db.execute(runs.insert().values(**row))
    db.commit()
    return row, True


@contextmanager
def execution(factory, row):
    token = _scope.set((factory, row["id"]))
    try:
        yield
    finally:
        _scope.reset(token)


def before_provider():
    context = _scope.get()
    if context is None:
        return
    factory, run_id = context
    with factory.begin() as db:
        accepted = db.execute(runs.update().where(runs.c.id == run_id,
            runs.c.state.in_(ACTIVE), runs.c.expires_at > sa.func.clock_timestamp()).values(
                state="running", provider_calls=runs.c.provider_calls + 1).returning(runs.c.id)).scalar()
        if accepted is None:
            raise RuntimeError("Assistant request is no longer executable")


def record_usage(event, *, provider, model):
    context = _scope.get()
    if context is None or event.get("type") != "message":
        return
    factory, run_id = context
    usage = event.get("usage") or {}
    allowed = ("prompt_tokens", "completion_tokens", "total_tokens", "cost", "input_tokens", "output_tokens")
    safe = {key: usage[key] for key in allowed if isinstance(usage.get(key), (int, float))}
    entry = {"provider": provider, "model": model, "usage": safe,
             "request_id": str(event.get("request_id") or "")[:200]}
    with factory.begin() as db:
        row = db.execute(sa.select(runs).where(runs.c.id == run_id).with_for_update()).mappings().one()
        db.execute(runs.update().where(runs.c.id == run_id).values(usage=[*row["usage"], entry]))


def finish(factory, row, state, message_id=None):
    with factory.begin() as db:
        account = _locked_account(db, row["account_id"])
        current = db.execute(sa.select(runs).where(runs.c.id == row["id"]).with_for_update()).mappings().one()
        _finish(db, current, account, state, message_id)
