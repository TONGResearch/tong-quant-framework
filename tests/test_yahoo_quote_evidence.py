"""Synthetic price captures do not qualify provider truth, valuations or trades."""

import json
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.providers.contracts import ProviderDatasetRequest
from tong_quant.data.providers.yahoo_quote import (
    DATASET,
    MAX_BYTES,
    YahooChinaQuoteEvidenceAdapter,
    YahooQuoteCapture,
    normalize_quote,
    yahoo_equity_symbol,
)
from tong_quant.data.quote_evidence import inspect_yahoo_quote
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market

NOW = datetime(2026, 10, 25, 8, tzinfo=UTC)
QUOTE = NOW - timedelta(days=2)


def _capture(**changes):
    meta = {"symbol": "002624.SZ", "currency": "CNY", "exchangeName": "SHZ",
            "instrumentType": "EQUITY", "exchangeTimezoneName": "Asia/Shanghai",
            "regularMarketPrice": 10.0, "regularMarketTime": int(QUOTE.timestamp())}
    meta.update(changes)
    return YahooQuoteCapture(NOW.date(), {"chart": {"error": None, "result": [{
        "meta": meta, "indicators": {"adjclose": [{"adjclose": [999]}]},
    }]}})


@pytest.fixture
def foundation(tmp_path):
    store = SQLiteStore(tmp_path / "quotes.sqlite3")
    store.initialize()
    return store, FileSystemArtifactStore(tmp_path / "artifacts")


def _ingest(foundation, capture=None, at=NOW, completed=None):
    store, artifacts = foundation
    adapter = YahooChinaQuoteEvidenceAdapter(download=lambda _: capture or _capture(),
                                             clock=lambda: at)
    return ProviderNeutralIngestionService(
        store, artifact_store=artifacts, clock=lambda: completed or at,
    ).ingest(adapter, ProviderDatasetRequest(DATASET, Market.CHINA_A, "002624", at))


def _read(foundation, as_of=NOW):
    store, artifacts = foundation
    return inspect_yahoo_quote(store, artifacts, "002624", as_of=as_of)


@pytest.mark.parametrize("symbol", ["920982", "832982", "510300", "900901", "AAPL",
                                   "002624.SZ", "00063", "１２３４５６", "002624?key=x"])
def test_scope_never_guesses_bse_funds_or_external_tickers(symbol):
    with pytest.raises(ValueError):
        yahoo_equity_symbol(symbol)


@pytest.mark.parametrize("symbol,ticker", [("000063", "000063.SZ"), ("002624", "002624.SZ"),
                                         ("688363", "688363.SS"), ("600109", "600109.SS")])
def test_explicit_equity_routes(symbol, ticker):
    assert yahoo_equity_symbol(symbol) == ticker


@pytest.mark.parametrize("field,value", [
    ("symbol", "000063.SZ"), ("currency", "USD"), ("exchangeName", "SHH"),
    ("instrumentType", "ETF"), ("exchangeTimezoneName", "UTC"), ("symbol", None),
])
def test_native_identity_exchange_currency_and_instrument_scope_must_all_match(field, value):
    result = normalize_quote(_capture(**{field: value}), "002624", NOW)
    assert result["status"] == "invalid_response" and result["price"] is None


@pytest.mark.parametrize("value", [None, True, 0, -1, "NaN", "Infinity", "1e100", {}, "bad"])
def test_missing_or_invalid_price_is_never_zero_or_adjusted_close(value):
    result = normalize_quote(_capture(regularMarketPrice=value), "002624", NOW)
    assert result["status"] == "invalid_response" and result["price"] is None


@pytest.mark.parametrize("value", [None, True, 0, -1, "123", 253402300800,
                                   int(NOW.timestamp()) + 1])
def test_quote_clock_requires_an_explicit_nonfuture_epoch(value):
    result = normalize_quote(_capture(regularMarketTime=value), "002624", NOW)
    assert result["status"] == "invalid_response" and result["claimed_quote_at"] is None


