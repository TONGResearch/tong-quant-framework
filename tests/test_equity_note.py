"""Display fixtures are not provider or financial-policy qualification."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta, timezone
from hashlib import sha256
from zoneinfo import ZoneInfo

import pytest

from tong_quant.application.equity_note import render_equity_note
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.research.trend import TrendResearchModule
from tong_quant.version import TREND_PRICE_OBSERVATIONS_VERSION

AT = "2026-11-08T09:18:31+00:00"
FLAGS = {name: False for name in ("execution_authorized", "validation_authorized",
    "investment_scoring_authorized", "historical_replay_eligible", "financial_scoring_authorized")}


def _hashed(body, key="input_hash"):
    return {**body, key: sha256(financial_input_json(body).encode()).hexdigest()}


def _document():
    return {"research_only": True, "research_report_created": False, "readiness_promoted": False,
        "inputs": _hashed({**FLAGS, "subject": "TEST", "market": "us", "as_of": AT,
            "status": "observed_unqualified", "observed_bar_count": 300,
            "trust_ceiling": "LOW", "availability_precision": "retrieval_time",
            "freshness": "UNASSESSED"}),
        "diagnostics": {"technical_research_only": True, "technical_scoring_admitted": False,
            "technical_confluence": "CONFLICTED", "technical_latest_close": 186.63999938964844,
            "setup_state": "INVALIDATED", "setup_direction": "bullish",
            "structural_invalidation_reference": 211.56789,
            "dynamic_invalidation_reference": 212.56789,
            "triple_average_events": "", "granville_events": "", "technical_missing_inputs": ""}}


def _with_financials(doc):
    doc["fundamentals"] = _hashed({**FLAGS, "subject": "TEST", "market": "us", "as_of": AT})
    doc["fundamentals_status"] = "observed_unqualified"
    doc["financial_review"] = _hashed({**FLAGS, "subject": "TEST", "market": "us", "as_of": AT,
        "source_input_hash": doc["fundamentals"]["input_hash"], "status": "EXPLORATORY_REVIEW",
        "comparisons": [{"native_metric": "annualTotalRevenue", "current_period_end": "2026-01-31",
            "prior_period_end": "2025-01-31", "current_value": "1200000", "currency": "USD",
            "native_change_percent": "20.0000", "status": "DESCRIPTIVE_UNQUALIFIED"}]},
        "review_hash")
    return doc


def test_note_is_readable_deterministic_and_does_not_mutate_input():
    doc = _document()
    before = deepcopy(doc)
    note = render_equity_note(doc)
    assert note == render_equity_note(doc) and doc == before
    assert "186.64" in note and "186.639999" not in note
    assert "LOW" in note and "UNASSESSED" in note
    assert "211.56789" not in note and "212.56789" not in note
    assert "ResearchReport" in note and "不是正式" in note
    assert "四确认" in note and "七加一" in note and "未请求基本面" in note


@pytest.mark.parametrize("alignment", ["BULLISH_TECHNICAL_ALIGNMENT",
    "BEARISH_TECHNICAL_ALIGNMENT", "CONFLICTED", "NEUTRAL", "INSUFFICIENT_DATA", "UNKNOWN"])
def test_alignment_never_becomes_validated_advice(alignment):
    doc = _document()
    doc["diagnostics"]["technical_confluence"] = alignment
    note = render_equity_note(doc)
    assert "已验证买卖信号" in note and "未完成独立验证" in note


@pytest.mark.parametrize("name", ["execution_authorized", "validation_authorized",
                                  "investment_scoring_authorized", "historical_replay_eligible"])
def test_admitted_top_level_input_is_rejected(name):
    doc = _document()
    doc[name] = True
    with pytest.raises(ValueError):
        render_equity_note(doc)


def test_tampered_receipt_and_secret_shaped_fields_are_rejected():
    doc = _document()
    doc["inputs"]["subject"] = "OTHER"
    with pytest.raises(ValueError, match="hash mismatch"):
        render_equity_note(doc)
    doc = _document()
    doc["password"] = "synthetic-rejected"
    with pytest.raises(ValueError):
        render_equity_note(doc)


@pytest.mark.parametrize("kind", ["subject", "cutoff", "hash", "authorization"])
def test_mismatched_or_tampered_financial_review_is_rejected(kind):
    doc = _with_financials(_document())
    review = doc["financial_review"]
    if kind == "subject":
        review["subject"] = "OTHER"
    elif kind == "cutoff":
        review["as_of"] = "2026-11-08T10:00:00+00:00"
    elif kind == "hash":
        review["comparisons"][0]["current_value"] = "9999999"
    else:
        review["financial_scoring_authorized"] = True
    if kind != "hash":
        doc["financial_review"] = _hashed(
            {key: value for key, value in review.items() if key != "review_hash"}, "review_hash")
    with pytest.raises(ValueError):
        render_equity_note(doc)


def test_native_financial_change_is_descriptive_not_verified_business_growth():
    note = render_equity_note(_with_financials(_document()))
    assert "1200000" in note and "20.0000" in note
    assert "不证明会计可比性" in note and "不代替最新财报" in note


@pytest.mark.parametrize("direction", ["bullish", "bearish"])
def test_only_active_setup_references_are_displayed_with_direction_and_caveat(direction):
    doc = _document()
    doc["diagnostics"].update(setup_state="ARMED", setup_direction=direction)
    note = render_equity_note(doc)
    assert "211.56789" in note and direction in note and "不是持仓止损价" in note


def test_display_escapes_markup_and_does_not_turn_missing_values_into_zero():
    doc = _document()
    doc["diagnostics"]["technical_missing_inputs"] = "<script>\n[link](x)|cell"
    note = render_equity_note(doc)
    assert "<script>" not in note and "&lt;script&gt;" in note
    assert "\\[link\\]" in note and "\\|cell" in note
    assert "| MACD DIF | 未取得 |" in note


@pytest.mark.parametrize("kind", ["missing", "wrong_subject", "admitted"])
def test_optional_trend_view_keeps_missing_confirmations_and_rejects_wrong_context(kind):
    from datetime import datetime

    doc = _document()
    result = TrendResearchModule().price_observations((), as_of=datetime.fromisoformat(AT))
    assert result["model_version"] == TREND_PRICE_OBSERVATIONS_VERSION
    if kind == "wrong_subject":
        result["subject"] = "OTHER"
    elif kind == "admitted":
        result["validation_authorized"] = True
    doc["trend_price_observations"] = _hashed(
        {key: value for key, value in result.items() if key != "input_hash"})
    if kind == "missing":
        note = render_equity_note(doc)
        assert "改进海龟价格与成交量观测" in note and "完整四确认未齐" in note
    else:
        with pytest.raises(ValueError, match="trend observations mismatch"):
            render_equity_note(doc)


def _with_cutoffs(price, fundamentals, review):
    doc = _with_financials(_document())
    for name, cutoff, hash_key in (("inputs", price, "input_hash"),
        ("fundamentals", fundamentals, "input_hash"),
        ("financial_review", review, "review_hash")):
        body = {key: value for key, value in doc[name].items() if key != hash_key}
        body["as_of"] = cutoff
        if name == "financial_review":
            body["source_input_hash"] = doc["fundamentals"]["input_hash"]
        doc[name] = _hashed(body, hash_key)
    return doc


@pytest.mark.parametrize("fold", [0, 1])
@pytest.mark.parametrize("mismatch", ["fundamentals", "review"])
def test_repeated_wall_clock_cutoffs_must_match_actual_instant(fold, mismatch):
    price = datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo("America/New_York"), fold=fold)
    other = price.replace(fold=1 - fold)
    doc = _with_cutoffs(price, other if mismatch == "fundamentals" else price, other)
    with pytest.raises(ValueError, match="financial input context mismatch"):
        render_equity_note(doc)


@pytest.mark.parametrize("strings", [False, True])
@pytest.mark.parametrize("with_trend", [False, True])
def test_equivalent_timezone_labels_share_one_financial_and_trend_cutoff(strings, with_trend):
    price = datetime.fromisoformat(AT)
    fundamental = price.astimezone(timezone(timedelta(hours=8)))
    review = price.astimezone(ZoneInfo("America/New_York"))
    if strings:
        price, fundamental, review = (value.isoformat() for value in (price, fundamental, review))
    doc = _with_cutoffs(price, fundamental, review)
    if with_trend:
        trend = TrendResearchModule().price_observations((), as_of=datetime.fromisoformat(AT))
        trend["as_of"] = review
        doc["trend_price_observations"] = _hashed(
            {key: value for key, value in trend.items() if key != "input_hash"})
    before = financial_input_json(doc)
    note = render_equity_note(doc)
    assert f"分析时点（UTC）：{AT}" in note
    assert ("完整四确认未齐" in note) is with_trend
    assert financial_input_json(doc) == before


@pytest.mark.parametrize("cutoff", [None, 1, "invalid", "2026-11-08T09:18:31",
                                  datetime(2026, 11, 8, 9, 18, 31)])
@pytest.mark.parametrize("target", ["inputs", "fundamentals", "financial_review", "trend"])
def test_every_display_cutoff_requires_an_aware_datetime(cutoff, target):
    values = {"inputs": AT, "fundamentals": AT, "financial_review": AT}
    if target in values:
        values[target] = cutoff
    doc = _with_cutoffs(values["inputs"], values["fundamentals"], values["financial_review"])
    if target == "trend":
        trend = TrendResearchModule().price_observations((), as_of=datetime.fromisoformat(AT))
        trend["as_of"] = cutoff
        doc["trend_price_observations"] = _hashed(
            {key: value for key, value in trend.items() if key != "input_hash"})
    with pytest.raises(ValueError):
        render_equity_note(doc)


@pytest.mark.parametrize("fold", [0, 1])
def test_trend_receipt_cannot_use_a_different_repeated_instant(fold):
    price = datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo("America/New_York"), fold=fold)
    doc = _with_cutoffs(price, price, price)
    trend = TrendResearchModule().price_observations((), as_of=price.astimezone(UTC))
    trend["as_of"] = price.replace(fold=1 - fold)
    doc["trend_price_observations"] = _hashed(
        {key: value for key, value in trend.items() if key != "input_hash"})
    with pytest.raises(ValueError, match="trend observations mismatch"):
        render_equity_note(doc)


@pytest.mark.parametrize("target", ["inputs", "fundamentals", "financial_review", "trend"])
def test_missing_cutoff_is_rejected_even_with_a_matching_receipt_hash(target):
    doc = _with_financials(_document())
    if target == "trend":
        doc["trend"] = TrendResearchModule().price_observations(
            (), as_of=datetime.fromisoformat(AT))
    key = "review_hash" if target == "financial_review" else "input_hash"
    body = {name: value for name, value in doc[target].items() if name not in {key, "as_of"}}
    doc[target] = _hashed(body, key)
    if target == "fundamentals":
        review = {name: value for name, value in doc["financial_review"].items()
                  if name != "review_hash"}
        review["source_input_hash"] = doc["fundamentals"]["input_hash"]
        doc["financial_review"] = _hashed(review, "review_hash")
    if target == "trend":
        doc["trend_price_observations"] = doc.pop("trend")
    with pytest.raises(ValueError):
        render_equity_note(doc)
