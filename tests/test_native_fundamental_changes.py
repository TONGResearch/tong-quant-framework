"""Native changes are retained record differences, never qualified accounting outcomes."""

import json
import runpy
import sqlite3
import subprocess
import sys
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from tong_quant.application import equity_changes as equity
from tong_quant.application import native_fundamental_changes as changes
from tong_quant.application.equity_changes import read_equity_change_digest
from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.providers.yahoo_fundamentals import NATIVE_METRICS, YahooFundamentalCapture
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.version import (
    EQUITY_NATIVE_CHANGE_DIGEST_VERSION,
    NATIVE_FUNDAMENTAL_CHANGE_VERSION,
)

AT = datetime(2026, 10, 27, 10, tzinfo=UTC)
LATER = AT + timedelta(seconds=1)
AGE = 3600  # Test capture-age limit only, not an operational freshness policy.


@lru_cache
def _helpers():
    return runpy.run_path(str(Path(__file__).with_name("test_global_fundamental_inputs.py")))


SCOPES = _helpers()["SCOPES"]


@pytest.fixture
def foundation(tmp_path):
    store = SQLiteStore(tmp_path / "native-changes.sqlite3")
    store.initialize()
    return store, FileSystemArtifactStore(tmp_path / "raw")


def _ingest(foundation, scope=SCOPES[0], *, at=AT, capture=None):
    return _helpers()["_ingest"](foundation, capture, scope=scope, at=at)


def _read(foundation, scope=SCOPES[0], *, previous=AT, current=LATER, age=AGE):
    return changes.read_native_fundamental_change_digest(
        SQLiteStore(foundation[0].path, read_only=True), foundation[1], scope[1], scope[0],
        previous_as_of=previous, as_of=current, maximum_capture_age_seconds=age)


def _footprint(foundation):
    paths = [foundation[0].path, *foundation[1].root.rglob("*.bin")]
    wal = foundation[0].path.with_name(foundation[0].path.name + "-wal")
    return {**{p: sha256(p.read_bytes()).hexdigest() for p in paths},
            wal: sha256(wal.read_bytes() if wal.exists() else b"").hexdigest()}


@pytest.mark.parametrize("scope", SCOPES)
@pytest.mark.parametrize("recapture", (False, True))
def test_identical_records_recompute_bindings_without_new_business_evidence(
    foundation, scope, recapture,
):
    _ingest(foundation, scope)
    if recapture:
        _ingest(foundation, scope, at=LATER)
    pins = _footprint(foundation)
    result = _read(foundation, scope)
    assert result == _read(foundation, scope)
    assert result["model_version"] == NATIVE_FUNDAMENTAL_CHANGE_VERSION
    assert result["comparison_status"] == "RETAINED_NATIVE_CONTENT_IDENTICAL"
    assert result["same_selected_capture"] is not recapture
    assert result["source_row_addition_count"] == result["source_row_removal_count"] == 0
    assert result["previous"]["retained_observation_count"] == 14
    assert all(row["comparison_status"] == "SAME_PERIOD_NATIVE_VALUE_IDENTICAL"
               for row in result["metric_comparisons"])
    assert result["trust_ceiling"] == "LOW" and result["availability_precision"] == "retrieval_time"
    assert result["fundamental_assessment"] == "NOT_ASSESSED"
    for key in ("source_qualified", "pit_qualified", "financial_scoring_authorized",
                "accounting_definitions_admitted", "publication_dates_verified",
                "issuer_revision_history_verified", "investment_scoring_authorized",
                "validation_authorized", "historical_replay_eligible",
                "holding_management_authorized", "execution_authorized", "research_report_created"):
        assert result[key] is False
    for side, cutoff in (("previous", AT), ("current", LATER)):
        source = _helpers()["_read"](foundation, scope, cutoff)
        assert result[side]["native_input_hash"] == source["input_hash"]
        assert result[side]["capture_freshness"] == "WITHIN_LIMIT"
    assert len(financial_input_json(result).encode()) < 18_000
    body = {key: value for key, value in result.items() if key != "digest_hash"}
    assert result["digest_hash"] == sha256(financial_input_json(body).encode()).hexdigest()
    assert pins == _footprint(foundation)
    for table in ("fundamental_facts", "research_reports", "signals"):
        assert foundation[0].table_count(table) == 0


