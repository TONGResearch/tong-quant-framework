"""Synthetic global captures exercise plumbing, never market-data qualification."""

import json
import runpy
import subprocess
import sys
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from zoneinfo import ZoneInfo

import pytest

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.global_price_inputs import read_global_price_inputs
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.providers import yahoo
from tong_quant.data.providers.contracts import ProviderDatasetRequest
from tong_quant.data.providers.yahoo import YahooChartHttpClient
from tong_quant.data.providers.yahoo_snapshot import (
    DATASET,
    MAX_BYTES,
    TIMEZONES,
    YahooGlobalSnapshotAdapter,
    YahooSnapshotCapture,
    snapshot_prices,
    validate_snapshot_request,
)
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.domain.models import TradingSession
from tong_quant.research.technical.diagnostics import technical_diagnostics
from tong_quant.research.technical.indicators import TechnicalParameters

NOW = datetime(2026, 10, 27, 9, tzinfo=UTC)
SCOPES = [(Market.US, "MSFT", "USD", "NMS"),
          (Market.HONG_KONG, "0700.HK", "HKD", "HKG"),
          (Market.MALAYSIA, "1155.KL", "MYR", "KLS")]


def _holding_file(path, scope=SCOPES[0]):
    path.write_text(f'''[holding]
symbol = "{scope[1]}"
market = "{scope[0].value}"
currency = "{scope[2]}"
quantity = "0.1"
reported_average_cost = "10"
observed_at = "{(NOW - timedelta(hours=1)).isoformat()}"
recorded_at = "{NOW.isoformat()}"
investment_intent = "long_term"
loss_review_percent = "30"
maximum_context_age_seconds = 604800
maximum_price_age_seconds = 604800
''')
    return path


@pytest.mark.parametrize("scope", SCOPES)
def test_holding_cli_is_opt_in_offline_and_keeps_old_inputs(foundation, tmp_path, scope):
    _ingest(foundation, scope=scope)
    store, artifacts = foundation
    path = _holding_file(tmp_path / "holding.toml", scope)
    args = [sys.executable, "scripts/inspect_global_technical.py", "--market", scope[0].value,
        "--symbol", scope[1], "--database", str(store.path), "--artifact-root", str(artifacts.root),
        "--as-of", NOW.isoformat()]
    before = sha256(store.path.read_bytes()).hexdigest()
    baseline = subprocess.run(args, capture_output=True, text=True)
    first = subprocess.run([*args, "--holding-context", str(path)], capture_output=True, text=True)
    second = subprocess.run([*args, "--holding-context", str(path)], capture_output=True, text=True)
    markdown = subprocess.run([*args, "--holding-context", str(path), "--format", "markdown"],
                              capture_output=True, text=True)
    after = subprocess.run(args, capture_output=True, text=True)
    assert baseline.returncode == first.returncode == second.returncode == markdown.returncode == 2
    assert first.stdout == second.stdout and baseline.stdout == after.stdout
    original, extended = json.loads(baseline.stdout), json.loads(first.stdout)
    review = extended.pop("holding_review")
    assert original == extended and "holding_review" not in original
    assert review["comparison_status"] == "BLOCKED"
    assert "PRICE_PREDATES_HOLDING_OBSERVATION" in review["blockers"]
    assert review["price_only_change_percent"] is None
    assert "NOT_ESTIMATED" in markdown.stdout
    assert before == sha256(store.path.read_bytes()).hexdigest()


@pytest.mark.parametrize("kind", ["capture", "mismatch", "malformed", "secret", "symlink"])
def test_holding_cli_rejects_bad_input_before_creating_a_database(tmp_path, kind):
    path = _holding_file(tmp_path / "holding.toml")
    extra = []
    if kind == "capture":
        extra = ["--capture"]
    elif kind == "mismatch":
        path.write_text(path.read_text().replace('symbol = "MSFT"', 'symbol = "OTHER"'))
    elif kind == "malformed":
        path.write_text("not valid TOML")
    elif kind == "secret":
        path.write_text(path.read_text() + 'api_key = ""\n')
    else:
        link = tmp_path / "link.toml"
        link.symlink_to(path)
        path = link
    database = tmp_path / "absent.sqlite3"
    result = subprocess.run([sys.executable, "scripts/inspect_global_technical.py",
        "--market", "us",
        "--symbol", "MSFT", "--database", str(database), "--artifact-root", str(tmp_path / "raw"),
        "--holding-context", str(path), *extra], capture_output=True, text=True)
    assert result.returncode == 2 and result.stdout == ""
    assert not database.exists()


def _request(scope=SCOPES[0], at=NOW):
    market, subject, currency, exchange = scope
    return ProviderDatasetRequest(DATASET, market, subject, at, {
        "start_date": "2025-01-01", "end_date": "2026-10-26",
        "currency": currency, "exchange": exchange, "timezone": TIMEZONES[market]})


def _capture(request=None):
    request = request or _request()
    start = datetime(2025, 1, 1, 15, tzinfo=UTC)
    stamps = [int((start + timedelta(days=index)).timestamp()) for index in range(300)]
    return YahooSnapshotCapture({"chart": {"error": None, "result": [{
        "meta": {"symbol": request.subject, "currency": request.parameters["currency"],
            "exchangeName": request.parameters["exchange"], "instrumentType": "EQUITY",
            "exchangeTimezoneName": request.parameters["timezone"], "dataGranularity": "1d"},
        "timestamp": stamps,
        "indicators": {"quote": [{"open": [10 + index / 100 for index in range(300)],
            "high": [11 + index / 100 for index in range(300)],
            "low": [9 + index / 100 for index in range(300)],
            "close": [10.5 + index / 100 for index in range(300)],
            "volume": [10000] * 300}], "adjclose": [{"adjclose": [999] * 300}]},
    }]}})


