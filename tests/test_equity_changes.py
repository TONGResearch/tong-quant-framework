"""Synthetic retained comparisons; no verified sessions, current quotes or investment rules."""

import json
import runpy
import sqlite3
import subprocess
import sys
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from tong_quant.application import equity_changes as changes
from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.providers.yahoo_snapshot import (
    YahooGlobalSnapshotAdapter,
    YahooSnapshotCapture,
)
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.research.technical.indicators import TechnicalParameters
from tong_quant.version import EQUITY_CHANGE_DIGEST_VERSION

AT = datetime(2026, 10, 27, 10, tzinfo=UTC)
LATER = AT + timedelta(seconds=1)
AGE = 400 * 86400  # Synthetic one-year-old series; not a production freshness policy.
SCOPES = ((Market.US, "MSFT", "USD", "NMS"),
          (Market.HONG_KONG, "0700.HK", "HKD", "HKG"),
          (Market.MALAYSIA, "1155.KL", "MYR", "KLS"))


@lru_cache
def _helpers():
    return runpy.run_path(str(Path(__file__).with_name("test_global_price_inputs.py")))


@pytest.fixture
def foundation(tmp_path):
    store = SQLiteStore(tmp_path / "changes.sqlite3")
    store.initialize()
    return store, FileSystemArtifactStore(tmp_path / "raw")


def _capture(scope, *, append=False, revision=False, omit=False, count=None):
    helper = _helpers()
    capture = helper["_capture"](helper["_request"](scope))
    payload = deepcopy(capture.payload)
    result = payload["chart"]["result"][0]
    quote = result["indicators"]["quote"][0]
    if append:
        result["timestamp"].append(result["timestamp"][-1] + 86400)
        for name, values in quote.items():
            values.append(values[-1] + (0 if name == "volume" else 1))
    if revision:
        quote["close"][10] += 0.01
    if omit:
        del result["timestamp"][10]
        for values in quote.values():
            del values[10]
    if count is not None:
        result["timestamp"] = result["timestamp"][:count]
        for name in quote:
            quote[name] = quote[name][:count]
    return YahooSnapshotCapture(payload)


def _ingest(foundation, *, scope=SCOPES[0], at=AT, capture=None):
    store, artifacts = foundation
    response = _capture(scope) if capture is None else capture
    service = ProviderNeutralIngestionService(store, artifact_store=artifacts, clock=lambda: at)
    return service.ingest(
        YahooGlobalSnapshotAdapter(download=lambda _: response, clock=lambda: at),
        _helpers()["_request"](scope, at))


def _read(foundation, *, scope=SCOPES[0], previous=AT, current=LATER, age=AGE, **kwargs):
    store, artifacts = foundation
    return changes.read_equity_change_digest(SQLiteStore(store.path, read_only=True), artifacts,
        scope[1], scope[0], previous_as_of=previous, as_of=current,
        maximum_age_seconds=age, **kwargs)


def _footprint(foundation):
    store, artifacts = foundation
    paths = [store.path, *artifacts.root.rglob("*.bin")]
    wal = store.path.with_name(store.path.name + "-wal")
    result = {p: sha256(p.read_bytes()).hexdigest() for p in paths}
    # Read-only SQLite can create empty coordination sidecars, but no WAL frames.
    result[wal] = sha256(wal.read_bytes() if wal.exists() else b"").hexdigest()
    return result


@pytest.mark.parametrize("scope", SCOPES)
def test_new_price_digest_recomputes_binds_and_stays_compact_readonly(foundation, scope):
    _ingest(foundation, scope=scope)
    _ingest(foundation, scope=scope, at=LATER, capture=_capture(scope, append=True))
    before = _footprint(foundation)
    first = _read(foundation, scope=scope)
    assert financial_input_json(first) == financial_input_json(_read(foundation, scope=scope))
    assert first["model_version"] == EQUITY_CHANGE_DIGEST_VERSION
    assert first["comparison_status"] == "NEW_PRICE_OBSERVATIONS"
    assert first["new_observation_count"] == 1 and first["series_comparison_evaluated"]
    assert float(first["price_change"]["absolute"]) == 1
    assert first["price_change"]["meaning"] == "native_close_change_not_investment_or_total_return"
    assert first["previous"]["technical_binding"]["supplied_daily_row_count"] == 300
    assert first["current"]["technical_binding"]["supplied_daily_row_count"] == 301
    assert first["previous"]["price_input_hash"] != first["current"]["price_input_hash"]
    assert len(financial_input_json(first).encode()) < 12_000
    body = {k: v for k, v in first.items() if k != "digest_hash"}
    assert first["digest_hash"] == sha256(financial_input_json(body).encode()).hexdigest()
    for flag in ("execution_authorized", "source_qualified", "pit_qualified",
                 "validation_authorized", "scoring_authorized", "holding_management_authorized",
                 "historical_replay_eligible", "research_report_created"):
        assert first[flag] is False
    assert first["fundamental_comparison"] == first["multi_timeframe_comparison"] == "NOT_ASSESSED"
    assert _footprint(foundation) == before
    for table in ("fundamental_facts", "research_reports", "signals"):
        assert foundation[0].table_count(table) == 0