@pytest.mark.parametrize("scope", SCOPES)
@pytest.mark.parametrize("defect,expected", (
    ("value", "SAME_PERIOD_NATIVE_VALUE_CHANGED"),
    ("negative", "SAME_PERIOD_NATIVE_VALUE_CHANGED"),
    ("zero", "SAME_PERIOD_NATIVE_VALUE_CHANGED"),
    ("representation", "SAME_PERIOD_NATIVE_REPRESENTATION_CHANGED"),
    ("advanced", "PERIOD_LABEL_ADVANCED"), ("regressed", "PERIOD_LABEL_REGRESSED"),
    ("currency", "INCOMPATIBLE_NATIVE_LABELS"), ("duplicate", "NOT_COMPARABLE"),
    ("missing", "NOT_COMPARABLE"), ("period_type", "NOT_COMPARABLE"),
    ("future", "NOT_COMPARABLE"),
))
def test_native_labels_and_value_differences_never_become_growth_or_restatement(
    foundation, scope, defect, expected,
):
    _ingest(foundation, scope)
    payload = deepcopy(_helpers()["_capture"](scope).payload)
    group = payload["timeseries"]["result"][0]
    metric = NATIVE_METRICS[0]
    latest = group[metric][-1]
    if defect in {"value", "negative", "zero", "representation"}:
        latest["reportedValue"]["raw"] = {
            "value": 1300000, "negative": -10, "zero": 0, "representation": 1200000.0}[defect]
    elif defect == "advanced":
        latest["asOfDate"] = "2026-06-30"
    elif defect == "regressed":
        group[metric].pop()
    elif defect == "currency":
        latest["currencyCode"] = "JPY"
    elif defect == "duplicate":
        group[metric].append(deepcopy(latest))
    elif defect == "missing":
        payload["timeseries"]["result"].pop(0)
    elif defect == "period_type":
        latest["periodType"] = "6M"
    else:
        latest["asOfDate"] = "2027-06-30"
    _ingest(foundation, scope, at=LATER, capture=YahooFundamentalCapture(payload))
    result = _read(foundation, scope)
    assert result["comparison_status"] == "RETAINED_NATIVE_CONTENT_DIFFERENT"
    first = result["metric_comparisons"][0]
    assert first["comparison_status"] == expected
    assert first["issuer_revision_verified"] is first["accounting_comparability_verified"] is False
    assert "amount_change" not in financial_input_json(result)
    assert all(row["comparison_status"] == "SAME_PERIOD_NATIVE_VALUE_IDENTICAL"
               for row in result["metric_comparisons"][1:])


@pytest.mark.parametrize("kind", ("history", "order"))
def test_historical_revision_is_not_hidden_by_latest_values_and_order_is_not_economic_change(
    foundation, kind,
):
    _ingest(foundation)
    payload = deepcopy(_helpers()["_capture"]().payload)
    for group in payload["timeseries"]["result"]:
        metric = group["meta"]["type"][0]
        if kind == "history":
            group[metric][0]["reportedValue"]["raw"] += 1
        else:
            group[metric].reverse()
    _ingest(foundation, at=LATER, capture=YahooFundamentalCapture(payload))
    result = _read(foundation)
    assert result["comparison_status"] == ("RETAINED_NATIVE_CONTENT_DIFFERENT" if kind == "history"
                                           else "RETAINED_NATIVE_CONTENT_IDENTICAL")
    assert result["source_row_addition_count"] == result["source_row_removal_count"] == (
        7 if kind == "history" else 0)
    assert all(row["comparison_status"] == "SAME_PERIOD_NATIVE_VALUE_IDENTICAL"
               for row in result["metric_comparisons"])


@pytest.mark.parametrize("scope", SCOPES)
@pytest.mark.parametrize("defect", (
    "missing", "failure", "ambiguous", "tampered", "stale", "empty"))