@pytest.fixture
def foundation(tmp_path):
    store = SQLiteStore(tmp_path / "global.sqlite3")
    store.initialize()
    return store, FileSystemArtifactStore(tmp_path / "artifacts")


def _ingest(foundation, capture=None, scope=SCOPES[0], at=NOW, completed=None):
    store, artifacts = foundation
    request = _request(scope, at)
    return ProviderNeutralIngestionService(store, artifact_store=artifacts,
        clock=lambda: completed or at).ingest(YahooGlobalSnapshotAdapter(
            download=lambda _: capture or _capture(request), clock=lambda: at), request)


def _read(foundation, scope=SCOPES[0], at=NOW, **kwargs):
    store, artifacts = foundation
    return read_global_price_inputs(store, artifacts, scope[1], scope[0], as_of=at, **kwargs)


@pytest.mark.parametrize("scope", SCOPES)
def test_global_series_reconstructs_retained_bytes_and_drives_technicals(foundation, scope):
    _ingest(foundation, scope=scope)
    before = sha256(foundation[0].path.read_bytes()).hexdigest()
    result = _read(foundation, scope)
    assert result.status == "observed_unqualified" and len(result.bars) == 300
    assert result.bars[0].instrument.currency == scope[2]
    assert result.bars[0].instrument.exchange == scope[3]
    assert result.bars[-1].available_at == NOW
    assert result.bars[-1].close != 999
    diagnostics = technical_diagnostics(result.bars, TechnicalParameters(), as_of=NOW)
    assert diagnostics["macd_dif"] is not None and diagnostics["kdj_k"] is not None
    assert diagnostics["technical_scoring_admitted"] is False
    document = result.document()
    assert document["price_basis"] == "PROVIDER_NATIVE_UNVERIFIED"
    for name in ("investment_scoring_authorized", "historical_replay_eligible",
                 "validation_authorized", "execution_authorized", "research_report_created"):
        assert document[name] is False
    assert _read(foundation, scope).document() == document
    assert _read(foundation, scope, at=NOW - timedelta(microseconds=1)).status == "missing"
    assert sha256(foundation[0].path.read_bytes()).hexdigest() == before
    for table in ("daily_bars", "instruments", "research_reports", "signals"):
        assert foundation[0].table_count(table) == 0


def test_snapshot_idempotency_and_actual_utc_identity(foundation):
    _ingest(foundation)
    _ingest(foundation)
    assert foundation[0].table_count("provider_evidence_records") == 1
    assert foundation[0].table_count("provider_artifacts") == 1
    local = NOW.astimezone(ZoneInfo("Asia/Kuala_Lumpur"))
    assert _read(foundation, at=local).document()["input_hash"] == (
        _read(foundation).document()["input_hash"])


def test_input_hash_binds_actual_reconstructed_bar_values_not_just_source_ids(foundation):
    _ingest(foundation)
    result = _read(foundation)
    changed = replace(result, bars=(*result.bars[:-1],
                                  replace(result.bars[-1], close=Decimal("13.48"))))
    assert changed.selected_evidence_id == result.selected_evidence_id
    assert changed.document()["bars_content_hash"] != result.document()["bars_content_hash"]
    assert changed.document()["input_hash"] != result.document()["input_hash"]


@pytest.mark.parametrize("field,value", [("symbol", "OTHER"), ("currency", "CNY"),
    ("exchangeName", "OTHER"), ("exchangeTimezoneName", "UTC"),
    ("instrumentType", "ETF"), ("dataGranularity", "1m")])
def test_native_identity_and_scope_mismatch_are_retained_but_unusable(foundation, field, value):
    payload = deepcopy(_capture().payload)
    payload["chart"]["result"][0]["meta"][field] = value
    _ingest(foundation, YahooSnapshotCapture(payload))
    result = _read(foundation)
    assert result.status == "invalid_response" and not result.bars
    assert len(result.observations) == 1


@pytest.mark.parametrize("kind", ["missing", "boolean", "zero", "negative_volume", "fractional",
    "duplicate", "reverse", "future", "length", "intraday", "outside_range", "ohlc"])
def test_any_invalid_row_blocks_whole_series_without_favorable_fallback(kind):
    payload = deepcopy(_capture().payload)
    result = payload["chart"]["result"][0]
    quote = result["indicators"]["quote"][0]
    if kind in {"missing", "boolean", "zero"}:
        quote["close"][-1] = {"missing": None, "boolean": True, "zero": 0}[kind]
    elif kind in {"negative_volume", "fractional"}:
        quote["volume"][-1] = -1 if kind == "negative_volume" else 1.5
    elif kind == "duplicate":
        result["timestamp"][-1] = result["timestamp"][-2]
    elif kind == "reverse":
        result["timestamp"].reverse()
    elif kind == "future":
        result["timestamp"][-1] = int((NOW + timedelta(days=1)).timestamp())
    elif kind == "length":
        quote["high"].pop()
    elif kind == "intraday":
        result["timestamp"][1] = result["timestamp"][0] + 60
    elif kind == "outside_range":
        result["timestamp"][0] = int(datetime(2024, 1, 1, tzinfo=UTC).timestamp())
    else:
        quote["high"][-1] = 1
    assert snapshot_prices(YahooSnapshotCapture(payload), _request(), NOW) == (
        "invalid_response", ())


