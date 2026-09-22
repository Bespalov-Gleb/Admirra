"""One ordered, non-replayable CloudPayments writer per account.

All transports run between short, fenced SQL transactions. Unknown results
stop the account queue; no compensation/retry is inferred from a timeout.
"""
from contextlib import contextmanager
import uuid
import sqlalchemy as sa
from core import models, billing_intents as intent
from core.job_fence import current_fence, LeaseLost
from automation.work_tables import jobs
from automation.work_errors import RejectedBeforeExternalIO


class BillingProviderUncertain(RuntimeError):
    pass


def _owned(db, payload):
    fence = current_fence.get()
    if not fence or not intent.enabled():
        raise LeaseLost("Billing provider execution requires an enabled durable executor")
    job = db.execute(sa.select(jobs).where(jobs.c.id == fence.job_id, jobs.c.lease_token == fence.token,
        jobs.c.state == "running", jobs.c.lease_until > sa.func.clock_timestamp())).mappings().first()
    if (not job or job["kind"] != "billing.provider" or job["payload"] != payload
            or job["tenant"] != payload["owner_id"] or job["resource"] != f'billing.provider:{payload["owner_id"]}'):
        raise LeaseLost("Billing execution scope changed")
    row = db.get(models.BillingProviderOperation, uuid.UUID(payload["operation_id"]))
    if not row or row.job_id != fence.job_id or str(row.user_id) != payload["owner_id"] or row.ordinal != payload["ordinal"]:
        raise LeaseLost("Billing intent does not match execution")
    sub = db.scalar(sa.select(models.Subscription).where(models.Subscription.id == row.subscription_id,
        models.Subscription.user_id == row.user_id).with_for_update())
    row = db.scalar(sa.select(models.BillingProviderOperation).where(models.BillingProviderOperation.id == row.id)
        .execution_options(populate_existing=True).with_for_update())
    return row, sub


def _parameters(db, sub):
    from backend_api.services.billing_notifications import _recurring_terms, _recurring_snapshot
    from backend_api.billing import _subscription_total, _subscription_receipt, _recurrent_for_billing_period
    from core.config import get_config
    owner = db.get(models.User, sub.user_id)
    if owner is None:
        raise RejectedBeforeExternalIO("Billing owner no longer exists")
    plan, period, slots = _recurring_terms(sub)
    cfg = get_config()
    recurrence = _recurrent_for_billing_period(plan, period)
    params = dict(Amount=_subscription_total(plan, period, slots), Currency=cfg.cloudpayments.currency,
        Description=f"AdMirra: {plan.name} + {slots} доп. слот(ов)",
        CustomerReceipt=_subscription_receipt(plan, period, slots, owner.email or "", cfg),
        Interval=recurrence.interval, Period=recurrence.period)
    signature = intent.digest((_recurring_snapshot(sub), owner.email or "", params))
    return params, signature


def _safe_parameters(params):
    return {**{k: v for k, v in params.items() if k != "CustomerReceipt"},
            "receipt_sha256": intent.digest(params.get("CustomerReceipt"))}


@contextmanager
def _permit(command, target):
    token = intent.permit.set((command, target))
    try:
        yield
    finally:
        intent.permit.reset(token)


def _step(factory, payload, target, status):
    with factory.begin() as db:
        row, _ = _owned(db, payload)
        if row.status != "dispatching":
            raise LeaseLost("Billing operation is no longer dispatching")
        steps = list(row.evidence.get("steps", []))
        if status == "sending":
            if len(steps) >= 20 or any(s["id"] == target for s in steps):
                raise BillingProviderUncertain("Billing target already attempted")
            steps.append({"id": target, "status": status})
        else:
            steps = [{**s, "status": status} if s["id"] == target else s for s in steps]
        row.evidence = {**row.evidence, "steps": steps}


