"""Transport-only tests; no real billing provider calls or credentials."""
import httpx
import pytest
from backend_api.services.cloudpayments import CloudPaymentsService as CP
from tests.test_durable_work import pg
from tests.test_billing_work import billing_scope, populate


@pytest.mark.asyncio
@pytest.mark.parametrize("body,valid", [
    ({"Success": True, "Model": []}, True),
    ({"Success": True, "Model": [{"Id": "one", "AccountId": "owner", "Status": "Active"}]}, True),
    ({"Success": False, "Message": "not authorized"}, False),
    ({"Success": True, "Model": None}, False),
    ({"Success": "true", "Model": []}, False),
    ({"Success": True, "Model": [{}]}, False),
    ({"Success": True, "Model": [{"Id": "one", "AccountId": "other", "Status": "Active"}]}, False),
    ({"Success": True, "Model": [{"Id": "one", "AccountId": "owner", "Status": "Unknown"}]}, False),
    ([], False),
])
async def test_lookup_never_confuses_error_with_no_subscriptions(monkeypatch, body, valid):
    real_client = httpx.AsyncClient
    def transport(request):
        assert request.url.path == "/subscriptions/find"
        return httpx.Response(200, json=body)
    monkeypatch.setattr(CP, "_auth_header", staticmethod(lambda: "synthetic"))
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: real_client(transport=httpx.MockTransport(transport), **kwargs))
    if valid:
        assert await CP.find_subscriptions("owner") == body["Model"]
    else:
        with pytest.raises(RuntimeError):
            await CP.find_subscriptions("owner")


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [None, "find", "cancel"])
async def test_unconfirmed_cancellation_keeps_provider_reference(billing_scope, monkeypatch, failure):
    from unittest.mock import AsyncMock
    from backend_api import billing
    from core import models
    import sqlalchemy as sa
    factory, owners = billing_scope
    populate(billing_scope)
    monkeypatch.setattr(billing.SubscriptionService, "get_billing_account_user", lambda db, user: user)
    monkeypatch.setattr(billing.SubscriptionService, "ensure_default_subscription",
        lambda db, user: db.scalar(sa.select(models.Subscription).where(models.Subscription.user_id == user.id)))
    monkeypatch.setattr(billing, "log_history_event", lambda *a, **kw: None)
    monkeypatch.setattr(CP, "find_subscriptions", AsyncMock(side_effect=RuntimeError("synthetic") if failure == "find" else None, return_value=[]))
    monkeypatch.setattr(CP, "cancel_subscription", AsyncMock(side_effect=RuntimeError("synthetic") if failure == "cancel" else None))
    with factory() as db:
        sub = db.scalar(sa.select(models.Subscription).where(models.Subscription.user_id == owners[0]))
        sub.card_last4 = "1234"
        db.commit()
        result = await billing.cancel_autorenew(db.get(models.User, owners[0]), db)
        assert result["recurrent_cancelled"] is (failure is None)
        assert result["cancellation_pending"] is (failure is not None)
        assert sub.cancel_at_period_end
        assert sub.cloudpayments_subscription_id == ("synthetic-1" if failure else None)
        assert sub.card_last4 == ("1234" if failure else None)