def test_latest_failure_and_unavailable_captures_never_fall_back(foundation, scope, defect):
    _ingest(foundation, scope)
    if defect in {"failure", "ambiguous"}:
        _ingest(foundation, scope, at=LATER,
                capture=YahooFundamentalCapture(None, "network_unavailable"))
    if defect in {"ambiguous", "tampered"}:
        _ingest(foundation, scope, at=LATER)
    if defect == "empty":
        _ingest(foundation, scope, at=LATER,
                capture=YahooFundamentalCapture({"timeseries": {"error": None, "result": []}}))
    if defect == "tampered":
        for path in foundation[1].root.rglob("*.bin"):
            if LATER.isoformat() in path.read_text():
                path.write_bytes(b"synthetic corruption")
    pins = _footprint(foundation)
    result = _read(foundation, scope, previous=AT - timedelta(microseconds=1) if defect == "missing"
                   else AT, current=LATER + timedelta(hours=2) if defect == "stale" else LATER)
    assert result["comparison_status"] == "NOT_COMPARABLE"
    assert result["source_series_comparison_evaluated"] is False
    assert result["source_row_addition_count"] is result["source_row_removal_count"] is None
    assert all(row["comparison_status"] == "NOT_COMPARABLE" for row in result["metric_comparisons"])
    if defect in {"failure", "ambiguous", "tampered"}:
        assert result["current"]["retained_observation_count"] is None
    assert pins == _footprint(foundation)


@pytest.mark.parametrize("age", (None, True, False, 0, -1, 1.5))
def test_capture_age_requires_explicit_positive_integer_before_read(foundation, age, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("invalid age must reject before source read")
    monkeypatch.setattr(changes, "read_native_financial_research_input", forbidden)
    with pytest.raises(ValueError, match="positive integer"):
        _read(foundation, age=age)


@pytest.mark.parametrize("previous,current", ((AT, AT), (LATER, AT),
    (AT.replace(tzinfo=None), LATER), (AT, LATER.replace(tzinfo=None))))
def test_invalid_cutoffs_do_not_read(foundation, previous, current):
    pins = _footprint(foundation)
    with pytest.raises(ValueError):
        _read(foundation, previous=previous, current=current)
    assert pins == _footprint(foundation)


@pytest.mark.parametrize("field", ("previous", "current"))
@pytest.mark.parametrize("cutoff", ("0001-01-01T00:00:00+01:00",
                                  "9999-12-31T23:59:59-01:00"))
def test_native_utc_cutoff_overflow_rejects_before_source_read(
    foundation, monkeypatch, field, cutoff,
):
    def forbidden(*args, **kwargs):
        pytest.fail("UTC cutoff overflow must reject before native source read")

    monkeypatch.setattr(changes, "read_native_financial_research_input", forbidden)
    before = _footprint(foundation)
    with pytest.raises(ValueError, match="cutoff outside UTC bounds") as error:
        _read(foundation, **{field: datetime.fromisoformat(cutoff)})
    assert error.value.__suppress_context__ and cutoff not in str(error.value)
    assert _footprint(foundation) == before


def test_equivalent_offsets_and_repeated_dst_are_actual_utc_instants(foundation):
    _ingest(foundation)
    assert _read(foundation) == _read(foundation,
        previous=AT.astimezone(ZoneInfo("Asia/Kuala_Lumpur")),
        current=LATER.astimezone(ZoneInfo("America/New_York")))
    zone = ZoneInfo("America/New_York")
    first = datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=0)
    second = first.replace(fold=1)
    _ingest(foundation, at=first.astimezone(UTC))
    result = _read(foundation, previous=first, current=second)
    assert result["current"]["capture_age_seconds"] == 3600
    with pytest.raises(ValueError, match="actual UTC"):
        _read(foundation, previous=second, current=first)


@pytest.mark.parametrize("defect", ("subject", "market", "cutoff"))
def test_bound_source_context_cannot_be_reused_for_another_request(foundation, monkeypatch, defect):
    _ingest(foundation)
    original = changes.read_native_financial_research_input

    def altered(store, artifacts, subject, market, **kwargs):
        if defect == "subject":
            subject = "AAPL"
        elif defect == "market":
            market, subject = SCOPES[1][:2]
        else:
            kwargs["as_of"] += timedelta(seconds=1)
        return original(store, artifacts, subject, market, **kwargs)

    monkeypatch.setattr(changes, "read_native_financial_research_input", altered)
    with pytest.raises(ValueError, match="context mismatch"):
        _read(foundation)


