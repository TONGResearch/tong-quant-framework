"""Synthetic retained-source co-display cannot complete a calendar or admit prices."""

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256

import pytest

from tong_quant.application.calendar_review import read_nasdaq_price_review
from tong_quant.application.equity_note import render_equity_note
from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.global_price_inputs import GlobalPriceInputs
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.providers import nasdaq_calendar as source
from tong_quant.data.providers.contracts import ProviderDatasetRequest
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.domain.models import Bar, Instrument
from tong_quant.research.technical.diagnostics import technical_diagnostics
from tong_quant.research.technical.indicators import TechnicalParameters

AT = datetime(2026, 11, 7, tzinfo=UTC)
BODY = b"""<h1>U.S. Equity and Options Markets Holiday Schedule 2026</h1>
<table><tr><th>2026</th><th>Holiday</th><th>Status</th></tr>
<tr><td>November 3, 2026</td><td>Synthetic closure</td><td>Closed</td></tr>
<tr><td>November 27, 2026</td><td>Early Close synthetic</td><td>1:00 p.m.</td></tr>
</table>"""


def _prices(at=AT):
    instrument = Instrument("MSFT", Market.US, "Synthetic", currency="USD", exchange="fixture")
    bars = tuple(Bar(instrument, datetime(2026, 11, day, 15, tzinfo=UTC),
        datetime(2026, 11, day, 22, tzinfo=UTC), Decimal(10), Decimal(12), Decimal(9),
        Decimal(11), Decimal(100), source="synthetic-only") for day in range(2, 7))
    return GlobalPriceInputs("MSFT", Market.US, at, "observed_unqualified", bars, (), None,
                             "UNASSESSED", None, None)


@pytest.fixture
def foundation(tmp_path):
    store = SQLiteStore(tmp_path / "calendar.sqlite3")
    store.initialize()
    artifacts = FileSystemArtifactStore(tmp_path / "raw")
    _ingest(store, artifacts)
    return store, artifacts


def _ingest(store, artifacts, *, at=AT, fail=False, body=BODY):
    request = ProviderDatasetRequest(source.DATASET, Market.US, "NASDAQ:2026", at,
                                     {"year": "2026"})
    capture = source.NasdaqCalendarCapture(None, "http_403") if fail else (
        source.NasdaqCalendarCapture(body))
    return ProviderNeutralIngestionService(store, artifact_store=artifacts,
        clock=lambda: at).ingest(source.NasdaqCalendarAdapter(
            download=lambda _: capture, clock=lambda: at), request)


def _read(foundation, prices=None, age=3600, shared=False):
    return read_nasdaq_price_review(prices or _prices(), *foundation, 2026,
        maximum_source_age_seconds=age, shared_database=shared)


def _document(foundation, prices=None):
    prices = prices or _prices()
    return {"inputs": prices.document(), "research_only": True,
        "diagnostics": technical_diagnostics(prices.bars, TechnicalParameters(),
                                             as_of=prices.as_of),
        "research_report_created": False, "readiness_promoted": False,
        "nasdaq_calendar_review": _read(foundation, prices)}


def _rehash(receipt):
    receipt["input_hash"] = sha256(financial_input_json(
        {key: value for key, value in receipt.items() if key != "input_hash"}).encode()).hexdigest()


@pytest.mark.parametrize("shared", [False, True])
def test_source_dates_preserve_conflict_native_early_close_and_no_inference(foundation, shared):
    store, _ = foundation
    before = store.path.read_bytes()
    result = _read(foundation, shared=shared)
    assert result == _read(foundation, shared=shared)
    closed, early = result["declaration_comparisons"]
    assert closed["closed_date_observation_conflict"] is True
    assert early["core_close_local"] == "13:00:00" and early["future_schedule_date"]
    assert early["price_date_observed"] is None
    assert result["source"]["trust_ceiling"] == "LOW"
    assert result["source"]["availability_precision"] == "retrieval_time"
    for key in ("exchange_binding_verified", "calendar_complete", "canonical_calendar_authorized",
        "session_completeness_verified", "scoring_authorized", "investment_scoring_authorized",
        "historical_replay_eligible", "validation_authorized", "execution_authorized"):
        assert result[key] is False
    assert len(result["declaration_comparisons"]) == 2
    assert store.path.read_bytes() == before and store.table_count("trading_calendar") == 0


@pytest.mark.parametrize("kind", ["stale", "future", "failure", "missing_prices", "suspended"])
def test_bad_or_missing_inputs_never_fallback_or_invent_dates(foundation, kind):
    prices = _prices()
    if kind == "stale":
        prices = replace(prices, as_of=AT + timedelta(hours=2))
    elif kind == "future":
        prices = replace(prices, as_of=AT - timedelta(microseconds=1))
    elif kind == "failure":
        _ingest(*foundation, at=AT + timedelta(seconds=1), fail=True)
        prices = replace(prices, as_of=AT + timedelta(seconds=1))
    elif kind == "missing_prices":
        prices = replace(prices, bars=())
    elif kind == "suspended":
        prices = replace(prices, bars=(*prices.bars[:-1], replace(
            prices.bars[-1], is_suspended=True)))
    result = _read(foundation, prices)
    if kind in {"stale", "future", "failure"}:
        assert result["declaration_comparisons"] == []
    else:
        assert all(row["price_date_observed"] is None for row in result["declaration_comparisons"])
    if kind == "stale":
        assert len(result["source"]["observed_declarations"]) == 2
        assert result["source"]["freshness"] == "STALE"
    note = render_equity_note(_document(foundation, prices))
    assert "Nasdaq 原文日历证据" in note and "不改变上方覆盖率" in note


