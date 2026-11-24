"""Calendar-ended comparison is descriptive, never independent trading evidence."""

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
from tong_quant.research.technical.indicators import TechnicalParameters
from tong_quant.research.technical.long_horizon import (
    LongHorizonParameters,
    long_horizon_diagnostics,
)
from tong_quant.version import EQUITY_CHANGE_DIGEST_VERSION, EQUITY_PERIOD_CHANGE_DIGEST_VERSION

AT = datetime(2026, 10, 27, 10, tzinfo=UTC)
LATER = AT + timedelta(seconds=1)
AGE = 400 * 86400  # Synthetic test admission only, not a production age policy.


@lru_cache
def _helpers():
    return runpy.run_path(str(Path(__file__).with_name("test_equity_changes.py")))


SCOPES = _helpers()["SCOPES"]
# Frozen pre-period v1 source SHA256:
# 9f0375ef62d1ba7a6e0668e22f95e598bd134bbdab0e88aa6913d9a0425e6f92.
_V1_HASHES = {
    "us": ("0fdb413ddac166e572fa5b601bb79132211b9b29c2cd16444e250912cf010cdf",
           "54f71d1668ca6c0ee89a902c3def7b9ac2976099082993c003b729de12dfc0b4"),
    "hong_kong": ("126e8c48f88b3497be01b7dfad1d7f61366710d3503ab665a3eed1be2ba25e62",
                 "ca71fbefb4f9ab918e912de571cb97cd82e22ac6830aaf9e5847510d0678871f"),
    "malaysia": ("ad5f80e1d6b33ccc5cb3e114371666b3265c2059e76fdb8fc2750df547c50b65",
                 "69edccd7de2fe2575e2f075230afc747b21cef162d215eeede55bbecb3a730b2"),
}


@pytest.fixture
def foundation(tmp_path):
    store = SQLiteStore(tmp_path / "periods.sqlite3")
    store.initialize()
    return store, FileSystemArtifactStore(tmp_path / "raw")


def _capture(scope, *, start=datetime(2023, 1, 1, 15, tzinfo=UTC),
             end=datetime(2026, 10, 26, 15, tzinfo=UTC), gap=False, revision=False):
    capture = _helpers()["_capture"](scope)
    result = deepcopy(capture.payload)["chart"]["result"][0]
    stamps = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    stamps = [at for at in stamps if not gap or (at.year, at.month) != (2024, 5)]
    result["timestamp"] = [int(at.timestamp()) for at in stamps]
    result["indicators"]["quote"] = [{
        name: [base + i / 100 for i in range(len(stamps))]
        for name, base in (("open", 100), ("high", 101), ("low", 99), ("close", 100.5))}]
    result["indicators"]["quote"][0]["volume"] = [10000] * len(stamps)
    result["indicators"]["adjclose"] = [{"adjclose": [999] * len(stamps)}]
    if revision:
        result["indicators"]["quote"][0]["close"][10] += 0.01
    return YahooSnapshotCapture({"chart": {"error": None, "result": [result]}})


def _ingest(foundation, scope=SCOPES[0], *, at=AT, capture=None):
    helper = _helpers()
    request = helper["_helpers"]()["_request"](scope, at)
    request = replace(request, parameters={**request.parameters, "start_date": "2023-01-01"})
    service = ProviderNeutralIngestionService(foundation[0], artifact_store=foundation[1],
                                            clock=lambda: at)
    return service.ingest(YahooGlobalSnapshotAdapter(
        download=lambda _: capture or _capture(scope), clock=lambda: at), request)


def _read(foundation, scope=SCOPES[0], *, previous=AT, current=LATER, **kwargs):
    return changes.read_equity_change_digest(SQLiteStore(foundation[0].path, read_only=True),
        foundation[1], scope[1], scope[0], previous_as_of=previous, as_of=current,
        maximum_age_seconds=AGE, **kwargs)


def _rows(result):
    return {row["frequency"]: row for row in result["period_context"]["comparisons"]}