@pytest.mark.parametrize("age", (True, False, 0, -1, 1.5, "3600"))
def test_combined_age_opt_in_rejects_before_any_price_or_native_read(foundation, age):
    pins = _footprint(foundation)
    with pytest.raises(ValueError, match="positive integer"):
        read_equity_change_digest(SQLiteStore(foundation[0].path, read_only=True), foundation[1],
            "MSFT", SCOPES[0][0], previous_as_of=AT, as_of=LATER,
            maximum_age_seconds=604800, maximum_native_capture_age_seconds=age)
    assert pins == _footprint(foundation)


def test_native_reader_rejects_writable_store(foundation):
    with pytest.raises(ValueError, match="read-only existing store"):
        changes.read_native_fundamental_change_digest(*foundation, "MSFT", SCOPES[0][0],
            previous_as_of=AT, as_of=LATER, maximum_capture_age_seconds=AGE)


def test_four_source_reads_share_snapshot_and_components_do_not_mask_failures(
    foundation, monkeypatch,
):
    _ingest(foundation)
    original = changes.read_native_financial_research_input
    calls = []

    def interleaved(*args, **kwargs):
        receipt = original(*args, **kwargs)
        calls.append(1)
        if len(calls) == 1:
            _ingest(foundation, at=LATER,
                    capture=YahooFundamentalCapture(None, "network_unavailable"))
        return receipt

    kwargs = dict(previous_as_of=AT, as_of=LATER, maximum_age_seconds=604800,
                  maximum_native_capture_age_seconds=AGE, include_period_context=True)
    with monkeypatch.context() as patch:
        patch.setattr(changes, "read_native_financial_research_input", interleaved)
        result = read_equity_change_digest(SQLiteStore(foundation[0].path, read_only=True),
            foundation[1], "MSFT", SCOPES[0][0], **kwargs)
    assert len(calls) == 2 and result["comparison_status"] == "NOT_COMPARABLE"  # No price captures.
    assert result["native_fundamental_context"]["comparison_status"] == (
        "RETAINED_NATIVE_CONTENT_IDENTICAL")
    later = read_equity_change_digest(SQLiteStore(foundation[0].path, read_only=True),
        foundation[1], "MSFT", SCOPES[0][0], **kwargs)
    assert later["native_fundamental_context"]["comparison_status"] == "NOT_COMPARABLE"
    assert later["fundamental_comparison"] == "NOT_ASSESSED"


def test_price_and_native_reads_share_snapshot_across_component_boundary(foundation, monkeypatch):
    _ingest(foundation)
    prices = runpy.run_path(str(Path(__file__).with_name("test_global_price_inputs.py")))
    prices["_ingest"](foundation, scope=prices["SCOPES"][0], at=AT)
    original = equity.read_global_price_inputs
    calls = []

    def interleaved(*args, **kwargs):
        snapshot = original(*args, **kwargs)
        calls.append(snapshot.status)
        if len(calls) == 2:
            _ingest(foundation, at=LATER,
                    capture=YahooFundamentalCapture(None, "network_unavailable"))
        return snapshot

    kwargs = dict(previous_as_of=AT, as_of=LATER, maximum_age_seconds=400 * 86400,
                  maximum_native_capture_age_seconds=AGE)
    with monkeypatch.context() as patch:
        patch.setattr(equity, "read_global_price_inputs", interleaved)
        result = read_equity_change_digest(SQLiteStore(foundation[0].path, read_only=True),
            foundation[1], "MSFT", SCOPES[0][0], **kwargs)
    assert calls == ["observed_unqualified", "observed_unqualified"]
    assert result["native_fundamental_context"]["comparison_status"] == (
        "RETAINED_NATIVE_CONTENT_IDENTICAL")
    fresh = read_equity_change_digest(SQLiteStore(foundation[0].path, read_only=True),
        foundation[1], "MSFT", SCOPES[0][0], **kwargs)
    assert fresh["comparison_status"] == "NO_NEW_PRICE_OBSERVATIONS"
    assert fresh["native_fundamental_context"]["comparison_status"] == "NOT_COMPARABLE"