async def execute(factory, payload):
    from backend_api.services.cloudpayments import CloudPaymentsService as CP
    with factory.begin() as db:
        row, sub = _owned(db, payload)
        if row.status in {"confirmed", "superseded"}:
            return row.status  # Crash after final SQL commit never repeats IO.
        if row.status != "queued":
            raise BillingProviderUncertain("Previous billing outcome needs reconciliation")
        prior = db.scalar(sa.select(models.BillingProviderOperation.id).where(
            models.BillingProviderOperation.user_id == row.user_id,
            models.BillingProviderOperation.ordinal < row.ordinal,
            models.BillingProviderOperation.status.in_(intent.OPEN)).limit(1))
        if prior:
            raise RejectedBeforeExternalIO("Earlier account operation is unresolved")
        command, target, owner_id = row.command, row.provider_id, row.user_id
        initial_provider_id = sub.cloudpayments_subscription_id if sub else None
        if (not sub or (command == "update" and (sub.cancel_at_period_end or sub.cloudpayments_subscription_id != target))
                or (command == "cancel_all" and not sub.cancel_at_period_end)
                or (command == "cancel_one" and sub.cloudpayments_subscription_id == target)):
            row.status = "superseded"
            return "superseded"
        params, signature = _parameters(db, sub) if command == "update" else ({}, None)
        row.status = "dispatching"
        row.evidence = {"expected": _safe_parameters(params) if params else {}, "steps": [], "source": signature}
    attempted = False
    try:
        # Read first also checks AccountId before cancellation of an old ID.
        subscriptions = await CP.find_subscriptions(str(owner_id))
        if len(subscriptions) > 20:
            raise RejectedBeforeExternalIO("Too many provider subscriptions for bounded reconciliation")
        active = {str(s["Id"]) for s in subscriptions if s["Status"] in {"Active", "PastDue"}}
        if command == "update":
            if target not in active:
                # Never reactivate a subscription cancelled directly at CP.
                raise RejectedBeforeExternalIO("Provider subscription is not active")
            targets = [target]
        else:
            targets = sorted(active if command == "cancel_all" else active.intersection({target}))
        for cp_id in targets:
            _step(factory, payload, cp_id, "sending")
            attempted = True
            with _permit("update" if command == "update" else "cancel", cp_id):
                if command == "update":
                    await CP.update_subscription(cp_id, **params)
                else:
                    await CP.cancel_subscription(cp_id)
            _step(factory, payload, cp_id, "confirmed")
        with factory.begin() as db:
            row, sub = _owned(db, payload)
            if row.status != "dispatching":
                raise LeaseLost("Billing outcome cannot be confirmed by an old worker")
            row.status = "confirmed"
            if sub and command == "update":
                _, current = _parameters(db, sub)
                if current == signature:
                    sub.recurring_sync_required = False
                elif not sub.cancel_at_period_end and sub.cloudpayments_subscription_id:
                    intent.enqueue(db, sub, "update")
            elif sub and command == "cancel_all" and sub.cancel_at_period_end:
                if (not sub.cloudpayments_subscription_id or sub.cloudpayments_subscription_id == initial_provider_id
                        or sub.cloudpayments_subscription_id in active):
                    sub.cloudpayments_subscription_id = None
                    sub.card_last4 = sub.card_type = sub.card_exp = None
                    sub.recurring_sync_required = False
                else:
                    # A late pre-cancel checkout webhook introduced another ID.
                    # Preserve pending UI and cancel it with a NEW durable intent.
                    intent.enqueue(db, sub, "cancel_all")
        return "confirmed"
    except Exception as exc:
        with factory.begin() as db:
            row, _ = _owned(db, payload)
            row.status = "uncertain" if attempted else "rejected"
            row.evidence = {**row.evidence, "error_type": type(exc).__name__}
        if attempted:
            raise BillingProviderUncertain("Provider outcome requires reconciliation") from None
        raise RejectedBeforeExternalIO("Billing preparation rejected before external mutation") from None