@pytest.mark.parametrize("scope", SCOPES)
def test_opt_in_is_deterministic_bound_compact_and_does_not_mutate_default(foundation, scope):
    _ingest(foundation, scope)
    baseline = _read(foundation, scope)
    assert sha256(financial_input_json(baseline).encode()).hexdigest() == _V1_HASHES[
        scope[0].value][0]
    before = _helpers()["_footprint"](foundation)
    result = _read(foundation, scope, include_period_context=True)
    assert result == _read(foundation, scope, include_period_context=True)
    assert baseline == _read(foundation, scope, include_period_context=False)
    assert baseline["model_version"] == EQUITY_CHANGE_DIGEST_VERSION
    assert "period_context" not in baseline
    assert result["model_version"] == EQUITY_PERIOD_CHANGE_DIGEST_VERSION
    stripped = {key: value for key, value in result.items()
                if key not in {"period_context", "digest_hash", "model_version",
                               "multi_timeframe_comparison"}}
    assert stripped == {key: value for key, value in baseline.items() if key not in {
        "digest_hash", "model_version", "multi_timeframe_comparison"}}
    context = result["period_context"]
    assert context["calendar_end_is_exchange_close"] is False
    assert context["cross_timeframe_decision"] == "NOT_EVALUATED"
    assert result["fundamental_comparison"] == "NOT_ASSESSED"
    for key in ("source_qualified", "pit_qualified", "holding_management_authorized",
                "execution_authorized", "calendar_verified"):
        assert context[key] is False
    for row in _rows(result).values():
        assert row["comparison_status"] == "SAME_ENDED_PERIOD"
        assert row["new_calendar_ended_period_count"] == 0
        assert all(item["comparison"] == "UNCHANGED" for item in row["indicator_changes"])
    for name, cutoff in (("previous", AT), ("current", LATER)):
        with SQLiteStore(foundation[0].path, read_only=True).read_snapshot() as store:
            original = changes.read_global_price_inputs(store, foundation[1], scope[1], scope[0],
                as_of=cutoff, maximum_age_seconds=AGE)
        expected = long_horizon_diagnostics(original.bars, market=scope[0], as_of=cutoff,
            parameters=LongHorizonParameters(), weekly_sma_periods=(13, 26, 52))
        assert context[name]["diagnostics_input_hash"] == expected["input_hash"]
        assert context[name]["source_bars_content_hash"] == expected["source_bars_content_hash"]
        for frequency in ("weekly", "monthly"):
            summary = context[name]["frequencies"][frequency]
            assert summary["macd"] == expected[frequency]["macd"]
            assert summary["last_ended_close"] == expected[frequency]["last_ended_close"]
    assert len(financial_input_json(result).encode()) < 30_000
    assert _helpers()["_footprint"](foundation) == before
    body = {key: value for key, value in result.items() if key != "digest_hash"}
    assert result["digest_hash"] == sha256(financial_input_json(body).encode()).hexdigest()


@pytest.mark.parametrize("scope", SCOPES)
@pytest.mark.parametrize("frequency,day", (("weekly", 2), ("monthly", 1)))
def test_exact_local_rollover_without_new_prices_is_not_aligned_change(foundation, scope,
                                                                    frequency, day):
    _ingest(foundation, scope)
    zone = ZoneInfo({"us": "America/New_York", "hong_kong": "Asia/Hong_Kong",
                     "malaysia": "Asia/Kuala_Lumpur"}[scope[0].value])
    boundary = datetime(2026, 11, day, tzinfo=zone).astimezone(UTC)
    result = _read(foundation, scope, previous=boundary - timedelta(microseconds=1),
                   current=boundary, include_period_context=True)
    assert result["comparison_status"] == "NO_NEW_PRICE_OBSERVATIONS"
    assert result["same_selected_capture"] and result["price_change"] is None
    rows = _rows(result)
    assert rows[frequency]["comparison_status"] == "PERIOD_END_ADVANCED"
    assert rows[frequency]["new_calendar_ended_period_count"] == 1
    assert all(row["comparison"] == "NOT_ALIGNED" for row in rows[frequency]["indicator_changes"])
    other = "monthly" if frequency == "weekly" else "weekly"
    assert rows[other]["comparison_status"] == "SAME_ENDED_PERIOD"
    latest = result["period_context"]["current"]["frequencies"][frequency]
    assert latest["latest_period_alignment"]["calendar_end_at"] == boundary
    if scope[0].value == "us" and frequency == "weekly":
        old = result["period_context"]["previous"]["frequencies"][frequency]
        assert (boundary - old["latest_period_alignment"]["calendar_end_at"]).total_seconds() == (
            169 * 3600)  # DST fallback: use local calendar boundaries, not a fixed UTC week.


