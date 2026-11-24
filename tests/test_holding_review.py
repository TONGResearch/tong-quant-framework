"""Owner annotations and synthetic calculations are not authenticated positions or advice."""

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import ROUND_DOWN, ROUND_UP, Decimal, localcontext
from hashlib import sha256
from zoneinfo import ZoneInfo

import pytest

from tong_quant.application.equity_note import render_equity_note
from tong_quant.application.holding_review import build_holding_review, parse_holding_context
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.global_price_inputs import GlobalPriceInputs
from tong_quant.domain.enums import Adjustment, AssetType, Market
from tong_quant.domain.models import Bar, Instrument
from tong_quant.research.technical.diagnostics import technical_diagnostics
from tong_quant.research.technical.indicators import TechnicalParameters

NOW = datetime(2026, 11, 10, 22, tzinfo=UTC)


def _annotation():
    return {"holding": {"symbol": "TEST", "market": "us", "currency": "USD",
        "quantity": "0.2468", "reported_average_cost": "10", "investment_intent": "long_term",
        "loss_review_percent": "30", "observed_at": (NOW - timedelta(days=1)).isoformat(),
        "recorded_at": NOW.isoformat(),
        "maximum_context_age_seconds": 86400, "maximum_price_age_seconds": 86400}}


def _snapshot():
    instrument = Instrument("TEST", Market.US, "Synthetic", currency="USD")
    bars = tuple(Bar(instrument, NOW - timedelta(days=300 - index), NOW,
        Decimal(10), Decimal(11), Decimal(9), Decimal(10), Decimal(100), source="synthetic")
        for index in range(300))
    return GlobalPriceInputs("TEST", Market.US, NOW, "observed_unqualified", bars, (),
                             "synthetic", "UNASSESSED", 86400, None)


def _review(annotation=None, snapshot=None):
    return build_holding_review(parse_holding_context(annotation or _annotation()),
                                snapshot or _snapshot(), TechnicalParameters())


def _document(snapshot=None, review=None):
    snapshot = snapshot or _snapshot()
    return {"inputs": snapshot.document(), "diagnostics": technical_diagnostics(
        snapshot.bars, TechnicalParameters(), as_of=snapshot.as_of),
        "research_only": True, "research_report_created": False, "readiness_promoted": False,
        "holding_review": review or _review(snapshot=snapshot)}


def test_deterministic_readonly_review_preserves_limits_and_withholds_authority():
    annotation = _annotation()
    before = deepcopy(annotation)
    result = _review(annotation)
    assert result == _review(annotation) and annotation == before
    assert result["comparison_status"] == "OBSERVED_UNQUALIFIED"
    assert Decimal(result["price_only_change_percent"]) == 0
    assert result["observed_position_value"] == "2.4680"
    assert result["holding_horizon"] == "NOT_ESTIMATED"
    assert result["thesis_invalidation"] == "NOT_EVALUATED"
    assert result["owner_context"]["borrowed_funds_status"] == "UNKNOWN"
    assert result["trust_ceiling"] == "LOW"
    assert result["availability_precision"] == "retrieval_time"
    assert all(value is False for key, value in result.items()
               if key.endswith("_authorized") or key == "historical_replay_eligible")
    digest = result.pop("review_hash")
    assert digest == sha256(financial_input_json(result).encode()).hexdigest()


@pytest.mark.parametrize("price,expected", [("7", "REVIEW_REQUIRED"),
    ("6.99", "REVIEW_REQUIRED"), ("7.01", "NOT_REACHED_ON_THIS_OBSERVATION")])
def test_owner_loss_alert_is_exact_and_never_a_sell_instruction(price, expected):
    snapshot = _snapshot()
    latest = replace(snapshot.bars[-1], open=Decimal(price), low=Decimal(price),
                     high=Decimal(price), close=Decimal(price))
    result = _review(snapshot=replace(snapshot, bars=(*snapshot.bars[:-1], latest)))
    assert result["loss_review_status"] == expected
    assert result["exit_review"] == "RESEARCH_REVIEW_ONLY_NO_SELL_INSTRUCTION"
    assert result["holding_management_authorized"] is False