def test_current_session_is_not_assumed_complete():
    payload = deepcopy(_capture().payload)
    payload["chart"]["result"][0]["timestamp"][-1] = int(NOW.timestamp())
    request = _request()
    request.parameters["end_date"] = "2026-10-27"
    assert snapshot_prices(YahooSnapshotCapture(payload), request, NOW) == (
        "current_session_completion_unverified", ())


def test_us_completion_check_uses_exchange_date_not_utc_date():
    payload = deepcopy(_capture().payload)
    captured = datetime(2026, 10, 27, 3, tzinfo=UTC)
    payload["chart"]["result"][0]["timestamp"][-1] = int(
        datetime(2026, 10, 26, 13, 30, tzinfo=UTC).timestamp())
    assert snapshot_prices(YahooSnapshotCapture(payload), _request(at=captured), captured) == (
        "current_session_completion_unverified", ())


@pytest.mark.parametrize("key", ["token", "api_key", "secret", "password", "webhook_url"])
def test_secrets_are_rejected_before_artifact_persistence(key):
    with pytest.raises(ValueError, match="credential"):
        YahooSnapshotCapture({key: "synthetic fixture only"})


@pytest.mark.parametrize("payload", [{"data": "x" * MAX_BYTES}, {"x": float("nan")},
                                    {"x": float("inf")}, []])
def test_oversized_nonfinite_or_nonobject_capture_is_rejected(payload):
    with pytest.raises(ValueError):
        YahooSnapshotCapture(payload)


@pytest.mark.parametrize("failure", ["provider_unavailable", "invalid_decoded_response"])
def test_latest_provider_failure_does_not_select_earlier_good_series(foundation, failure):
    _ingest(foundation)
    at = NOW + timedelta(seconds=1)
    _ingest(foundation, YahooSnapshotCapture(None, failure), at=at)
    result = _read(foundation, at=at)
    assert result.status == failure and not result.bars and len(result.observations) == 2
    _ingest(foundation, at=at)
    assert _read(foundation, at=at).status == "rejected_or_ambiguous"


@pytest.mark.parametrize("kind", ["bytes", "payload", "registry", "batch_time", "batch_hash",
                                  "batch_parameters", "batch_status"])
def test_binding_rejects_tampering_and_future_completion(foundation, kind):
    result = _ingest(foundation)
    store, artifacts = foundation
    record = _read(foundation).observations[0]
    digest = record["raw_data_hash"]
    with store._connect() as connection:
        if kind == "payload":
            connection.execute("UPDATE provider_evidence_records SET payload_json='{}'")
        elif kind == "registry":
            connection.execute("UPDATE provider_artifacts SET source_identity='synthetic tamper'")
        elif kind.startswith("batch_"):
            column, value = {
                "batch_time": ("completed_at", (NOW + timedelta(seconds=1)).isoformat()),
                "batch_hash": ("raw_response_hash", "f" * 64),
                "batch_parameters": ("parameters_json", "{}"),
                "batch_status": ("status", "failed"),
            }[kind]
            connection.execute(f"UPDATE ingestion_batches SET {column}=? WHERE batch_id=?",
                               (value, result.batch_id))
    if kind == "bytes":
        (artifacts.root / "sha256" / digest[:2] / f"{digest}.bin").write_bytes(b"synthetic tamper")
    assert _read(foundation).status == "rejected_or_ambiguous"
    assert not _read(foundation).bars


def test_snapshot_requires_completed_batch_and_explicit_observation_freshness(foundation):
    _ingest(foundation, completed=NOW + timedelta(seconds=1))
    assert _read(foundation).status == "rejected_or_ambiguous"
    result = _read(foundation, at=NOW + timedelta(seconds=1), maximum_age_seconds=60)
    assert result.status == "stale_observation" and result.freshness == "STALE"
    assert not result.bars and result.observation_age_seconds > 60


@pytest.mark.parametrize("scope", [(Market.CHINA_A, "600000", "CNY", "SHH"),
    (Market.US, "0700.HK", "USD", "NMS"), (Market.HONG_KONG, "MSFT", "HKD", "HKG"),
    (Market.MALAYSIA, "1155.KL?token=x", "MYR", "KLS")])
def test_market_symbol_routing_is_explicit_and_rejects_wrong_scope(scope):
    with pytest.raises((ValueError, KeyError)):
        validate_snapshot_request(_request(scope))


def test_global_cli_is_read_only_and_reproducible(foundation):
    _ingest(foundation)
    store, artifacts = foundation
    args = [sys.executable, "scripts/inspect_global_technical.py", "--market", "us",
        "--symbol", "MSFT", "--database", str(store.path), "--artifact-root", str(artifacts.root),
        "--as-of", NOW.isoformat()]
    before = store.path.read_bytes()
    first = subprocess.run(args, capture_output=True, text=True, check=False)
    second = subprocess.run(args, capture_output=True, text=True, check=False)
    assert first.returncode == second.returncode == 2, first.stderr
    assert first.stdout == second.stdout and store.path.read_bytes() == before
    output = json.loads(first.stdout)
    assert output["inputs"]["observed_bar_count"] == 300
    assert output["diagnostics"]["macd_dif"] is not None
    assert output["fundamentals_status"] == output["trend_four_confirmations"] == "NOT_ASSESSED"
    assert not output["research_report_created"] and not output["readiness_promoted"]
    assert "calendar_periods" not in output