@pytest.mark.parametrize("scope", SCOPES)
def test_new_open_period_observation_does_not_change_ended_indicators(foundation, scope):
    _ingest(foundation, scope, capture=_capture(scope, end=datetime(2026, 10, 25, 15, tzinfo=UTC)))
    _ingest(foundation, scope, at=LATER)
    result = _read(foundation, scope, include_period_context=True)
    assert result["comparison_status"] == "NEW_PRICE_OBSERVATIONS"
    for row in _rows(result).values():
        assert row["comparison_status"] == "SAME_ENDED_PERIOD"
        assert all(item["comparison"] == "UNCHANGED" for item in row["indicator_changes"])


@pytest.mark.parametrize("defect", ("failure", "missing", "revision", "parameters", "currency",
                                  "stale", "ambiguous", "tampered"))
def test_parent_blockers_prevent_favorable_period_comparison(foundation, defect):
    _ingest(foundation)
    if defect in {"failure", "ambiguous"}:
        _ingest(foundation, at=LATER, capture=YahooSnapshotCapture(None, "provider_unavailable"))
    elif defect in {"revision", "currency"}:
        scope = (*SCOPES[0][:2], "EUR", SCOPES[0][3]) if defect == "currency" else SCOPES[0]
        _ingest(foundation, scope, at=LATER, capture=_capture(scope, revision=defect == "revision"))
    if defect in {"ambiguous", "tampered"}:
        result = _ingest(foundation, at=LATER)
        if defect == "tampered":
            for path in foundation[1].root.rglob("*.bin"):
                if LATER.isoformat() in path.read_text():
                    path.write_bytes(b"synthetic corruption")
            assert result is not None
    kwargs = {"current_parameters": replace(TechnicalParameters(), macd_fast=10)} if (
        defect == "parameters") else {}
    result = _read(foundation, previous=AT - timedelta(microseconds=1) if defect == "missing"
                   else AT, current=LATER + timedelta(days=500) if defect == "stale" else LATER,
                   include_period_context=True, **kwargs)
    assert result["comparison_status"] == "NOT_COMPARABLE"
    for row in _rows(result).values():
        assert row["comparison_status"] == "NOT_COMPARABLE"
        assert row["new_calendar_ended_period_count"] is None
        assert row["same_ended_period"] is None and row["indicator_changes"] == []
        assert set(result["blocking_reasons"]).issubset(row["blocking_reasons"])
    if defect in {"failure", "stale", "ambiguous", "tampered"}:
        for frame in result["period_context"]["current"]["frequencies"].values():
            assert frame["period_inventory_evaluated"] is False
            assert frame["ended_period_count"] is None and frame["open_period_starts"] is None


def test_missing_historical_month_blocks_without_stitching_or_last_good_fallback(foundation):
    _ingest(foundation, capture=_capture(SCOPES[0], gap=True))
    result = _read(foundation, include_period_context=True)
    assert result["comparison_status"] == "NO_NEW_PRICE_OBSERVATIONS"
    for row in _rows(result).values():
        assert row["comparison_status"] == "NOT_COMPARABLE" and row["indicator_changes"] == []
    for frequency in ("weekly", "monthly"):
        summary = result["period_context"]["current"]["frequencies"][frequency]
        assert summary["blocking_period_count"] > 0
        assert summary["calculation_period_count"] == 0 and summary["last_ended_close"] is None


def test_latest_suspension_with_retained_rows_is_not_an_evaluated_zero_inventory(
    foundation, monkeypatch,
):
    _ingest(foundation)
    original = changes.read_global_price_inputs

    def suspended(*args, **kwargs):
        snapshot = original(*args, **kwargs)
        return replace(snapshot, bars=(*snapshot.bars[:-1],
            replace(snapshot.bars[-1], is_suspended=True)))

    monkeypatch.setattr(changes, "read_global_price_inputs", suspended)
    result = _read(foundation, include_period_context=True)
    for side in ("previous", "current"):
        assert result["period_context"][side]["supplied_daily_row_count"] > 0
        for frame in result["period_context"][side]["frequencies"].values():
            assert frame["status"] == "SUSPENDED_LATEST"
            assert frame["period_inventory_evaluated"] is False
            assert frame["ended_period_count"] is frame["calculation_period_count"] is None
            assert frame["blocking_period_count"] is frame["open_period_starts"] is None
    for row in _rows(result).values():
        assert row["comparison_status"] == "NOT_COMPARABLE" and row["indicator_changes"] == []