@pytest.mark.parametrize("change,reason", [
    ({"observed_at": (NOW - timedelta(hours=23)).isoformat()},
     "PRICE_PREDATES_HOLDING_OBSERVATION"),
    ({"maximum_context_age_seconds": 86399}, "OWNER_CONTEXT_STALE"),
    ({"maximum_price_age_seconds": 86399}, "PRICE_OBSERVATION_STALE"),
])
def test_blocked_context_never_computes_pnl_or_reuses_old_price(change, reason):
    annotation = _annotation()
    annotation["holding"].update(change)
    result = _review(annotation)
    assert reason in result["blockers"] and result["comparison_status"] == "BLOCKED"
    assert result["price_only_change_percent"] is result["observed_position_value"] is None
    assert result["loss_review_status"] == "NOT_EVALUATED"


def test_missing_source_and_latest_suspension_do_not_fall_back():
    snapshot = _snapshot()
    for missing in (replace(snapshot, status="rejected_or_ambiguous", bars=()),
        replace(snapshot, bars=(*snapshot.bars[:-1],
                                replace(snapshot.bars[-1], is_suspended=True)))):
        result = _review(snapshot=missing)
        assert "CURRENT_PRICE_MISSING_OR_SUSPENDED" in result["blockers"]
        assert result["observed_position_value"] is None
        assert result["loss_review_status"] == "NOT_EVALUATED"


@pytest.mark.parametrize("field,value", [("quantity", "0"), ("quantity", "-1"),
    ("quantity", True), ("quantity", 0.1), ("quantity", "1e-999999"),
    ("reported_average_cost", "NaN"), ("reported_average_cost", "Infinity"),
    ("reported_average_cost", "1000000000000"), ("loss_review_percent", "101"),
    ("observed_at", "2026-10-01T12:00:00"), ("observed_at", "invalid"),
    ("maximum_context_age_seconds", True), ("maximum_price_age_seconds", 0),
    ("maximum_price_age_seconds", 999999999), ("currency", "MYR"),
    ("investment_intent", "buy"), ("symbol", "../invalid"), ("market", "china_a")])
def test_invalid_annotations_fail_closed_without_echoing_private_values(field, value):
    annotation = _annotation()
    annotation["holding"][field] = value
    with pytest.raises(ValueError):
        parse_holding_context(annotation)


@pytest.mark.parametrize("field", ["api_key", "execution_authorized", "account_number"])
def test_credentials_and_extra_authority_or_account_fields_are_not_accepted(field):
    annotation = _annotation()
    annotation["holding"][field] = None
    with pytest.raises(ValueError):
        parse_holding_context(annotation)


@pytest.mark.parametrize("kind", ["symbol", "market", "currency", "adjusted", "future_bar"])
def test_original_price_context_is_rechecked(kind):
    snapshot = _snapshot()
    if kind in {"symbol", "market"}:
        snapshot = replace(snapshot, **({"subject": "OTHER"} if kind == "symbol" else
                                        {"market": Market.HONG_KONG}))
    elif kind == "currency":
        snapshot = replace(snapshot, bars=tuple(replace(bar, instrument=replace(
            bar.instrument, currency="HKD")) for bar in snapshot.bars))
    elif kind == "adjusted":
        snapshot = replace(snapshot, bars=(replace(snapshot.bars[0], adjustment=Adjustment.FORWARD),
                                            *snapshot.bars[1:]))
    else:
        snapshot = replace(snapshot, bars=(*snapshot.bars, replace(snapshot.bars[-1],
            timestamp=NOW + timedelta(seconds=1), available_at=NOW + timedelta(seconds=1))))
    with pytest.raises(ValueError):
        _review(snapshot=snapshot)