@pytest.mark.parametrize("scope", SCOPES)
@pytest.mark.parametrize("fundamentals", [False, True])
def test_markdown_cli_repeats_offline_without_altering_json_or_database(
    foundation, scope, fundamentals,
):
    _ingest(foundation, scope=scope)
    store, artifacts = foundation
    args = [sys.executable, "scripts/inspect_global_technical.py", "--market", scope[0].value,
        "--symbol", scope[1], "--database", str(store.path), "--artifact-root", str(artifacts.root),
        "--as-of", NOW.isoformat()]
    if fundamentals:
        args.extend(["--fundamentals", "--sector-profile", "bank" if scope[0] is
                     Market.MALAYSIA else "nonfinancial"])
    before = store.path.read_bytes()
    original = subprocess.run(args, capture_output=True, text=True)
    first = subprocess.run([*args, "--format", "markdown"], capture_output=True, text=True)
    second = subprocess.run([*args, "--format", "markdown"], capture_output=True, text=True)
    after = subprocess.run(args, capture_output=True, text=True)
    assert first.returncode == second.returncode == original.returncode == after.returncode == 2
    assert first.stdout == second.stdout and first.stdout.startswith(f"# {scope[1]}")
    assert "不是正式 ResearchReport" in first.stdout and "LOW" in first.stdout
    if fundamentals:
        assert "INPUT_REJECTED" in first.stdout and "基本面来源状态：missing" in first.stdout
    assert original.stdout == after.stdout and store.path.read_bytes() == before
    assert store.table_count("research_reports") == store.table_count("signals") == 0


@pytest.mark.parametrize("scope", SCOPES)
@pytest.mark.parametrize("state", ["observed", "missing", "latest_failure"])
def test_optional_trend_observations_share_retained_input_without_promoting_or_writing(
    foundation, scope, state,
):
    cutoff = NOW
    if state != "missing":
        _ingest(foundation, scope=scope)
    if state == "latest_failure":
        cutoff = NOW + timedelta(seconds=1)
        _ingest(foundation, YahooSnapshotCapture(None, "provider_unavailable"), scope, cutoff)
    store, artifacts = foundation
    args = [sys.executable, "scripts/inspect_global_technical.py", "--market", scope[0].value,
        "--symbol", scope[1], "--database", str(store.path), "--artifact-root", str(artifacts.root),
        "--as-of", cutoff.isoformat()]
    before = store.path.read_bytes()
    baseline = subprocess.run(args, capture_output=True, text=True)
    first = subprocess.run([*args, "--trend-observations"], capture_output=True, text=True)
    second = subprocess.run([*args, "--trend-observations"], capture_output=True, text=True)
    markdown = subprocess.run([*args, "--trend-observations", "--format", "markdown"],
                              capture_output=True, text=True)
    assert baseline.returncode == first.returncode == second.returncode == markdown.returncode == 2
    assert first.stdout == second.stdout
    body = json.loads(first.stdout)
    trend = body.pop("trend_price_observations")
    assert body == json.loads(baseline.stdout)
    assert trend["four_confirmations_complete"] is False
    assert trend["execution_authorized"] is False and trend["scoring_authorized"] is False
    assert trend["market_sentiment_confirmation"] is trend["industry_heat_confirmation"] is None
    assert trend["usable_observations"] == (300 if state == "observed" else 0)
    assert "完整四确认未齐" in markdown.stdout
    assert store.path.read_bytes() == before


def test_optional_trend_capture_is_rejected_before_file_creation(tmp_path):
    path = tmp_path / "must-not-exist.sqlite3"
    result = subprocess.run([sys.executable, "scripts/inspect_global_technical.py",
        "--market", "us", "--symbol", "MSFT", "--database", str(path),
        "--artifact-root", str(tmp_path / "raw"), "--trend-observations", "--capture"],
        capture_output=True, text=True)
    assert result.returncode == 2 and "trend observations are read-only" in result.stderr
    assert not path.exists()


def test_markdown_capture_is_rejected_before_any_database_creation(tmp_path):
    path = tmp_path / "must-not-exist.sqlite3"
    result = subprocess.run([sys.executable, "scripts/inspect_global_technical.py",
        "--market", "us", "--symbol", "MSFT", "--database", str(path),
        "--artifact-root", str(tmp_path / "raw"), "--format", "markdown", "--capture"],
        capture_output=True, text=True)
    assert result.returncode == 2 and "markdown display is read-only" in result.stderr
    assert not path.exists() and not (tmp_path / "raw").exists()


@pytest.mark.parametrize("scope", SCOPES)
def test_calendar_display_preserves_legacy_diagnostics_and_database(foundation, scope):
    _ingest(foundation, scope=scope)
    store, artifacts = foundation
    args = [sys.executable, "scripts/inspect_global_technical.py", "--market", scope[0].value,
        "--symbol", scope[1], "--database", str(store.path), "--artifact-root", str(artifacts.root),
        "--as-of", NOW.isoformat()]
    before = store.path.read_bytes()
    baseline = subprocess.run(args, capture_output=True, text=True)
    first = subprocess.run([*args, "--calendar-periods"], capture_output=True, text=True)
    second = subprocess.run([*args, "--calendar-periods"], capture_output=True, text=True)
    assert baseline.returncode == first.returncode == second.returncode == 2, first.stderr
    assert first.stdout == second.stdout and store.path.read_bytes() == before
    output = json.loads(first.stdout)
    calendar = output.pop("calendar_periods")
    assert output == json.loads(baseline.stdout)
    assert calendar["market"] == scope[0].value
    assert calendar["selected_observation_count"] == 300
    assert any(row["status"] == "MISSING_PERIOD_OBSERVATIONS" for row in calendar["monthly"])
    assert not calendar["scoring_authorized"] and not calendar["calendar_verified"]
    assert not output["research_report_created"] and not output["readiness_promoted"]