@pytest.mark.parametrize("age", [True, 0, -1, 1.5, None])
def test_invalid_age_is_rejected(foundation, age):
    with pytest.raises(ValueError):
        _read(foundation, age=age)


@pytest.mark.parametrize("kind", ["market", "subject", "future_bar"])
def test_price_context_mismatch_rejected(foundation, kind):
    prices = _prices()
    if kind == "market":
        prices = replace(prices, market=Market.HONG_KONG)
    elif kind == "subject":
        prices = replace(prices, subject="OTHER")
    else:
        prices = replace(prices, as_of=AT - timedelta(days=2))
    with pytest.raises(ValueError):
        _read(foundation, prices)


@pytest.mark.parametrize("key,value", [
    ("price_input_hash", "a" * 64), ("subject", "OTHER"), ("market", "hong_kong"),
    ("as_of", AT + timedelta(seconds=1)), ("exchange_binding_verified", True),
    ("calendar_complete", True), ("canonical_calendar_authorized", True),
    ("investment_scoring_authorized", True), ("snapshot_scope", "atomic_verified"),
])
def test_rehashed_review_tampering_cannot_be_rendered(foundation, key, value):
    document = deepcopy(_document(foundation))
    receipt = document["nasdaq_calendar_review"]
    receipt[key] = value
    _rehash(receipt)
    with pytest.raises(ValueError):
        render_equity_note(document)


@pytest.mark.parametrize("key,value", [
    ("trust_ceiling", "HIGH"), ("availability_precision", "exact"),
    ("as_of", AT + timedelta(seconds=1)), ("calendar_complete", True),
    ("execution_authorized", True), ("source_capture_at", AT + timedelta(seconds=1)),
    ("freshness", "STALE"), ("source_capture_age_microseconds", 1),
    ("source_capture_age_seconds", 1), ("source_bound", False),
])
def test_rehashed_nested_source_promotions_or_stale_rows_rejected(foundation, key, value):
    document = deepcopy(_document(foundation))
    receipt = document["nasdaq_calendar_review"]
    receipt["source"][key] = value
    _rehash(receipt["source"])
    _rehash(receipt)
    with pytest.raises(ValueError):
        render_equity_note(document)


def test_default_note_is_unchanged_and_new_note_has_native_times(foundation):
    document = _document(foundation)
    result = render_equity_note(document)
    assert "13:00:00" in result and "v7-nasdaq-comparison-context" in result
    document.pop("nasdaq_calendar_review")
    default = render_equity_note(document)
    assert "Nasdaq 原文日历证据" not in default
    assert "v7-nasdaq-comparison-context" not in default


def test_rehashed_future_schedule_flag_cannot_claim_an_observed_session(foundation):
    document = _document(foundation)
    receipt = document["nasdaq_calendar_review"]
    receipt["declaration_comparisons"][-1]["future_schedule_date"] = False
    _rehash(receipt)
    with pytest.raises(ValueError, match="declaration mismatch"):
        render_equity_note(document)


@pytest.mark.parametrize("kind,expected", [
    ("conflict", "候选日期冲突（未核验）"),
    ("no_observation", "未见该日行情（非完整性认证）"),
    ("future", "未评估（未来计划日期）"),
    ("missing", "未评估（无可用行情对照）"),
    ("suspended", "未评估（无可用行情对照）"),
    ("outside", "未评估（行情区间外）"),
    ("early", "未评估（缺盘中时段依据）"),
])
def test_date_comparison_view_distinguishes_unassessed_from_candidate_conflicts(
    foundation, kind, expected,
):
    prices = _prices()
    if kind == "no_observation":
        prices = replace(prices, bars=tuple(bar for bar in prices.bars if bar.timestamp.day != 3))
    elif kind == "missing":
        prices = replace(prices, bars=())
    elif kind == "suspended":
        prices = replace(prices, bars=(*prices.bars[:-1], replace(
            prices.bars[-1], is_suspended=True)))
    elif kind == "outside":
        prices = replace(prices, bars=prices.bars[2:])
    elif kind == "early":
        at = AT + timedelta(seconds=1)
        _ingest(*foundation, at=at, body=BODY.replace(b"November 27", b"November 5"))
        prices = replace(prices, as_of=at)
    document = _document(foundation, prices)
    original = financial_input_json(document)
    note = render_equity_note(document)
    table = note.split("| 声明日期 |", 1)[1].split("提前收市时间属于来源", 1)[0]
    assert expected in table and "行情日期冲突" not in table
    assert "v7-nasdaq-comparison-context" in note
    assert financial_input_json(document) == original
    assert document["nasdaq_calendar_review"]["model_version"] == "nasdaq-price-source-review-v1"


@pytest.mark.parametrize("key,value", [
    ("closed_date_observation_conflict", False),
    ("closed_date_observation_conflict", 1),
    ("within_price_observation_span", False),
    ("within_price_observation_span", 1),
    ("price_date_observed", None),
    ("price_date_observed", False),
    ("price_date_observed", 1),
    ("future_schedule_date", 0),
])
def test_rehashed_contradictory_date_comparison_cannot_hide_candidate_conflict(
    foundation, key, value,
):
    document = _document(foundation)
    receipt = document["nasdaq_calendar_review"]
    receipt["declaration_comparisons"][0][key] = value
    _rehash(receipt)
    with pytest.raises(ValueError, match="Nasdaq (comparison state|declaration) mismatch"):
        render_equity_note(document)