def test_future_owner_observation_and_repeated_dst_labels_are_rejected():
    annotation = _annotation()
    annotation["holding"]["observed_at"] = (NOW + timedelta(seconds=1)).isoformat()
    annotation["holding"]["recorded_at"] = (NOW + timedelta(seconds=1)).isoformat()
    with pytest.raises(ValueError, match="later"):
        _review(annotation)
    clock = datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo("America/New_York"))
    context = replace(parse_holding_context(_annotation()), observed_at=clock.replace(fold=1),
                      recorded_at=clock.replace(fold=1))
    with pytest.raises(ValueError, match="later"):
        build_holding_review(context, replace(_snapshot(), as_of=clock), TechnicalParameters())


def test_equivalent_timezone_context_and_cutoff_have_identical_hashes():
    context = parse_holding_context(_annotation())
    snapshot = _snapshot()
    result = build_holding_review(context, snapshot, TechnicalParameters())
    other = build_holding_review(replace(context, observed_at=context.observed_at.astimezone(
        ZoneInfo("Asia/Kuala_Lumpur"))), replace(snapshot, as_of=NOW.astimezone(
            ZoneInfo("America/New_York"))), TechnicalParameters())
    assert other == result


def test_ambient_decimal_rounding_does_not_change_review_identity():
    annotation = _annotation()
    annotation["holding"]["reported_average_cost"] = "3"
    with localcontext() as context:
        context.rounding = ROUND_UP
        first = _review(annotation)
        context.rounding = ROUND_DOWN
        second = _review(annotation)
    assert first == second


def test_non_equity_bars_cannot_enter_equity_holding_review():
    snapshot = _snapshot()
    other = tuple(replace(bar, instrument=replace(bar.instrument, asset_type=AssetType.ETF))
                  for bar in snapshot.bars)
    with pytest.raises(ValueError):
        _review(snapshot=replace(snapshot, bars=other))


def test_declared_recording_must_be_visible_and_not_predate_observation():
    annotation = _annotation()
    annotation["holding"]["recorded_at"] = (NOW + timedelta(seconds=1)).isoformat()
    with pytest.raises(ValueError, match="recording is later"):
        _review(annotation)
    annotation["holding"]["recorded_at"] = (NOW - timedelta(days=2)).isoformat()
    with pytest.raises(ValueError):
        parse_holding_context(annotation)


def test_markdown_warns_on_pre_position_data_and_keeps_existing_technical_results():
    annotation = _annotation()
    annotation["holding"]["observed_at"] = (NOW - timedelta(hours=23)).isoformat()
    doc = _document(review=_review(annotation))
    before = deepcopy(doc)
    note = render_equity_note(doc)
    assert "PRICE_PREDATES_HOLDING_OBSERVATION" in note
    assert "NOT_ESTIMATED" in note and "NOT_EVALUATED" in note
    assert "0.2468" in note and "OWNER_CONTEXT_STALE" not in note
    assert doc == before


@pytest.mark.parametrize("key,value", [("subject", "OTHER"), ("as_of", NOW.isoformat()+"x"),
    ("source_input_hash", "0"*64), ("technical_input_hash", "0"*64),
    ("execution_authorized", True), ("holding_management_authorized", True)])
def test_rehashed_foreign_or_admitted_review_cannot_render(key, value):
    doc = _document()
    review = doc["holding_review"]
    review[key] = value
    body = {name: item for name, item in review.items() if name != "review_hash"}
    review["review_hash"] = sha256(financial_input_json(body).encode()).hexdigest()
    with pytest.raises(ValueError):
        render_equity_note(doc)


def _exit_annotation(**changes):
    annotation = _annotation()
    annotation["holding"].update(quantity="2", loss_review_percent="25")
    annotation["holding"].update(changes)
    return annotation