def test_missing_price_inputs_keep_missing_calendar_receipt(foundation):
    store, artifacts = foundation
    before = store.path.read_bytes()
    result = subprocess.run([sys.executable, "scripts/inspect_global_technical.py",
        "--market", "us", "--symbol", "MSFT", "--database", str(store.path),
        "--artifact-root", str(artifacts.root), "--as-of", NOW.isoformat(), "--calendar-periods"],
        capture_output=True, text=True)
    assert result.returncode == 2, result.stderr
    output = json.loads(result.stdout)
    assert output["calendar_periods"]["status"] == "MISSING"
    assert output["calendar_periods"]["weekly"] == output["calendar_periods"]["monthly"] == []
    assert store.path.read_bytes() == before


@pytest.mark.parametrize("scope", SCOPES)
@pytest.mark.parametrize("state", ["observed", "missing", "latest_failure"])
def test_long_horizon_cli_is_opt_in_readonly_and_retains_gaps(foundation, scope, state):
    cutoff = NOW
    if state != "missing":
        _ingest(foundation, scope=scope)
    if state == "latest_failure":
        cutoff = NOW + timedelta(seconds=1)
        _ingest(foundation, YahooSnapshotCapture(None, "provider_unavailable"), scope, cutoff)
    store, artifacts = foundation
    args = [sys.executable, "scripts/inspect_global_technical.py", "--market", scope[0].value,
        "--symbol", scope[1], "--database", str(store.path), "--artifact-root", str(artifacts.root),
        "--as-of", cutoff.isoformat()]
    before = store.path.read_bytes()
    baseline = subprocess.run(args, capture_output=True, text=True)
    first = subprocess.run([*args, "--long-horizon"], capture_output=True, text=True)
    second = subprocess.run([*args, "--long-horizon"], capture_output=True, text=True)
    note = subprocess.run([*args, "--long-horizon", "--format", "markdown"],
                          capture_output=True, text=True)
    assert baseline.returncode == first.returncode == second.returncode == note.returncode == 2
    assert first.stdout == second.stdout and "月线与年线观察" in note.stdout
    extended = json.loads(first.stdout)
    horizon = extended.pop("long_horizon")
    assert extended == json.loads(baseline.stdout)
    assert horizon["supplied_daily_row_count"] == (300 if state == "observed" else 0)
    assert not horizon["execution_authorized"] and not horizon["scoring_authorized"]
    assert horizon["source_bars_content_hash"] == extended["inputs"]["bars_content_hash"]
    assert store.path.read_bytes() == before
    assert store.table_count("research_reports") == store.table_count("signals") == 0


def test_long_horizon_capture_is_rejected_before_creating_files(tmp_path):
    path = tmp_path / "must-not-exist.sqlite3"
    result = subprocess.run([sys.executable, "scripts/inspect_global_technical.py",
        "--market", "us", "--symbol", "MSFT", "--database", str(path),
        "--artifact-root", str(tmp_path / "raw"), "--long-horizon", "--capture"],
        capture_output=True, text=True)
    assert result.returncode == 2 and "long-horizon observations are read-only" in result.stderr
    assert not path.exists() and not (tmp_path / "raw").exists()


@pytest.mark.parametrize("scope", SCOPES)
@pytest.mark.parametrize("state", ["observed", "missing", "latest_failure"])
def test_multi_timeframe_cli_preserves_old_output_and_keeps_research_boundaries(
    foundation, scope, state,
):
    cutoff = NOW
    if state != "missing":
        _ingest(foundation, scope=scope)
    if state == "latest_failure":
        cutoff = NOW + timedelta(seconds=1)
        _ingest(foundation, YahooSnapshotCapture(None, "provider_unavailable"), scope, cutoff)
    store, artifacts = foundation
    args = [sys.executable, "scripts/inspect_global_technical.py", "--market", scope[0].value,
        "--symbol", scope[1], "--database", str(store.path), "--artifact-root", str(artifacts.root),
        "--as-of", cutoff.isoformat()]
    before = store.path.read_bytes()
    legacy = subprocess.run([*args, "--long-horizon"], capture_output=True, text=True)
    new = subprocess.run([*args, "--multi-timeframe"], capture_output=True, text=True)
    repeated = subprocess.run([*args, "--multi-timeframe"], capture_output=True, text=True)
    note = subprocess.run([*args, "--multi-timeframe", "--format", "markdown"],
                          capture_output=True, text=True)
    assert legacy.returncode == new.returncode == repeated.returncode == note.returncode == 2
    assert new.stdout == repeated.stdout and "周/月/年观察" in note.stdout
    old_document, new_document = json.loads(legacy.stdout), json.loads(new.stdout)
    old_horizon, new_horizon = old_document.pop("long_horizon"), new_document.pop("long_horizon")
    assert old_document == new_document
    assert old_horizon["monthly"] == new_horizon["monthly"]
    assert old_horizon["yearly"] == new_horizon["yearly"]
    assert new_horizon["timeframe_alignment"]["comparison_eligible"] is False
    assert "weekly" not in old_horizon and not new_horizon["execution_authorized"]
    assert store.path.read_bytes() == before


def test_multi_timeframe_capture_rejects_before_any_file_creation(tmp_path):
    path = tmp_path / "must-not-exist.sqlite3"
    result = subprocess.run([sys.executable, "scripts/inspect_global_technical.py",
        "--market", "us", "--symbol", "MSFT", "--database", str(path),
        "--artifact-root", str(tmp_path / "raw"), "--multi-timeframe", "--capture"],
        capture_output=True, text=True)
    assert result.returncode == 2 and "multi-timeframe observations are read-only" in result.stderr
    assert not path.exists() and not (tmp_path / "raw").exists()