@pytest.mark.parametrize("start", (datetime(2026, 10, 26, 15, tzinfo=UTC),
                                   datetime(2026, 9, 1, 15, tzinfo=UTC)))
def test_no_ended_period_or_insufficient_warmup_is_not_unchanged(foundation, start):
    _ingest(foundation, capture=_capture(SCOPES[0], start=start))
    result = _read(foundation, include_period_context=True)
    for row in _rows(result).values():
        if row["comparison_status"] == "NOT_COMPARABLE":
            assert row["indicator_changes"] == []
        else:
            assert all(item["comparison"] == "NOT_EVALUATED" for item in row["indicator_changes"])


@pytest.mark.parametrize("opt_in", (1, None, "yes", (), {}))
def test_period_opt_in_is_strict_before_read(foundation, opt_in, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("invalid opt-in must reject before reading")
    monkeypatch.setattr(changes, "read_global_price_inputs", forbidden)
    with pytest.raises(ValueError, match="opt-in must be boolean"):
        _read(foundation, include_period_context=opt_in)


def test_equivalent_cutoff_labels_preserve_period_context(foundation):
    _ingest(foundation)
    baseline = _read(foundation, include_period_context=True)
    actual = _read(foundation, previous=AT.astimezone(ZoneInfo("America/New_York")),
                   current=LATER.astimezone(ZoneInfo("Asia/Kuala_Lumpur")),
                   include_period_context=True)
    assert baseline == actual


def test_opt_in_reuses_one_snapshot_despite_an_independent_writer(foundation, monkeypatch):
    _ingest(foundation)
    original = changes.read_global_price_inputs
    calls = []

    def interleaved(*args, **kwargs):
        snapshot = original(*args, **kwargs)
        calls.append(snapshot.selected_evidence_id)
        if len(calls) == 1:
            _ingest(foundation, at=LATER,
                    capture=YahooSnapshotCapture(None, "provider_unavailable"))
        return snapshot

    with monkeypatch.context() as patch:
        patch.setattr(changes, "read_global_price_inputs", interleaved)
        result = _read(foundation, include_period_context=True)
    assert len(calls) == 2 and calls[0] == calls[1]
    assert all(row["comparison_status"] == "SAME_ENDED_PERIOD" for row in _rows(result).values())
    later = _read(foundation, include_period_context=True)
    assert all(row["comparison_status"] == "NOT_COMPARABLE" for row in _rows(later).values())


def test_period_read_preserves_existing_nonempty_committed_wal(foundation):
    with sqlite3.connect(foundation[0].path) as keeper:
        keeper.execute("PRAGMA journal_mode=WAL")
        keeper.execute("PRAGMA wal_autocheckpoint=0")
        _ingest(foundation)
        wal = foundation[0].path.with_name(foundation[0].path.name + "-wal")
        assert wal.stat().st_size > 32
        before = _helpers()["_footprint"](foundation)
        _read(foundation, include_period_context=True)
        assert _helpers()["_footprint"](foundation) == before


@pytest.mark.parametrize("scope", SCOPES)
def test_period_cli_stays_offline_opt_in_repeatable_and_unqualified(foundation, scope):
    _ingest(foundation, scope)
    args = [sys.executable, "scripts/inspect_equity_changes.py", "--database",
        str(foundation[0].path), "--artifact-root", str(foundation[1].root),
        "--market", scope[0].value,
        "--symbol", scope[1], "--previous-as-of", AT.isoformat(), "--as-of", LATER.isoformat(),
        "--max-observation-age-seconds", str(AGE)]
    before = _helpers()["_footprint"](foundation)
    plain = subprocess.run(args, capture_output=True, text=True)
    first = subprocess.run([*args, "--with-period-context"], capture_output=True, text=True)
    second = subprocess.run([*args, "--with-period-context"], capture_output=True, text=True)
    assert plain.returncode == first.returncode == second.returncode == 2
    assert not plain.stderr + first.stderr + second.stderr
    assert "period_context" not in json.loads(plain.stdout)
    assert sha256(plain.stdout.encode()).hexdigest() == _V1_HASHES[scope[0].value][1]
    assert first.stdout == second.stdout
    assert json.loads(first.stdout)["model_version"] == EQUITY_PERIOD_CHANGE_DIGEST_VERSION
    assert _helpers()["_footprint"](foundation) == before