@pytest.mark.parametrize("scope", SCOPES)
@pytest.mark.parametrize("recapture", (False, True))
def test_same_prices_are_not_a_new_market_observation_or_business_assurance(
    foundation, scope, recapture,
):
    _ingest(foundation, scope=scope)
    if recapture:
        _ingest(foundation, scope=scope, at=LATER)
    result = _read(foundation, scope=scope)
    assert result["comparison_status"] == "NO_NEW_PRICE_OBSERVATIONS"
    assert result["same_selected_capture"] is not recapture
    assert result["new_observation_count"] == result["revised_overlap_count"] == 0
    assert result["price_change"] is None
    assert all(row["comparison"] in ("UNCHANGED", "NOT_EVALUATED")
               for row in result["technical_changes"])
    assert result["holding_method"] == "NOT_VALIDATED"


@pytest.mark.parametrize("scope", SCOPES)
@pytest.mark.parametrize("mode", ("missing", "failure", "ambiguous", "tampered", "stale"))
def test_bad_current_inputs_remain_visible_without_old_good_fallback(foundation, scope, mode):
    _ingest(foundation, scope=scope)
    current = LATER
    if mode in {"failure", "ambiguous"}:
        _ingest(foundation, scope=scope, at=LATER,
                capture=YahooSnapshotCapture(None, "provider_unavailable"))
    if mode in {"tampered", "ambiguous"}:
        _ingest(foundation, scope=scope, at=LATER, capture=_capture(scope, append=True))
    if mode == "tampered":
        files = list(foundation[1].root.rglob("*.bin"))
        for path in files:
            if len(json.loads(path.read_bytes())["decoded_payload"]["chart"]["result"][0][
                "timestamp"]) == 301:
                path.write_bytes(b"synthetic corruption")
    if mode == "stale":
        current += timedelta(days=100)
    previous = AT - timedelta(microseconds=1) if mode == "missing" else AT
    before = _footprint(foundation)
    result = _read(foundation, scope=scope, previous=previous, current=current)
    assert result["comparison_status"] == "NOT_COMPARABLE"
    assert result["blocking_reasons"] and result["technical_changes"] == []
    assert result["price_change"] is None and result["new_observation_count"] is None
    assert result["removed_observation_count"] is None
    assert not result["series_comparison_evaluated"]
    assert _footprint(foundation) == before


@pytest.mark.parametrize("scope", SCOPES)
@pytest.mark.parametrize("defect", (
    "revision", "removed", "history_added", "currency", "parameters"))
def test_source_or_parameter_changes_are_not_reported_as_price_progress(foundation, scope, defect):
    _ingest(foundation, scope=scope,
            capture=_capture(scope, omit=defect == "history_added"))
    new_scope = (*scope[:2], "EUR", scope[3]) if defect == "currency" else scope
    capture = _capture(new_scope, revision=defect == "revision", omit=defect == "removed")
    _ingest(foundation, scope=new_scope, at=LATER, capture=capture)
    kwargs = {"current_parameters": replace(TechnicalParameters(), macd_fast=10)} if (
        defect == "parameters") else {}
    result = _read(foundation, scope=scope, **kwargs)
    reason = {"revision": "overlapping_source_observations_revised",
        "removed": "historical_coverage_changed", "history_added": "historical_coverage_changed",
        "currency": "source_currency_exchange_or_price_basis_changed",
        "parameters": "technical_parameters_changed"}[defect]
    assert result["comparison_status"] == "NOT_COMPARABLE"
    assert reason in result["blocking_reasons"]
    assert result["price_change"] is None and result["technical_changes"] == []
    if defect == "revision":
        assert result["revised_overlap_count"] == 1