@pytest.mark.parametrize("scope", SCOPES)
@pytest.mark.parametrize("mode", ["--long-horizon", "--multi-timeframe"])
def test_annual_calendar_coverage_is_readonly_and_does_not_change_long_horizon_values(
    foundation, scope, mode,
):
    _ingest(foundation, scope=scope)
    store, artifacts = foundation
    args = [sys.executable, "scripts/inspect_global_technical.py", "--market", scope[0].value,
        "--symbol", scope[1], "--database", str(store.path), "--artifact-root", str(artifacts.root),
        "--as-of", NOW.isoformat(), mode]
    before = store.path.read_bytes()
    baseline = subprocess.run(args, capture_output=True, text=True)
    extended = subprocess.run([*args, "--calendar-coverage"], capture_output=True, text=True)
    repeated = subprocess.run([*args, "--calendar-coverage"], capture_output=True, text=True)
    note = subprocess.run([*args, "--calendar-coverage", "--format", "markdown"],
                          capture_output=True, text=True)
    assert baseline.returncode == extended.returncode == repeated.returncode == note.returncode == 2
    assert extended.stdout == repeated.stdout and "交易日期覆盖核对" in note.stdout
    document = json.loads(extended.stdout)
    coverage = document.pop("calendar_coverage")
    assert document == json.loads(baseline.stdout)
    assert coverage["calendar_period_input_hash"] == document["long_horizon"]["calendar_input_hash"]
    assert coverage["supplied_calendar_row_count"] == 0 and "yearly" in coverage
    assert all(row["observed_open_date_coverage_percent"] is None for row in coverage["yearly"])
    assert store.path.read_bytes() == before


def _calendar_args(foundation, scope=SCOPES[0]):
    store, artifacts = foundation
    return [sys.executable, "scripts/inspect_global_technical.py", "--market", scope[0].value,
        "--symbol", scope[1], "--database", str(store.path), "--artifact-root", str(artifacts.root),
        "--as-of", NOW.isoformat(), "--calendar-periods"]


@pytest.mark.parametrize("shared", [False, True])
def test_explicit_nasdaq_source_cli_is_offline_repeatable_without_calendar_population(
    foundation, tmp_path, shared,
):
    from tong_quant.data.providers import nasdaq_calendar as nasdaq

    _ingest(foundation)
    store, artifacts = foundation
    calendar_store = store if shared else SQLiteStore(tmp_path / "calendar.sqlite3")
    if not shared:
        calendar_store.initialize()
    calendar_artifacts = artifacts if shared else FileSystemArtifactStore(tmp_path / "calendar-raw")
    body = b"""<h1>U.S. Equity and Options Markets Holiday Schedule 2026</h1>
<table><tr><th>2026</th><th>Holiday</th><th>Status</th></tr>
<tr><td>November 27, 2026</td><td>Early Close synthetic</td><td>1:00 p.m.</td></tr>
</table>"""
    ProviderNeutralIngestionService(calendar_store, artifact_store=calendar_artifacts,
        clock=lambda: NOW).ingest(nasdaq.NasdaqCalendarAdapter(
            download=lambda _: nasdaq.NasdaqCalendarCapture(body), clock=lambda: NOW),
            ProviderDatasetRequest(nasdaq.DATASET, Market.US, "NASDAQ:2026", NOW, {"year": "2026"}))
    before = (store.path.read_bytes(), calendar_store.path.read_bytes())
    args = [*_calendar_args(foundation), "--multi-timeframe", "--calendar-coverage"]
    extra = ["--nasdaq-calendar-database", str(calendar_store.path),
        "--nasdaq-calendar-artifact-root", str(calendar_artifacts.root),
        "--nasdaq-calendar-year", "2026", "--nasdaq-max-source-age-seconds", "3600"]
    legacy = subprocess.run(args, capture_output=True, text=True)
    first = subprocess.run([*args, *extra], capture_output=True, text=True)
    second = subprocess.run([*args, *extra], capture_output=True, text=True)
    note = subprocess.run([*args, *extra, "--format", "markdown"], capture_output=True, text=True)
    assert first.returncode == second.returncode == note.returncode == legacy.returncode == 2
    assert not first.stderr and first.stdout == second.stdout
    document = json.loads(first.stdout)
    review = document.pop("nasdaq_calendar_review")
    assert document == json.loads(legacy.stdout)
    assert review["snapshot_scope"] == ("single_database_snapshot" if shared else
                                       "separate_database_snapshots_shared_cutoff")
    assert review["source"]["freshness"] == "WITHIN_CONFIGURED_LIMIT"
    assert review["declaration_comparisons"][0]["core_close_local"] == "13:00:00"
    assert "Nasdaq 原文日历证据" in note.stdout
    assert "v7-nasdaq-comparison-context" in note.stdout
    assert before == (store.path.read_bytes(), calendar_store.path.read_bytes())
    assert store.table_count("trading_calendar") == 0
    assert calendar_store.table_count("trading_calendar") == 0


