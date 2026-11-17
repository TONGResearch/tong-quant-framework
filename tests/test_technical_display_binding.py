"""Synthetic recomputation guards; never actual price/source qualification."""

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
from zoneinfo import ZoneInfo

import pytest

from tong_quant.application.equity_note import render_equity_note
from tong_quant.application.technical_binding import build_technical_binding
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.global_price_inputs import GlobalPriceInputs
from tong_quant.domain.enums import AssetType, Market
from tong_quant.domain.models import Bar, Instrument
from tong_quant.research.technical.diagnostics import technical_diagnostics
from tong_quant.research.technical.indicators import TechnicalParameters
from tong_quant.version import EQUITY_BOUND_NOTE_VERSION, TECHNICAL_DISPLAY_BINDING_VERSION

AT = datetime(2026, 11, 8, 9, 18, 31, tzinfo=UTC)
PARAMETERS = TechnicalParameters()


def _snapshot(*, as_of=AT, empty=False):
    instrument = Instrument("MSFT", Market.US, "Synthetic display fixture", currency="USD")
    start = datetime(2025, 1, 1, tzinfo=UTC)
    bars = tuple(Bar(instrument=instrument, timestamp=start + timedelta(days=index),
        open=Decimal(10 + index), high=Decimal(11 + index), low=Decimal(9 + index),
        close=Decimal(10 + index), volume=Decimal(1000),
        available_at=start + timedelta(days=index, hours=16), source="synthetic")
        for index in range(40))
    return GlobalPriceInputs("MSFT", Market.US, as_of,
        "missing" if empty else "observed_unqualified", () if empty else bars,
        (), None, "UNASSESSED", None, None)


def _document(snapshot):
    return {"inputs": snapshot.document(), "research_only": True,
        "research_report_created": False, "readiness_promoted": False,
        "diagnostics": technical_diagnostics(snapshot.bars, PARAMETERS, as_of=snapshot.as_of)}


def _bound(snapshot):
    document = _document(snapshot)
    document["technical_binding"] = build_technical_binding(snapshot, PARAMETERS, document)
    return document


def _render(document, snapshot, parameters=PARAMETERS):
    return render_equity_note(document, technical_source=snapshot, technical_parameters=parameters)


def _rehash(receipt):
    key = "binding_hash"
    body = {name: value for name, value in receipt.items() if name != key}
    return {**body, key: sha256(financial_input_json(body).encode()).hexdigest()}


def test_bound_note_recomputes_is_deterministic_and_preserves_legacy_document():
    source = _snapshot()
    legacy = _document(source)
    legacy_bytes = financial_input_json(legacy)
    legacy_note = render_equity_note(legacy)
    document = _bound(source)
    before = financial_input_json(document)
    note = _render(document, source)
    assert note == _render(document, source)
    assert before == financial_input_json(document)
    assert legacy_bytes == financial_input_json(legacy)
    assert legacy_note == render_equity_note(legacy)
    assert "日线技术展示绑定" in note and EQUITY_BOUND_NOTE_VERSION in note
    assert "不证明数据真实" in note and "不授权评分" in note
    assert document["technical_binding"]["model_version"] == TECHNICAL_DISPLAY_BINDING_VERSION


@pytest.mark.parametrize("kind", ["symbol", "market", "cutoff", "prices", "source", "rows"])
def test_original_six_mixed_diagnostic_counterexamples_are_rejected(kind):
    source = _snapshot()
    document = _bound(source)
    bars, cutoff = source.bars, source.as_of
    if kind == "symbol":
        bars = tuple(replace(bar, instrument=replace(bar.instrument, symbol="NVDA"))
                     for bar in bars)
    elif kind == "market":
        instrument = Instrument("1155.KL", Market.MALAYSIA, "Synthetic", currency="MYR")
        bars = tuple(replace(bar, instrument=instrument) for bar in bars)
    elif kind == "cutoff":
        cutoff += timedelta(hours=1)
    elif kind == "prices":
        bars = tuple(replace(bar, open=bar.open * 2, high=bar.high * 2,
            low=bar.low * 2, close=bar.close * 2) for bar in bars)
    elif kind == "source":
        bars = tuple(replace(bar, source="other_synthetic") for bar in bars)
    else:
        bars = bars[:-1]
    document["diagnostics"] = technical_diagnostics(bars, PARAMETERS, as_of=cutoff)
    with pytest.raises(ValueError, match="recomputation mismatch"):
        _render(document, source)
    with pytest.raises(ValueError, match="recomputation mismatch"):
        build_technical_binding(source, PARAMETERS, document)


@pytest.mark.parametrize("field,value", [
    ("subject", "NVDA"), ("market", "malaysia"), ("as_of", "2026-11-08T10:18:31+00:00"),
    ("source_bars_content_hash", "f" * 64), ("supplied_daily_row_count", 39),
    ("diagnostics_content_hash", "f" * 64), ("price_input_hash", "f" * 64),
    ("technical_input_hash", "f" * 64), ("parameters_json", "{}"),
    ("technical_calculations_version", "unknown"), ("model_version", "unknown"),
    ("source_qualified", True), ("pit_qualified", True), ("execution_authorized", True),
    ("validation_authorized", True), ("scoring_authorized", True),
    ("historical_replay_eligible", True), ("holding_management_authorized", True),
    ("research_only", False), ("source_qualified", 0),
])
def test_receipt_contradictions_fail_even_after_rehash(field, value):
    source = _snapshot()
    document = _bound(source)
    document["technical_binding"][field] = value
    document["technical_binding"] = _rehash(document["technical_binding"])
    with pytest.raises(ValueError, match="binding mismatch"):
        _render(document, source)


