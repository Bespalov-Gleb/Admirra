import httpx
import pytest
from ops.provider_read_peak import ReadBudget


def test_provider_probe_refuses_mutations_oauth_bank_and_unbounded_ai():
    budget = ReadBudget()
    for request in [
        httpx.Request('POST', 'https://api.direct.yandex.com/json/v5/campaigns', json={'method': 'delete'}),
        httpx.Request('POST', 'https://ads.vk.com/api/v2/oauth2/token.json'),
        httpx.Request('POST', 'https://api.cloudpayments.ru/payments/charge'),
        httpx.Request('POST', 'http://10.78.0.3:8080/api/v1/chat/completions', json={'max_tokens': 10000}),
    ]:
        with pytest.raises(RuntimeError):
            budget.admit(request)
    assert not budget.calls


def test_provider_probe_has_one_paid_request_and_finite_read_budget():
    budget = ReadBudget()
    request = httpx.Request('POST', 'http://10.78.0.3:8080/api/v1/chat/completions',
        json={'max_tokens': 100, 'messages': [{'role': 'user', 'content': 'test'}]})
    budget.admit(request)
    with pytest.raises(RuntimeError, match='budget'):
        budget.admit(request)
    read = httpx.Request('GET', 'https://ads.vk.com/api/v3/ad_plans.json')
    for _ in range(39):
        budget.admit(read)
    with pytest.raises(RuntimeError, match='budget'):
        budget.admit(read)