@pytest.mark.parametrize("kind", [
    "capture", "market", "year", "age", "as_of", "partial", "same_db_wrong_root",
])
def test_nasdaq_source_cli_rejects_invalid_options_before_filesystem_or_network(tmp_path, kind):
    path, calendar = tmp_path / "price.sqlite3", tmp_path / "calendar.sqlite3"
    options = {"--market": "us", "--symbol": "MSFT", "--database": str(path),
        "--artifact-root": str(tmp_path / "raw"), "--as-of": NOW.isoformat(),
        "--nasdaq-calendar-database": str(calendar),
        "--nasdaq-calendar-artifact-root": str(tmp_path / "calendar-raw"),
        "--nasdaq-calendar-year": "2026", "--nasdaq-max-source-age-seconds": "3600"}
    if kind == "market":
        options["--market"] = "hong_kong"
    elif kind == "year":
        options["--nasdaq-calendar-year"] = "1999"
    elif kind == "age":
        options["--nasdaq-max-source-age-seconds"] = "0"
    elif kind == "as_of":
        options.pop("--as-of")
    elif kind == "partial":
        options.pop("--nasdaq-calendar-artifact-root")
    elif kind == "same_db_wrong_root":
        options["--nasdaq-calendar-database"] = str(path)
    args = [sys.executable, "scripts/inspect_global_technical.py",
        *(value for pair in options.items() for value in pair)]
    result = subprocess.run([*args, *(["--capture"] if kind == "capture" else [])],
                            capture_output=True, text=True)
    assert result.returncode == 2 and not result.stdout and "error:" in result.stderr
    assert not path.exists() and not calendar.exists()
    assert not (tmp_path / "raw").exists() and not (tmp_path / "calendar-raw").exists()


@pytest.mark.parametrize("kind", ["refresh", "stale_prices", "latest_failure"])
def test_nasdaq_refresh_preserves_historical_report_and_cannot_rejuvenate_prices(
    foundation, tmp_path, kind,
):
    from tong_quant.data.providers import nasdaq_calendar as nasdaq

    _ingest(foundation)
    prices, artifacts = foundation
    calendar = SQLiteStore(tmp_path / "calendar.sqlite3")
    calendar.initialize()
    raw = FileSystemArtifactStore(tmp_path / "calendar-raw")
    body = b"""<h1>U.S. Equity and Options Markets Holiday Schedule 2026</h1>
<table><tr><th>2026</th><th>Holiday</th><th>Status</th></tr>
<tr><td>November 27, 2026</td><td>Early Close synthetic</td><td>1:00 p.m.</td></tr>
</table>"""

    def capture(at, failed=False):
        response = nasdaq.NasdaqCalendarCapture(None, "http_403") if failed else (
            nasdaq.NasdaqCalendarCapture(body))
        ProviderNeutralIngestionService(calendar, artifact_store=raw,
            clock=lambda: at).ingest(nasdaq.NasdaqCalendarAdapter(
                download=lambda _: response, clock=lambda: at),
                ProviderDatasetRequest(nasdaq.DATASET, Market.US, "NASDAQ:2026", at,
                                       {"year": "2026"}))

    args = [sys.executable, "scripts/inspect_global_technical.py", "--market", "us",
        "--symbol", "MSFT", "--database", str(prices.path), "--artifact-root", str(artifacts.root),
        "--multi-timeframe", "--calendar-coverage",
        "--nasdaq-calendar-database", str(calendar.path),
        "--nasdaq-calendar-artifact-root", str(raw.root), "--nasdaq-calendar-year", "2026",
        "--nasdaq-max-source-age-seconds", "60"]

    def read(at, *options):
        result = subprocess.run([*args, "--as-of", at.isoformat(), *options],
                                capture_output=True, text=True)
        assert result.returncode == 2 and not result.stderr
        return result.stdout

    capture(NOW)
    old_cutoff = NOW + timedelta(seconds=1)
    old_report = read(old_cutoff)
    capture(NOW + timedelta(seconds=2))
    if kind == "latest_failure":
        capture(NOW + timedelta(seconds=4), failed=True)
    before = (prices.path.read_bytes(), calendar.path.read_bytes())
    assert read(old_cutoff) == old_report
    current_at = NOW + timedelta(seconds=5)
    extra = ["--max-observation-age-seconds", "1"] if kind == "stale_prices" else []
    current_json = read(current_at, *extra)
    assert current_json == read(current_at, *extra)
    current = json.loads(current_json)
    source = current["nasdaq_calendar_review"]["source"]
    old = json.loads(old_report)["nasdaq_calendar_review"]["source"]
    assert len(old["captures"]) == 1 and old["source_capture_age_microseconds"] == 1_000_000
    if kind == "latest_failure":
        assert source["freshness"] == "BLOCKED_INPUT"
        assert source["source_status"] == "http_403" and source["declarations"] == []
        assert current["nasdaq_calendar_review"]["declaration_comparisons"] == []
    else:
        assert source["freshness"] == "WITHIN_CONFIGURED_LIMIT"
        assert source["source_capture_age_microseconds"] == 3_000_000
        assert len(source["captures"]) == 2
    if kind == "stale_prices":
        assert current["inputs"]["freshness"] == "STALE"
        assert current["inputs"]["observed_bar_count"] == 0
        assert current["long_horizon"]["status"] == "MISSING"
        assert all(row["price_date_observed"] is None
                   for row in current["nasdaq_calendar_review"]["declaration_comparisons"])
    assert before == (prices.path.read_bytes(), calendar.path.read_bytes())
    assert calendar.table_count("trading_calendar") == prices.table_count("trading_calendar") == 0
    assert current["research_report_created"] is False and current["readiness_promoted"] is False