def _assert_no_holding_decision(result):
    assert result["exit_review"] == "RESEARCH_REVIEW_ONLY_NO_SELL_INSTRUCTION"
    assert result["holding_horizon"] == "NOT_ESTIMATED"
    assert result["thesis_invalidation"] == "NOT_EVALUATED"
    assert result["financial_review"] == "NOT_EVALUATED_BY_THIS_CHECK"
    assert result["holding_management_authorized"] is False
    assert result["validation_authorized"] is False
    assert result["execution_authorized"] is False
    assert "target_exit_price" not in result
    assert "recommended_action" not in result


@pytest.mark.parametrize("cost,expected", [
    ("4", "NOT_REACHED_ON_THIS_OBSERVATION"),
    ("10", "NOT_REACHED_ON_THIS_OBSERVATION"),
    ("25", "REVIEW_REQUIRED"),
])
def test_cost_changes_alert_not_technical_evidence_or_exit_permission(cost, expected):
    result = _review(_exit_annotation(reported_average_cost=cost))
    reference = _review(_exit_annotation())
    assert result["loss_review_status"] == expected
    assert result["technical_input_hash"] == reference["technical_input_hash"]
    assert result["trend_structure_family"] == reference["trend_structure_family"]
    assert result["momentum_family"] == reference["momentum_family"]
    _assert_no_holding_decision(result)


@pytest.mark.parametrize("kind", ["missing", "suspended", "stale", "rejected"])
def test_blocked_exit_review_is_neither_hold_approval_nor_thesis_failure(kind):
    snapshot = _snapshot()
    annotation = _exit_annotation()
    if kind == "missing":
        snapshot = replace(snapshot, bars=())
    elif kind == "suspended":
        snapshot = replace(snapshot, bars=(*snapshot.bars[:-1],
                                          replace(snapshot.bars[-1], is_suspended=True)))
    elif kind == "stale":
        annotation["holding"]["maximum_price_age_seconds"] = 86399
    else:
        snapshot = replace(snapshot, status="rejected_or_ambiguous")
    result = _review(annotation, snapshot)
    assert result["comparison_status"] == "BLOCKED" and result["blockers"]
    assert result["price_only_change_percent"] is None
    assert result["loss_review_status"] == "NOT_EVALUATED"
    _assert_no_holding_decision(result)


@pytest.mark.parametrize("rising,expected", [(True, "BULLISH"), (False, "BEARISH")])
def test_directional_technical_evidence_does_not_evaluate_an_exit_thesis(rising, expected):
    snapshot = _snapshot()
    bars = tuple(replace(bar, open=Decimal(100 + index if rising else 400 - index),
        close=Decimal(100 + index if rising else 400 - index),
        high=Decimal(101 + index if rising else 401 - index),
        low=Decimal(99 + index if rising else 399 - index))
        for index, bar in enumerate(snapshot.bars))
    result = _review(_exit_annotation(), replace(snapshot, bars=bars))
    assert result["momentum_family"] == expected
    _assert_no_holding_decision(result)


def test_cost_loss_review_cannot_establish_peak_or_portfolio_drawdown():
    snapshot = _snapshot()
    peak = replace(snapshot.bars[-2], open=Decimal(40), close=Decimal(40),
                   high=Decimal(41), low=Decimal(39))
    result = _review(_exit_annotation(), replace(snapshot,
        bars=(*snapshot.bars[:-2], peak, snapshot.bars[-1])))
    assert Decimal(result["price_only_change_percent"]) == 0
    assert result["loss_review_status"] == "NOT_REACHED_ON_THIS_OBSERVATION"
    assert "portfolio_drawdown" not in result and "maximum_drawdown" not in result
    _assert_no_holding_decision(result)


@pytest.mark.parametrize("intent", ["short_term", "medium_term", "long_term"])
def test_declared_horizon_never_automatically_validates_holding_or_event_exit(intent):
    result = _review(_exit_annotation(investment_intent=intent))
    assert result["owner_context"]["investment_intent"] == intent
    _assert_no_holding_decision(result)