def test_warmup_missing_is_never_unchanged_or_a_favorable_state(foundation):
    _ingest(foundation, capture=_capture(SCOPES[0], count=5))
    result = _read(foundation, age=1000 * 86400)
    assert result["comparison_status"] == "NO_NEW_PRICE_OBSERVATIONS"
    rows = {r["field"]: r for r in result["technical_changes"]}
    assert rows["macd_histogram"]["comparison"] == "NOT_EVALUATED"
    assert rows["technical_confluence"]["comparison"] == "NOT_EVALUATED"
    assert rows["triple_average_events"]["comparison"] == "NOT_EVALUATED"
    assert rows["granville_events"]["comparison"] == "NOT_EVALUATED"
    assert result["current"]["technical_missing_inputs"]


@pytest.mark.parametrize("field,count", (("triple_average_events", 19),
                                       ("granville_events", 203)))
def test_crossing_warmup_boundary_is_not_a_comparable_event(foundation, field, count):
    _ingest(foundation, capture=_capture(SCOPES[0], count=count))
    _ingest(foundation, at=LATER, capture=_capture(SCOPES[0], count=count + 1))
    result = _read(foundation, age=1000 * 86400)
    assert result["comparison_status"] == "NEW_PRICE_OBSERVATIONS"
    row = next(row for row in result["technical_changes"] if row["field"] == field)
    assert row["comparison"] == "NOT_EVALUATED"


def test_empty_events_after_full_warmup_can_be_unchanged(foundation):
    capture = _capture(SCOPES[0])
    quote = capture.payload["chart"]["result"][0]["indicators"]["quote"][0]
    for name in ("open", "high", "low", "close"):
        quote[name] = [100] * len(quote[name])
    _ingest(foundation, capture=capture)
    result = _read(foundation)
    for field in ("triple_average_events", "granville_events"):
        row = next(row for row in result["technical_changes"] if row["field"] == field)
        assert row["previous"] == row["current"] == ""
        assert row["comparison"] == "UNCHANGED"


def test_read_preserves_existing_committed_nonempty_wal_frames(foundation):
    with sqlite3.connect(foundation[0].path) as keeper:
        keeper.execute("PRAGMA journal_mode=WAL")
        keeper.execute("PRAGMA wal_autocheckpoint=0")
        _ingest(foundation)
        wal = foundation[0].path.with_name(foundation[0].path.name + "-wal")
        assert wal.stat().st_size > 32
        before = _footprint(foundation)
        assert _read(foundation)["comparison_status"] == "NO_NEW_PRICE_OBSERVATIONS"
        assert _footprint(foundation) == before


@pytest.mark.parametrize("zone", ("Asia/Kuala_Lumpur", "America/New_York"))
def test_equivalent_cutoff_labels_preserve_the_complete_digest(foundation, zone):
    _ingest(foundation)
    expected = _read(foundation)
    actual = _read(foundation, previous=AT.astimezone(ZoneInfo(zone)),
                   current=LATER.astimezone(ZoneInfo(zone)))
    assert financial_input_json(actual) == financial_input_json(expected)


def test_repeated_dst_labels_use_utc_order_not_wall_time(foundation):
    zone = ZoneInfo("America/New_York")
    first = datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=0)
    second = first.replace(fold=1)
    _ingest(foundation, at=first.astimezone(UTC))
    result = _read(foundation, previous=first, current=second)
    assert result["previous"]["as_of"] < result["current"]["as_of"]
    with pytest.raises(ValueError, match="strictly increasing"):
        _read(foundation, previous=second, current=first)


@pytest.mark.parametrize("age", (None, True, 0, -1, 1.5))
def test_age_policy_must_be_explicit_and_positive(foundation, age):
    with pytest.raises(ValueError, match="positive observation-age"):
        _read(foundation, age=age)


@pytest.mark.parametrize("previous,current", ((AT, AT), (LATER, AT),
    (AT.replace(tzinfo=None), LATER), (AT, LATER.replace(tzinfo=None))))
def test_invalid_cutoffs_reject_before_read(foundation, previous, current):
    before = _footprint(foundation)
    with pytest.raises(ValueError):
        _read(foundation, previous=previous, current=current)
    assert _footprint(foundation) == before


@pytest.mark.parametrize("field", ("previous", "current"))
@pytest.mark.parametrize("cutoff", ("0001-01-01T00:00:00+01:00",
                                  "9999-12-31T23:59:59-01:00"))
