"""Регрессионные проверки контракта AI-комментария v2.0."""

import json
import uuid
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from ai.report_generator import (
    COMMENT_PROMPT_VERSION,
    _ai_output_config,
    _ai_error_is_non_retryable,
    _collect_context_numbers,
    _flatten_comment,
    _model_cost_rub,
    _model_cost_usd,
    _normalise_comment_model_json,
    _parse_comment_json,
    _runtime_comment_prompt,
    _validate_comment,
)


def _valid_obj(**overrides):
    obj = {
        "period_state": "attention",
        "lead": "Заявки дорожают, проект требует проверки.",
        "body": ["Конверсия в заявку составила 3,28%, а CPA кампании «Поиск» — 1 537 ₽."],
        "recommendation": "Стоит проверить семантику и посадочную страницу.",
    }
    obj.update(overrides)
    return obj


def _validate(obj, context=None, **kwargs):
    context = context or {"cr_click_to_lead_pct": 3.28, "cpa": 1537}
    return _validate_comment(
        obj,
        _collect_context_numbers(context),
        kwargs.get("directions_fixed", False),
        kwargs.get("direction_names", []),
        kwargs.get("campaign_names", ["Поиск"]),
    )


def test_prompt_version_and_v2_schema_are_strict():
    assert COMMENT_PROMPT_VERSION == "2.0"
    parsed = _parse_comment_json(json.dumps(_valid_obj(), ensure_ascii=False))
    assert parsed is not None
    assert parsed["period_state"] == "attention"


def test_interactive_claude_effort_defaults_to_low(monkeypatch):
    monkeypatch.delenv("AI_COMMENT_EFFORT", raising=False)
    assert _ai_output_config("AI_COMMENT_EFFORT") == {"effort": "low"}
    monkeypatch.setenv("AI_COMMENT_EFFORT", "high")
    assert _ai_output_config("AI_COMMENT_EFFORT") == {"effort": "high"}
    monkeypatch.setenv("AI_COMMENT_EFFORT", "unsupported")
    assert _ai_output_config("AI_COMMENT_EFFORT") == {"effort": "low"}


def test_runtime_prompt_keeps_all_rules_and_selects_one_of_five_examples():
    prompt = _runtime_comment_prompt({"kpi": {"leads": {"value": 34}}})
    assert "## ПРАВИЛА — ДАННЫЕ" in prompt
    assert "## ПРАВИЛА — РЕКОМЕНДАЦИЯ" in prompt
    assert prompt.count("Контекст:") == 1
    assert '"period_state":"steady"' in prompt

    balance = _runtime_comment_prompt({
        "kpi": {"leads": {"value": 31}},
        "detector": {"flags": [{"text": "Баланс кабинета заканчивается"}]},
    })
    assert "баланс кабинета на исходе" in balance


def test_comment_json_normalisation_removes_only_numeric_tilde():
    assert _normalise_comment_model_json('а ~98 962 ₽, знак ~ отдельно') == 'а 98 962 ₽, знак ~ отдельно'


@pytest.mark.asyncio
async def test_dashboard_comment_throttle_stays_http_429(monkeypatch):
    """Общий обработчик отчёта не должен превращать штатный троттл в 500."""
    from ai import router

    monkeypatch.setattr(router, "_client_or_404", lambda *args, **kwargs: None)
    monkeypatch.setattr(router, "_get_cached_comment", lambda *args, **kwargs: None)

    def throttled(*args, **kwargs):
        raise HTTPException(
            status_code=429,
            detail={"reason": "comment_refresh_throttled", "retry_after": 123},
        )

    monkeypatch.setattr(router, "_enforce_comment_refresh_throttle", throttled)
    body = router.GenerateReportRequest(
        client_id=str(uuid.uuid4()),
        start_date="2026-08-01",
        end_date="2026-08-06",
        report_type="dashboard_comment",
    )

    with pytest.raises(HTTPException) as exc_info:
        await router.generate_report(
            body=body,
            current_user=SimpleNamespace(id=uuid.uuid4()),
            db=object(),
        )

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail["reason"] == "comment_refresh_throttled"