@pytest.mark.parametrize("scope", SCOPES)
@pytest.mark.parametrize("has_calendar", [False, True])
def test_calendar_coverage_opt_in_is_read_only_reproducible_and_never_promotes(foundation, scope,
                                                                            has_calendar):
    _ingest(foundation, scope=scope)
    store, _ = foundation
    if has_calendar:
        # Synthetic all-open declarations deliberately conflict with no real calendar claims.
        first = date(2024, 12, 1)
        store.upsert_trading_sessions(TradingSession(scope[0], first + timedelta(days=index),
            True, NOW - timedelta(days=1), "synthetic-only-calendar")
            for index in range((NOW.date() - first).days + 1))
    before = store.path.read_bytes()
    args = _calendar_args(foundation, scope)
    baseline = subprocess.run(args, capture_output=True, text=True)
    first = subprocess.run([*args, "--calendar-coverage"], capture_output=True, text=True)
    second = subprocess.run([*args, "--calendar-coverage"], capture_output=True, text=True)
    assert first.returncode == second.returncode == baseline.returncode == 2, first.stderr
    assert first.stdout == second.stdout and store.path.read_bytes() == before
    output = json.loads(first.stdout)
    coverage = output.pop("calendar_coverage")
    assert output == json.loads(baseline.stdout)
    if has_calendar:
        assert coverage["selected_calendar_date_count"] > 0
    else:
        assert coverage["selected_calendar_date_count"] == 0
    assert coverage["calendar_trust_level"] == "unknown"
    assert coverage["calendar_availability_precision"] == "unknown"
    assert not coverage["scoring_authorized"] and not coverage["session_completeness_verified"]
    if has_calendar:
        assert any(row["missing_open_dates"] for row in coverage["weekly"])
        assert any(row["status"] == "DATES_MATCH_UNVERIFIED" for row in coverage["weekly"])
    else:
        assert all(row["unknown_calendar_dates"] for row in coverage["weekly"])
        assert all(row["observed_open_date_coverage_percent"] is None
                   for row in coverage["weekly"])


def test_calendar_and_price_reads_share_a_snapshot_during_competing_write(
    foundation, monkeypatch, capsys,
):
    from tong_quant.data import global_price_inputs

    _ingest(foundation)
    store, _ = foundation
    original = global_price_inputs.read_global_price_inputs

    def competing_write(*args, **kwargs):
        result = original(*args, **kwargs)
        SQLiteStore(store.path).upsert_trading_sessions((TradingSession(Market.US,
            date(2025, 1, 2), True, NOW - timedelta(days=1), "synthetic-only-calendar"),))
        return result

    monkeypatch.setattr(global_price_inputs, "read_global_price_inputs", competing_write)
    args = [*_calendar_args(foundation)[1:], "--calendar-coverage"]
    monkeypatch.setattr(sys, "argv", args)
    with pytest.raises(SystemExit) as stopped:
        runpy.run_path(args[0], run_name="__main__")
    assert stopped.value.code == 2
    output = json.loads(capsys.readouterr().out)
    assert output["calendar_coverage"]["selected_calendar_date_count"] == 0
    later = subprocess.run([*_calendar_args(foundation), "--calendar-coverage"],
                           capture_output=True, text=True)
    assert later.returncode == 2, later.stderr
    assert json.loads(later.stdout)["calendar_coverage"]["selected_calendar_date_count"] == 1


@pytest.mark.parametrize("value", [2, -1, 0.5, "open"])
def test_calendar_reader_rejects_corrupt_database_open_flags(foundation, value):
    store, _ = foundation
    store.upsert_trading_sessions((TradingSession(Market.US, date(2025, 1, 2), True,
        NOW - timedelta(days=1), "synthetic-only-calendar"),))
    with store._connect() as connection:
        connection.execute("UPDATE trading_calendar SET is_open = ?", (value,))
    before = store.path.read_bytes()
    with pytest.raises(ValueError, match="exactly integer"):
        store.trading_sessions(Market.US, date(2025, 1, 1), NOW.date(), as_of=NOW)
    assert store.path.read_bytes() == before


@pytest.mark.parametrize("value", [1, 0, 2, -1, 0.5, "open"])
def test_calendar_writer_rejects_lossy_bool_conversion_before_any_write(foundation, value):
    store, _ = foundation
    first = TradingSession(Market.US, date(2025, 1, 2), True,
                           NOW - timedelta(days=1), "synthetic-only-calendar")
    second = replace(first, trade_date=date(2025, 1, 3), is_open=value)
    before = store.path.read_bytes()
    with pytest.raises(ValueError, match="must be a boolean"):
        store.upsert_trading_sessions((first, second))
    assert store.path.read_bytes() == before


def test_calendar_coverage_flag_requires_readonly_periods_before_filesystem_access(tmp_path):
    path = tmp_path / "absent.sqlite3"
    result = subprocess.run([sys.executable, "scripts/inspect_global_technical.py", "--market",
        "us", "--symbol", "MSFT", "--database", str(path), "--artifact-root", str(tmp_path),
        "--calendar-coverage"], capture_output=True, text=True)
    assert result.returncode == 2 and "requires --calendar-periods" in result.stderr
    assert not path.exists()


@pytest.mark.parametrize("limit", [0, -1, True, 1.5, 16 * 1024 * 1024 + 1])
def test_yahoo_transport_requires_a_bounded_integer_response_limit(limit):
    with pytest.raises(ValueError, match="byte limit"):
        YahooChartHttpClient(max_response_bytes=limit)


def test_yahoo_transport_bounds_read_before_json_parsing(monkeypatch):
    reads = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, size):
            reads.append(size)
            return b"x" * size

    monkeypatch.setattr(yahoo, "urlopen", lambda *args, **kwargs: Response())
    with pytest.raises(ValueError, match="exceeds byte limit"):
        YahooChartHttpClient(max_response_bytes=64).chart(
            "MSFT", start_date="2026-10-01", end_date="2026-10-26")
    assert reads == [65]