def test_rehashing_both_forged_diagnostic_and_receipt_cannot_replace_recomputation():
    source = _snapshot()
    document = _bound(source)
    document["diagnostics"]["technical_latest_close"] = 999.0
    document["technical_binding"]["diagnostics_content_hash"] = sha256(
        financial_input_json(document["diagnostics"]).encode()).hexdigest()
    document["technical_binding"] = _rehash(document["technical_binding"])
    with pytest.raises(ValueError, match="recomputation mismatch"):
        _render(document, source)


@pytest.mark.parametrize("kind", ["absent", "null", "empty", "extra"])
def test_missing_or_malformed_receipt_cannot_gain_bound_display(kind):
    source = _snapshot()
    document = _bound(source)
    if kind == "absent":
        document.pop("technical_binding")
    elif kind == "null":
        document["technical_binding"] = None
    elif kind == "empty":
        document["technical_binding"] = {}
    else:
        document["technical_binding"]["extra"] = False
        document["technical_binding"] = _rehash(document["technical_binding"])
    with pytest.raises(ValueError):
        _render(document, source)


@pytest.mark.parametrize("provided", ["none", "source", "parameters"])
def test_receipt_without_complete_original_inputs_is_rejected(provided):
    source = _snapshot()
    document = _bound(source)
    kwargs = {}
    if provided == "source":
        kwargs["technical_source"] = source
    elif provided == "parameters":
        kwargs["technical_parameters"] = PARAMETERS
    with pytest.raises(ValueError, match="original snapshot and parameters"):
        render_equity_note(document, **kwargs)


@pytest.mark.parametrize("fold", [0, 1])
def test_actual_utc_cutoff_not_repeated_local_wall_time(fold):
    at = datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo("America/New_York"), fold=fold)
    source = _snapshot(as_of=at)
    document = _bound(source)
    assert "日线技术展示绑定" in _render(document, source)
    with pytest.raises(ValueError, match="cutoff mismatch"):
        _render(document, replace(source, as_of=at.replace(fold=1 - fold)))


def test_equivalent_cutoff_timezone_labels_are_allowed_without_rewriting_receipts():
    source = _snapshot()
    document = _bound(source)
    before = financial_input_json(document)
    same = replace(source, as_of=source.as_of.astimezone(timezone(timedelta(hours=8))))
    assert _render(document, source) == _render(document, same)
    assert before == financial_input_json(document)


@pytest.mark.parametrize("field,value", [("subject", "NVDA"), ("market", Market.MALAYSIA),
    ("status", "stale_observation"), ("freshness", "WITHIN_LIMIT")])
def test_snapshot_metadata_cannot_be_replaced_or_made_favorable(field, value):
    source = _snapshot()
    document = _bound(source)
    with pytest.raises(ValueError):
        _render(document, replace(source, **{field: value}))


def test_parameters_and_instrument_metadata_are_bound():
    source = _snapshot()
    document = _bound(source)
    with pytest.raises(ValueError, match="recomputation mismatch"):
        _render(document, source, replace(PARAMETERS, macd_fast=10))
    changed = replace(source, bars=tuple(replace(bar, instrument=replace(
        bar.instrument, name="Different retained metadata")) for bar in source.bars))
    with pytest.raises(ValueError, match="price snapshot mismatch"):
        _render(document, changed)
    fund = replace(source, bars=tuple(replace(bar, instrument=replace(
        bar.instrument, asset_type=AssetType.ETF)) for bar in source.bars))
    with pytest.raises(ValueError, match="identity mismatch"):
        _render(document, fund)


@pytest.mark.parametrize("mode", ["missing", "latest_suspended", "duplicate"])
def test_missing_suspension_and_full_original_rows_are_preserved(mode):
    source = _snapshot(empty=mode == "missing")
    if mode == "latest_suspended":
        source = replace(source, bars=(*source.bars[:-1], replace(
            source.bars[-1], is_suspended=True)))
    if mode == "duplicate":
        source = replace(source, bars=(*source.bars, source.bars[-1]))
    document = _bound(source)
    original = deepcopy(document)
    note = _render(document, source)
    assert document == original and "不授权评分" in note
    if mode == "duplicate":
        assert document["technical_binding"]["supplied_daily_row_count"] == 41
        assert document["diagnostics"]["technical_usable_observations"] == 40
    else:
        assert document["diagnostics"]["technical_usable_observations"] == 0
        assert document["diagnostics"]["technical_latest_close"] is None


def test_future_original_availability_is_rejected_without_fallback():
    source = _snapshot()
    source = replace(source, bars=(*source.bars[:-1], replace(
        source.bars[-1], available_at=AT + timedelta(seconds=1))))
    document = {"inputs": source.document(), "diagnostics": {}, "research_only": True,
                "research_report_created": False, "readiness_promoted": False}
    with pytest.raises(ValueError, match="future data"):
        build_technical_binding(source, PARAMETERS, document)


@pytest.mark.parametrize("field,value", [("research_only", False),
    ("research_report_created", True), ("readiness_promoted", True),
    ("execution_authorized", True), ("validation_authorized", True),
    ("investment_scoring_authorized", True), ("historical_replay_eligible", True),
    ("financial_scoring_authorized", True)])
def test_binding_builder_cannot_label_admitted_or_nonresearch_document(field, value):
    source = _snapshot()
    document = _document(source)
    document[field] = value
    with pytest.raises(ValueError, match="unqualified research"):
        build_technical_binding(source, PARAMETERS, document)