@pytest.mark.parametrize("microseconds,expected", ((0, "WITHIN_LIMIT"), (1, "STALE")))
def test_capture_age_boundary_is_exact_to_one_microsecond(foundation, microseconds, expected):
    _ingest(foundation)
    result = _read(foundation, current=AT + timedelta(seconds=AGE, microseconds=microseconds))
    assert result["current"]["capture_freshness"] == expected
    assert result["source_series_comparison_evaluated"] is (microseconds == 0)


def test_native_read_preserves_existing_nonempty_committed_wal(foundation):
    with sqlite3.connect(foundation[0].path) as keeper:
        keeper.execute("PRAGMA journal_mode=WAL")
        keeper.execute("PRAGMA wal_autocheckpoint=0")
        _ingest(foundation)
        assert foundation[0].path.with_name(foundation[0].path.name + "-wal").stat().st_size > 32
        pins = _footprint(foundation)
        _read(foundation)
        assert pins == _footprint(foundation)


@pytest.mark.parametrize("scope", SCOPES)
@pytest.mark.parametrize("periods", (False, True))
def test_combined_cli_is_opt_in_offline_and_preserves_old_modes(foundation, scope, periods):
    _ingest(foundation, scope)
    prices = runpy.run_path(str(Path(__file__).with_name("test_global_price_inputs.py")))
    price_scope = next(item for item in prices["SCOPES"] if item[0] is scope[0])
    prices["_ingest"](foundation, scope=price_scope, at=AT)
    args = [sys.executable, "scripts/inspect_equity_changes.py", "--database",
        str(foundation[0].path), "--artifact-root", str(foundation[1].root),
        "--market", scope[0].value,
        "--symbol", scope[1], "--previous-as-of", AT.isoformat(), "--as-of", LATER.isoformat(),
        "--max-observation-age-seconds", str(400 * 86400)]  # Synthetic older daily fixture.
    pins = _footprint(foundation)
    old = subprocess.run(args, capture_output=True, text=True)
    opts = [*args, "--max-native-capture-age-seconds", str(AGE)]
    if periods:
        opts.append("--with-period-context")
    first = subprocess.run(opts, capture_output=True, text=True)
    second = subprocess.run(opts, capture_output=True, text=True)
    assert old.returncode == first.returncode == second.returncode == 2
    assert not old.stderr + first.stderr + second.stderr
    assert "native_fundamental_context" not in json.loads(old.stdout)
    assert first.stdout == second.stdout
    result = json.loads(first.stdout)
    assert result["model_version"] == EQUITY_NATIVE_CHANGE_DIGEST_VERSION
    assert ("period_context" in result) is periods
    assert result["comparison_status"] == "NO_NEW_PRICE_OBSERVATIONS"
    assert result["fundamental_comparison"] == "NOT_ASSESSED"
    assert result["execution_authorized"] is False
    assert pins == _footprint(foundation)


@pytest.mark.parametrize("value", (("0",), ("-1",), ("1.5",), ("synthetic-private-probe",), ()))
def test_cli_invalid_native_age_is_sanitized_before_database_creation(tmp_path, value):
    database, raw = tmp_path / "absent.sqlite3", tmp_path / "absent-raw"
    args = [sys.executable, "scripts/inspect_equity_changes.py", "--database", str(database),
        "--artifact-root", str(raw), "--market", "us", "--symbol", "MSFT",
        "--previous-as-of", AT.isoformat(), "--as-of", LATER.isoformat(),
        "--max-observation-age-seconds", "604800", "--max-native-capture-age-seconds", *value]
    result = subprocess.run(args, capture_output=True, text=True)
    assert result.returncode == 2 and not result.stdout
    assert "synthetic-private-probe" not in result.stderr
    assert not database.exists() and not raw.exists()