@pytest.mark.parametrize("payload", [{}, {"chart": {}}, {"chart": {"error": {}, "result": []}},
    {"chart": {"error": None, "result": [None]}},
    {"chart": {"error": None, "result": [{}, {}]}},
])
def test_ambiguous_chart_schema_is_not_a_quote(payload):
    assert normalize_quote(YahooQuoteCapture(NOW.date(), payload), "002624", NOW)["status"] == (
        "invalid_response")


@pytest.mark.parametrize("key", ["token", "api_key", "secret", "password", "webhook_url"])
def test_decoded_sensitive_fields_are_rejected_before_envelope_encoding(key):
    with pytest.raises(ValueError, match="credential"):
        YahooQuoteCapture(NOW.date(), {key: "synthetic fixture only"})


@pytest.mark.parametrize("payload", [{"fixture": "x" * (MAX_BYTES + 1)},
                                   {"value": float("nan")}, {"value": float("inf")}])
def test_oversized_or_nonfinite_decoded_snapshots_are_not_persistable(payload):
    with pytest.raises(ValueError):
        YahooQuoteCapture(NOW.date(), payload)


def test_price_only_observation_never_borrows_shares_market_value_or_adjusted_close():
    result = normalize_quote(_capture(marketCap=1000000, sharesOutstanding=10000), "002624", NOW)
    assert result["status"] == "price_only_unqualified" and result["price"] == "10.0"
    assert result["total_shares"] is result["total_market_value"] is None
    assert result["float_shares"] is result["float_market_value"] is None
    assert not result["valuation_authorized"] and not result["execution_authorized"]


def test_source_bound_atomic_capture_is_idempotent_and_retrieval_time_only(foundation):
    store, _ = foundation
    _ingest(foundation)
    _ingest(foundation)
    result = _read(foundation)
    assert result["source_bound"] and result["price"] == "10.0"
    assert result["status"] == "price_only_unqualified" and result["freshness"] == "UNASSESSED"
    assert result["inspections"][0]["trust_level"] == "low"
    assert result["inspections"][0]["availability_precision"] == "retrieval_time"
    assert not result["market_value_available"] and not result["investment_scoring_authorized"]
    assert store.table_count("provider_evidence_records") == 1
    assert store.table_count("provider_artifacts") == 1
    for table in ("daily_bars", "fundamental_facts", "research_reports", "signals"):
        assert store.table_count(table) == 0
    assert _read(foundation, NOW - timedelta(microseconds=1))["status"] == "missing"
    assert _read(foundation) == result


@pytest.mark.parametrize("kind", ["payload", "raw_bytes", "artifact", "batch_status",
                                  "batch_time", "batch_hash", "batch_parameters"])
def test_tampered_or_future_source_binding_is_rejected_without_deleting_evidence(foundation, kind):
    store, artifacts = foundation
    ingestion = _ingest(foundation)
    result = _read(foundation)
    digest = result["inspections"][0]["raw_data_hash"]
    with store._connect() as connection:
        if kind == "payload":
            row = connection.execute(
                "SELECT payload_json FROM provider_evidence_records").fetchone()
            payload = json.loads(row["payload_json"])
            payload["price"] = "999"
            connection.execute("UPDATE provider_evidence_records SET payload_json=?",
                               (json.dumps(payload),))
        elif kind == "artifact":
            connection.execute("UPDATE provider_artifacts SET source_identity='tampered fixture'")
        elif kind.startswith("batch_"):
            column, value = {
                "batch_status": ("status", "failed"),
                "batch_time": ("completed_at", (NOW + timedelta(seconds=1)).isoformat()),
                "batch_hash": ("raw_response_hash", "f" * 64),
                "batch_parameters": ("parameters_json", "{}"),
            }[kind]
            connection.execute(f"UPDATE ingestion_batches SET {column}=? WHERE batch_id=?",
                               (value, ingestion.batch_id))
    if kind == "raw_bytes":
        (artifacts.root / "sha256" / digest[:2] / f"{digest}.bin").write_bytes(b"tampered fixture")
    assert _read(foundation)["status"] == "rejected_or_ambiguous"
    assert store.table_count("provider_evidence_records") == 1