def test_period_state_is_required_and_has_closed_enum():
    without_state = _valid_obj()
    without_state.pop("period_state")
    assert _parse_comment_json(json.dumps(without_state, ensure_ascii=False)) is None
    assert _parse_comment_json(json.dumps(_valid_obj(period_state="urgent"), ensure_ascii=False)) is None


def test_recommendation_and_one_or_two_body_paragraphs_are_required():
    assert _parse_comment_json(json.dumps(_valid_obj(recommendation=""), ensure_ascii=False)) is None
    assert _parse_comment_json(json.dumps(_valid_obj(body=[]), ensure_ascii=False)) is None
    assert _parse_comment_json(json.dumps(_valid_obj(body=["a", "b", "c"]), ensure_ascii=False)) is None


def test_service_identifiers_and_detector_codes_are_hard_failures():
    for leaked in ("period_state", "manual_cpc", "P-2", "С-0"):
        obj = _valid_obj(body=[f"Активен служебный код {leaked}."])
        hard, _ = _validate(obj, context={})
        assert hard, leaked


def test_banlist_and_digits_in_lead_are_hard_failures():
    hard, _ = _validate(_valid_obj(lead="Период прошёл под знаком роста."))
    assert hard
    hard, _ = _validate(_valid_obj(lead="Заявок стало 12."), context={"leads": 12})
    assert hard


def test_numbers_must_come_from_context_including_small_decimals():
    hard, _ = _validate(_valid_obj())
    assert not hard
    hard, _ = _validate(_valid_obj(body=["Конверсия в заявку составила 9,99%."]))
    assert any("число" in issue for issue in hard)


def test_rounded_percentage_is_allowed_but_approximation_is_not():
    obj = _valid_obj(body=["Конверсия в заявку составила 3%."])
    hard, _ = _validate(obj, context={"cr_click_to_lead_pct": 3.28})
    assert not hard
    obj = _valid_obj(body=["Конверсия в заявку — около 3%."])
    hard, _ = _validate(obj, context={"cr_click_to_lead_pct": 3.28})
    assert any("приближен" in issue for issue in hard)


def test_human_phrase_without_numeric_approximation_is_allowed():
    obj = _valid_obj(body=["Остатка в кабинете хватит примерно на день расхода."])
    hard, _ = _validate(obj, context={})
    assert not hard


def test_fixed_directions_still_block_budget_reallocation():
    obj = _valid_obj(recommendation="Стоит перенести бюджет из «Ростов» в «Краснодар».")
    hard, _ = _validate(
        obj,
        directions_fixed=True,
        direction_names=["Ростов", "Краснодар"],
    )
    assert hard


def test_flatten_keeps_required_recommendation_and_hides_machine_state():
    text = _flatten_comment(_valid_obj())
    assert "Рекомендация:" in text
    assert "period_state" not in text
    assert "attention" not in text


def test_billing_and_auth_errors_are_not_blindly_retried():
    class ProviderError(Exception):
        def __init__(self, status_code, message):
            super().__init__(message)
            self.status_code = status_code

    assert _ai_error_is_non_retryable(ProviderError(402, "insufficient quota"))
    assert _ai_error_is_non_retryable(ProviderError(401, "invalid x-api-key"))
    assert not _ai_error_is_non_retryable(ProviderError(429, "rate limit"))
    assert not _ai_error_is_non_retryable(ProviderError(529, "overloaded"))


def test_byesu_observed_usd_rates_reproduce_real_comment_charge(monkeypatch):
    monkeypatch.setenv("AI_INPUT_COST_PER_MILLION_USD", "0.4")
    monkeypatch.setenv("AI_OUTPUT_COST_PER_MILLION_USD", "2.0")
    # Живой smoke 06.08.2026: 7 331 input + 2 000 output = $0.0069324.
    assert _model_cost_usd(7331, 2000) == Decimal("0.0069324")


def test_ruble_cost_has_no_stale_proxyapi_default(monkeypatch):
    for name in (
        "AI_INPUT_COST_PER_MILLION_RUB",
        "AI_OUTPUT_COST_PER_MILLION_RUB",
        "AI_CACHE_WRITE_COST_PER_MILLION_RUB",
        "AI_CACHE_READ_COST_PER_MILLION_RUB",
    ):
        monkeypatch.delenv(name, raising=False)
    assert _model_cost_rub(7331, 2000) == Decimal("0")