def test_utc_cutoff_overflow_is_sanitized_before_source_read(
    foundation, monkeypatch, field, cutoff,
):
    def forbidden(*args, **kwargs):
        pytest.fail("UTC cutoff overflow must reject before source read")

    monkeypatch.setattr(changes, "read_global_price_inputs", forbidden)
    before = _footprint(foundation)
    with pytest.raises(ValueError, match="cutoff outside UTC bounds") as error:
        _read(foundation, **{field: datetime.fromisoformat(cutoff)})
    assert error.value.__suppress_context__ and cutoff not in str(error.value)
    assert _footprint(foundation) == before


@pytest.mark.parametrize("defect", ("subject", "market", "cutoff"))
def test_reader_result_cannot_be_rebound_to_another_requested_context(
    foundation, monkeypatch, defect,
):
    _ingest(foundation)
    original = changes.read_global_price_inputs

    def altered(*args, **kwargs):
        source = original(*args, **kwargs)
        return replace(source, **{"subject": {"subject": "NVDA"},
            "market": {"market": Market.MALAYSIA},
            "cutoff": {"as_of": source.as_of + timedelta(seconds=1)}}[defect])

    monkeypatch.setattr(changes, "read_global_price_inputs", altered)
    with pytest.raises(ValueError, match="snapshot identity or cutoff"):
        _read(foundation)


def test_two_cutoffs_share_a_database_snapshot_despite_an_independent_writer(
    foundation, monkeypatch,
):
    _ingest(foundation)
    original = changes.read_global_price_inputs
    calls = []

    def interleaved(*args, **kwargs):
        source = original(*args, **kwargs)
        calls.append(1)
        if len(calls) == 1:
            _ingest(foundation, at=LATER,
                    capture=YahooSnapshotCapture(None, "provider_unavailable"))
        return source

    with monkeypatch.context() as patch:
        patch.setattr(changes, "read_global_price_inputs", interleaved)
        first = _read(foundation)
    assert first["comparison_status"] == "NO_NEW_PRICE_OBSERVATIONS"
    assert first["same_selected_capture"] is True
    assert _read(foundation)["comparison_status"] == "NOT_COMPARABLE"


def _cli(foundation):
    return [sys.executable, "scripts/inspect_equity_changes.py", "--database",
        str(foundation[0].path), "--artifact-root", str(foundation[1].root), "--market", "us",
        "--symbol", "MSFT", "--previous-as-of", AT.isoformat(), "--as-of", LATER.isoformat(),
        "--max-observation-age-seconds", str(AGE)]


def test_cli_is_offline_repeatable_and_does_not_create_official_artifacts(foundation):
    _ingest(foundation)
    before = _footprint(foundation)
    first = subprocess.run(_cli(foundation), capture_output=True, text=True)
    second = subprocess.run(_cli(foundation), capture_output=True, text=True)
    assert first.returncode == second.returncode == 2 and not first.stderr
    assert first.stdout == second.stdout
    assert json.loads(first.stdout)["comparison_status"] == "NO_NEW_PRICE_OBSERVATIONS"
    assert _footprint(foundation) == before


@pytest.mark.parametrize("extra", (("--capture",), ("--secret", "synthetic-probe"),
    ("--market", "china_a"), ("--as-of", AT.isoformat())))
def test_cli_rejects_unsupported_inputs_without_creating_database(tmp_path, extra):
    store = SQLiteStore(tmp_path / "absent.sqlite3")
    artifacts = FileSystemArtifactStore(tmp_path / "absent-raw")
    result = subprocess.run([*_cli((store, artifacts)), *extra], capture_output=True, text=True)
    assert result.returncode == 2 and not result.stdout
    assert "synthetic-probe" not in result.stderr
    assert not store.path.exists() and not artifacts.root.exists()


@pytest.mark.parametrize("flag", ("--previous-as-of", "--as-of"))
@pytest.mark.parametrize("cutoff", ("0001-01-01T00:00:00+01:00",
                                  "9999-12-31T23:59:59-01:00"))
@pytest.mark.parametrize("periods", (False, True))
@pytest.mark.parametrize("native", (False, True))
def test_cli_utc_overflow_is_a_sanitized_error_in_every_mode(
    foundation, flag, cutoff, periods, native,
):
    args = _cli(foundation)
    args[args.index(flag) + 1] = cutoff
    if periods:
        args.append("--with-period-context")
    if native:
        args.extend(("--max-native-capture-age-seconds", "3600"))
    before = _footprint(foundation)
    result = subprocess.run(args, capture_output=True, text=True)
    assert result.returncode == 2 and not result.stdout
    assert result.stderr == "Read-only change inputs could not be verified.\n"
    assert _footprint(foundation) == before