def test_latest_failure_and_tie_never_fall_back_to_a_favorable_quote(foundation):
    _ingest(foundation)
    failure = YahooQuoteCapture(NOW.date(), None, "provider_unavailable")
    _ingest(foundation, failure, at=NOW + timedelta(seconds=1))
    result = _read(foundation, NOW + timedelta(seconds=1))
    assert result["source_bound"] and result["status"] == "unavailable"
    assert result["price"] is None and len(result["inspections"]) == 2
    _ingest(foundation, _capture(regularMarketPrice=11), at=NOW + timedelta(seconds=1))
    assert _read(foundation, NOW + timedelta(seconds=1))["status"] == "rejected_or_ambiguous"


def test_capture_and_ingestion_cutoffs_cannot_be_backdated(foundation):
    store, artifacts = foundation
    adapter = YahooChinaQuoteEvidenceAdapter(download=lambda _: _capture(), clock=lambda: NOW)
    with pytest.raises(ValueError, match="future event"):
        ProviderNeutralIngestionService(store, artifact_store=artifacts, clock=lambda: NOW).ingest(
            adapter, ProviderDatasetRequest(DATASET, Market.CHINA_A, "002624",
                                            NOW - timedelta(seconds=1)))
    with pytest.raises(ValueError, match="capture precedes"):
        adapter.fetch(ProviderDatasetRequest(DATASET, Market.CHINA_A, "002624",
                                             NOW + timedelta(seconds=1)))
    assert store.table_count("provider_evidence_records") == 0


def test_completed_ingestion_is_required_even_when_capture_is_visible(foundation):
    _ingest(foundation, completed=NOW + timedelta(seconds=1))
    assert _read(foundation)["status"] == "rejected_or_ambiguous"
    assert _read(foundation, NOW + timedelta(seconds=1))["source_bound"]


def test_quote_cli_fixed_cutoff_is_read_only_and_deterministic(foundation):
    store, artifacts = foundation
    _ingest(foundation)
    args = [sys.executable, "scripts/capture_yahoo_quote.py", "--read-only", "--symbol", "002624",
            "--database", str(store.path), "--artifact-root", str(artifacts.root),
            "--as-of", NOW.isoformat()]
    before = store.path.read_bytes()
    first = subprocess.run(args, capture_output=True, text=True, check=False)
    second = subprocess.run(args, capture_output=True, text=True, check=False)
    assert first.returncode == second.returncode == 2, first.stderr
    assert first.stdout == second.stdout and store.path.read_bytes() == before
    assert not json.loads(first.stdout)["valuation_authorized"]


def test_capture_cli_prefetches_without_relaxing_strict_ingestion(foundation, monkeypatch, capsys):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    import capture_yahoo_quote as script

    store, artifacts = foundation

    class Clock:
        @staticmethod
        def now(zone):
            return NOW

    def service(store, *, artifact_store):
        return ProviderNeutralIngestionService(
            store, artifact_store=artifact_store, clock=lambda: NOW)

    monkeypatch.setattr(script, "datetime", Clock)
    monkeypatch.setattr(script, "download_quote", lambda _: _capture())
    monkeypatch.setattr(script, "ProviderNeutralIngestionService", service)
    monkeypatch.setattr(sys, "argv", ["capture", "--symbol", "002624", "--database",
                                     str(store.path), "--artifact-root", str(artifacts.root)])
    with pytest.raises(SystemExit) as error:
        script.main()
    assert error.value.code == 2
    result = json.loads(capsys.readouterr().out)
    assert result["source_bound"] and result["status"] == "price_only_unqualified"
    assert not result["market_value_available"]


@pytest.mark.parametrize("change", ["market", "dataset", "parameters", "query_date"])
def test_unsupported_requests_and_future_query_dates_fail_before_persistence(foundation, change):
    request = ProviderDatasetRequest(DATASET, Market.CHINA_A, "002624", NOW)
    capture = _capture()
    if change == "market":
        request = replace(request, market=Market.US)
    elif change == "dataset":
        request = replace(request, dataset="other")
    elif change == "parameters":
        request = replace(request, parameters={"arbitrary_url": "synthetic"})
    else:
        capture = replace(capture, query_date=(NOW + timedelta(days=1)).date())
    with pytest.raises(ValueError):
        YahooChinaQuoteEvidenceAdapter(download=lambda _: capture, clock=lambda: NOW).fetch(request)
