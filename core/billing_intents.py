"""SQL-only financial intents. Subscription row lock precedes operation locks."""
from contextvars import ContextVar
import hashlib
import json
import uuid
import sqlalchemy as sa
from core import models
from core.runtime import env_bool
from automation.work_tables import jobs
from automation.work_ledger import submit

permit = ContextVar("billing_provider_permit", default=None)
OPEN = ("queued", "dispatching", "uncertain", "rejected")


def enabled():
    if not env_bool("BILLING_PROVIDER_QUEUE", False):
        return False
    if not env_bool("DURABLE_TASKS", False):
        raise RuntimeError("Billing provider queue requires durable tasks")
    return True


def require_permit(command, provider_id):
    if enabled() and permit.get() != (command, provider_id):
        raise RuntimeError("CloudPayments mutations require the durable account queue")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def enqueue(db, sub, command, provider_id=None):
    if not enabled() or command not in {"update", "cancel_one", "cancel_all"}:
        raise ValueError("Unsupported billing operation")
    if command == "cancel_one" and not provider_id:
        raise ValueError("Cancellation target is required")
    # Identity ordinals must be allocated in account COMMIT order, including
    # concurrent transactions on different subscription rows of the same owner.
    db.execute(sa.text("SELECT pg_advisory_xact_lock(hashtextextended(:owner, 732123))"),
               {"owner": str(sub.user_id)})
    db.flush()
    # All API paths / webhook / recurring planner already own or acquire this
    # lock. No SQL connection from this transaction is used for provider IO.
    db.scalar(sa.select(models.Subscription.id).where(models.Subscription.id == sub.id).with_for_update())
    op = models.BillingProviderOperation
    target = provider_id or (sub.cloudpayments_subscription_id if command == "update" else None)
    existing = db.scalar(sa.select(op).where(op.user_id == sub.user_id, op.subscription_id == sub.id,
        op.command == command, op.provider_id == target, op.status == "queued").order_by(op.ordinal).limit(1))
    if existing:
        return existing
    count = db.scalar(sa.select(sa.func.count()).select_from(op).where(op.user_id == sub.user_id, op.status.in_(OPEN)))
    if count >= 32:
        raise RuntimeError("Billing operation queue is full; requires reconciliation")
    row = op(user_id=sub.user_id, subscription_id=sub.id, command=command, provider_id=target,
             job_id=uuid.uuid4(), evidence={})
    db.add(row)
    db.flush()
    row.job_id = submit(db, kind="billing.provider", queue="maintenance", tenant=str(sub.user_id),
        resource=f"billing.provider:{sub.user_id}", key=f"billing.provider:{row.id}",
        payload={"operation_id": str(row.id), "owner_id": str(sub.user_id), "ordinal": row.ordinal}, replay_safe=False)
    return row


def pending(db, owner_id):
    return db.scalar(sa.select(models.BillingProviderOperation).where(
        models.BillingProviderOperation.user_id == owner_id,
        models.BillingProviderOperation.status.in_(OPEN)).order_by(models.BillingProviderOperation.ordinal).limit(1))


def assert_checkout_allowed(db, owner_id):
    if not enabled():
        return
    blocked = pending(db, owner_id) or db.scalar(sa.select(jobs.c.id).where(
        jobs.c.tenant == str(owner_id), jobs.c.kind == "billing.recurring",
        jobs.c.state.in_(["running", "uncertain"])).limit(1))
    if blocked:
        from fastapi import HTTPException
        raise HTTPException(409, {"reason": "billing_operation_pending",
            "message": "Предыдущее изменение платежей ещё не подтверждено. Дождитесь результата или обратитесь в поддержку."})


def cancellation_wins(db, sub, intent):
    """A delayed Active/Pay webhook isn't consent to resume cancelled renewals."""
    if not sub.cancel_at_period_end:
        return False
    if intent is None:
        return True
    last = db.scalar(sa.select(sa.func.max(models.BillingProviderOperation.created_at)).where(
        models.BillingProviderOperation.user_id == sub.user_id, models.BillingProviderOperation.command == "cancel_all"))
    # Missing historical cancellation evidence is not consent to reactivate.
    return last is None or intent.created_at <= last


def public(row, job=None):
    state = row.status
    if state in {"queued", "dispatching"} and job and job["state"] in {"failed", "uncertain"}:
        state = "uncertain"
    return {"id": str(row.id), "command": row.command, "status": state,
        "created_at": row.created_at, "updated_at": row.updated_at,
        "message": {
            "queued": "Изменение платежей в очереди. Платёжная система ещё не подтвердила результат.",
            "dispatching": "Ожидаем подтверждение платёжной системы.",
            "uncertain": "Результат неизвестен. Автоматический повтор остановлен; требуется проверка поддержки.",
            "rejected": "Изменение не выполнено. Требуется проверка поддержки.",
            "confirmed": "Изменение подтверждено платёжной системой.",
            "superseded": "Изменение заменено более новым решением; запрос провайдеру не отправлен.",
        }[state]}
