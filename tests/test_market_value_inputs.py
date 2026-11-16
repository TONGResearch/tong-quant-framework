"""Synthetic quote bodies verify engineering contracts, never source/valuation quality."""

import json
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal, localcontext
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.market_value_inputs import MarketValueInputSnapshot
from tong_quant.data.market_value_reader import MarketValueInputReader
from tong_quant.data.providers.contracts import ProviderDatasetRequest
from tong_quant.data.providers.eastmoney_market_values import (
    DATASET,
    MAX_BYTES,
    PROVIDER,
    EastmoneyMarketValueAdapter,
    QuoteHttpCapture,
    normalize_quote,
    quote_url,
)
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Adjustment, DataTrustLevel, Market
from tong_quant.domain.models import Bar, Instrument
from tong_quant.research.financial.market_value import (
    MarketValueMatchingPolicy,
    market_value_diagnostics,
)

NOW = datetime(2026, 10, 23, 8, tzinfo=UTC)
QUOTE = NOW - timedelta(hours=1)
CUTOFF = NOW + timedelta(minutes=1)


def _capture(**changes):
    data = {"f57": "002624", "f58": "Synthetic fixture", "f43": 20, "f59": 2,
            "f84": 20000, "f85": 10000, "f86": int(QUOTE.timestamp()),
            "f116": 400000, "f117": 200000}
    data.update(changes)
    return QuoteHttpCapture(200, json.dumps({"rc": 0, "data": data}).encode())


def _adapter(capture=None, clock=NOW):
    return EastmoneyMarketValueAdapter(download=lambda _: capture or _capture(),
                                       clock=lambda: clock)


def _request(as_of=NOW):
    return ProviderDatasetRequest(DATASET, Market.CHINA_A, "002624", as_of)


@pytest.fixture
def foundation(tmp_path):
    store = SQLiteStore(tmp_path / "research.sqlite3")
    store.initialize()
    artifacts = FileSystemArtifactStore(tmp_path / "artifacts")
    return store, artifacts


def _ingest(foundation, capture=None, clock=NOW):
    store, artifacts = foundation
    return ProviderNeutralIngestionService(
        store, artifact_store=artifacts, clock=lambda: clock,
    ).ingest(_adapter(capture, clock), _request(clock))


def _read(foundation, as_of=CUTOFF):
    store, artifacts = foundation
    return MarketValueInputReader(store, artifacts).read("002624", Market.CHINA_A, as_of=as_of)


def _bar(**changes):
    instrument = Instrument("002624", Market.CHINA_A, "Synthetic", available_at=QUOTE)
    return replace(Bar(instrument, QUOTE, QUOTE, Decimal("20"), Decimal("21"),
                       Decimal("19"), Decimal("20"), Decimal("100"), source="Synthetic"), **changes)


@pytest.mark.parametrize("symbol", ["920982", "832982", "510300", "900901", "00063",
                                   "000063;pwd", "１２３４５６", "AAPL"])
def test_quote_scope_never_guesses_bse_funds_or_global_mapping(symbol):
    with pytest.raises(ValueError):
        quote_url(symbol)


@pytest.mark.parametrize("symbol,market_prefix", [("000063", "0"), ("002624", "0"),
                                                 ("688363", "1"), ("600109", "1")])
def test_fixed_public_endpoint_and_explicit_equity_routes(symbol, market_prefix):
    url = quote_url(symbol)
    assert url.startswith("https://push2.eastmoney.com/api/qt/stock/get?")
    assert f"secid={market_prefix}.{symbol}" in url and "fltt=2" in url


@pytest.mark.parametrize("status", [302, 403, 429, 500])
def test_http_failures_are_unavailable_not_zero_market_value(status):
    payload = normalize_quote(QuoteHttpCapture(status, b"not a quote"), "002624", NOW)
    assert payload["status"] == "unavailable" and payload["reasons"] == [f"HTTP_{status}"]
    assert payload["total_market_value"] is payload["float_market_value"] is None


@pytest.mark.parametrize("body", [b"<html>not JSON</html>", b'{"rc":0,"data":null}',
                                 b'{"rc":false,"data":{}}', b'{"rc":0,"rc":1,"data":{}}'])
def test_bad_json_schema_and_duplicate_fields_are_not_accepted(body):
    payload = normalize_quote(QuoteHttpCapture(200, body), "002624", NOW)
    assert payload["status"] == "invalid_response"


@pytest.mark.parametrize("change", [
    {"f84": None}, {"f85": "-"}, {"f116": True}, {"f117": "NaN"}, {"f43": 0},
    {"f84": -1}, {"f84": "20000.5"}, {"f85": 30000}, {"f117": 500000},
    {"f86": None}, {"f86": True}, {"f86": int((NOW + timedelta(seconds=1)).timestamp())},
])
def test_missing_invalid_units_counts_and_future_quote_claims_remain_visible(change):
    payload = normalize_quote(_capture(**change), "002624", NOW)
    assert payload["status"] == "incomplete_or_inconsistent" and payload["reasons"]
    assert payload["valuation_authorized"] is False


def test_subject_mismatch_does_not_publish_the_wrong_company_values():
    payload = normalize_quote(_capture(f57="000063"), "002624", NOW)
    assert payload["status"] == "invalid_response" and payload["total_market_value"] is None


def test_raw_size_and_labelled_secret_filtering():
    with pytest.raises(ValueError):
        QuoteHttpCapture(200, b"x" * (MAX_BYTES + 1))
    with pytest.raises(ValueError):
        QuoteHttpCapture(200, b'{"api_key":"synthetic-only-not-a-credential"}')


def test_atomic_capture_is_idempotent_low_trust_and_visible_only_after_retrieval(foundation):
    store, artifacts = foundation
    first = _ingest(foundation)
    _ingest(foundation)
    assert store.table_count("provider_evidence_records") == 1
    assert store.table_count("provider_artifacts") == 1
    assert store.table_count("daily_bars") == store.table_count("fundamental_facts") == 0
    snapshot = _read(foundation)
    (inspection,) = snapshot.inspections
    assert inspection.source_bound and inspection.record.trust_level is DataTrustLevel.LOW
    assert inspection.record.available_at == NOW and inspection.record.observed_at is None
    assert inspection.record.payload["claimed_quote_at"] == QUOTE.isoformat()
    assert not _read(foundation, NOW - timedelta(microseconds=1)).inspections
    row = store.provider_evidence_as_of(provider=PROVIDER, dataset=DATASET, market=Market.CHINA_A,
                                       subject="002624", as_of=CUTOFF)[0]
    assert row["batch_id"] == first.batch_id
    result = market_value_diagnostics(snapshot, (_bar(),))
    assert result["quote_bar_date_match"] is result["quote_bar_price_match"] is True
    assert result["arithmetic_consistency"] == "EXACT_AGREEMENT"
    assert result["total_value_residual"] == result["float_value_residual"] == "0"
    assert result["freshness"] == "UNASSESSED" and result["valuation_multiple"] is None
    assert not result["valuation_authorized"] and not result["investment_scoring_authorized"]
    assert not result["execution_authorized"] and not result["historical_replay_eligible"]
    assert snapshot.document()["valuation_authorized"] is False
    assert market_value_diagnostics(snapshot, (_bar(),)) == result
    with localcontext() as context:
        context.prec = 3
        assert market_value_diagnostics(snapshot, (_bar(),)) == result


@pytest.mark.parametrize("defect", ["payload", "artifact_bytes", "artifact_metadata",
                                  "batch_status", "batch_time", "batch_hash", "batch_parameters"])
def test_source_tampering_and_future_batches_reject_but_preserve_records(foundation, defect):
    store, artifacts = foundation
    first = _ingest(foundation)
    (inspection,) = _read(foundation).inspections
    artifact_id = inspection.record.payload["artifact_id"]
    with store._connect() as connection:
        if defect == "payload":
            payload = dict(inspection.record.payload)
            payload["total_market_value"] = "123"
            connection.execute("UPDATE provider_evidence_records SET payload_json = ?",
                               (json.dumps(payload),))
        elif defect == "artifact_metadata":
            connection.execute("UPDATE provider_artifacts SET source_identity = ?", ("tampered",))
        elif defect.startswith("batch_"):
            column, value = {
                "batch_status": ("status", "failed"),
                "batch_time": ("completed_at", (CUTOFF + timedelta(seconds=1)).isoformat()),
                "batch_hash": ("raw_response_hash", "f" * 64),
                "batch_parameters": ("parameters_json", "{}"),
            }[defect]
            connection.execute(f"UPDATE ingestion_batches SET {column} = ? WHERE batch_id = ?",
                               (value, first.batch_id))
    if defect == "artifact_bytes":
        row = store.provider_artifact(artifact_id)
        (artifacts.root / row["storage_key"]).write_bytes(b"tampered fixture")
    snapshot = _read(foundation)
    assert len(snapshot.inspections) == 1 and not snapshot.inspections[0].source_bound
    assert market_value_diagnostics(snapshot)["status"] == "rejected_or_ambiguous"
    assert store.table_count("provider_evidence_records") == 1


def test_new_failure_does_not_fall_back_to_old_good_snapshot(foundation):
    _ingest(foundation)
    _ingest(foundation, QuoteHttpCapture(302, b"redirect"), NOW + timedelta(seconds=1))
    snapshot = _read(foundation)
    assert len(snapshot.inspections) == 2 and all(e.source_bound for e in snapshot.inspections)
    result = market_value_diagnostics(snapshot)
    assert result["status"] == "unavailable" and result["reasons"] == ["HTTP_302"]


def test_arithmetic_conflicts_are_not_rounded_away_and_stale_dates_remain_visible(foundation):
    _ingest(foundation, _capture(f116="400000.01"))
    result = market_value_diagnostics(
        _read(foundation), (_bar(timestamp=QUOTE - timedelta(days=1)),))
    assert result["arithmetic_consistency"] == "CONFLICT"
    assert result["total_value_residual"] == "0.01"
    assert result["quote_bar_date_match"] is False and result["quote_bar_price_match"] is True
    assert not result["valuation_authorized"]


def test_ambiguous_latest_cannot_select_one_favorable_quote(foundation):
    _ingest(foundation)
    _ingest(foundation, _capture(f116="400001"))
    assert market_value_diagnostics(_read(foundation))["status"] == "rejected_or_ambiguous"


@pytest.mark.parametrize("change", [{"adjustment": Adjustment.FORWARD},
                                    {"available_at": CUTOFF + timedelta(seconds=1)},
                                    {"timestamp": CUTOFF + timedelta(seconds=1)}])
def test_bad_or_future_bars_cannot_match_a_quote(foundation, change):
    _ingest(foundation)
    with pytest.raises(ValueError):
        market_value_diagnostics(_read(foundation), (_bar(**change),))


def test_request_clock_and_snapshot_cutoffs_are_fail_closed(foundation):
    with pytest.raises(ValueError):
        _adapter(clock=NOW - timedelta(seconds=1)).fetch(_request())
    _ingest(foundation)
    with pytest.raises(ValueError):
        replace(_read(foundation), as_of=NOW - timedelta(microseconds=1))
    snapshot = MarketValueInputSnapshot("002624", Market.CHINA_A, CUTOFF, ())
    assert market_value_diagnostics(snapshot)["status"] == "missing"


def test_mutating_consumed_quote_payload_cannot_preserve_a_source_binding(foundation):
    _ingest(foundation)
    snapshot = _read(foundation)
    snapshot.inspections[0].record.payload["total_market_value"] = "999"
    with pytest.raises(ValueError, match="receipt mismatch"):
        market_value_diagnostics(snapshot)


@pytest.mark.parametrize("change", [
    {"open": Decimal("19.5")}, {"volume": Decimal("101")}, {"high": Decimal("22")},
    {"source": "Another synthetic source"}, {"available_at": QUOTE + timedelta(seconds=1)},
])
def test_matching_identity_binds_actual_consumed_bars_even_when_price_and_date_match(
    foundation, change,
):
    _ingest(foundation)
    snapshot = _read(foundation)
    original = market_value_diagnostics(snapshot, (_bar(),))
    changed = market_value_diagnostics(snapshot, (_bar(**change),))
    assert original["quote_bar_date_match"] is changed["quote_bar_date_match"] is True
    assert original["quote_bar_price_match"] is changed["quote_bar_price_match"] is True
    assert original["bar_input_hash"] != changed["bar_input_hash"]
    assert original["diagnostic_hash"] != changed["diagnostic_hash"]


def test_freshness_limits_are_explicit_exact_and_never_scoring_authority(foundation):
    _ingest(foundation)
    snapshot = _read(foundation)
    policy = MarketValueMatchingPolicy(3660, 60, 3660)
    result = market_value_diagnostics(snapshot, (_bar(),), policy)
    assert result["freshness"] == "WITHIN_CONFIGURED_LIMIT"
    assert result["quote_age_microseconds"] == result["bar_age_microseconds"] == 3660000000
    assert result["capture_age_microseconds"] == 60000000
    assert result["matching_policy_hash"] == policy.policy_hash
    assert result["valuation_multiple"] is None and not result["valuation_authorized"]
    late = replace(snapshot, as_of=CUTOFF + timedelta(microseconds=1))
    assert market_value_diagnostics(late, (_bar(),), policy)["freshness"] == "STALE"
    unconfigured = market_value_diagnostics(snapshot, (_bar(),))
    assert unconfigured["freshness"] == "UNASSESSED"
    assert unconfigured["matching_policy_hash"] != result["matching_policy_hash"]


@pytest.mark.parametrize("field", ["max_quote_age_seconds", "max_capture_age_seconds",
                                   "max_bar_age_seconds"])
@pytest.mark.parametrize("value", [0, -1, True, 1.5, "60"])
def test_freshness_cannot_treat_invalid_values_as_infinite_or_disabled(field, value):
    with pytest.raises(ValueError):
        MarketValueMatchingPolicy(**{field: value})


def test_suspension_of_latest_bar_does_not_match_an_older_favorable_close(foundation):
    _ingest(foundation)
    bars = (_bar(timestamp=QUOTE - timedelta(days=1)), _bar(),
            _bar(available_at=QUOTE + timedelta(minutes=1), is_suspended=True))
    result = market_value_diagnostics(
        _read(foundation), bars, MarketValueMatchingPolicy(4000, 60, 4000))
    assert result["bar_status"] == "SUSPENDED_LATEST"
    assert result["quote_bar_price_match"] is result["quote_bar_date_match"] is None
    assert result["bar_freshness"] == result["freshness"] == "UNAVAILABLE"


def test_invalid_bars_cannot_hide_behind_an_unavailable_quote(foundation):
    _ingest(foundation, QuoteHttpCapture(502, b"gateway"))
    with pytest.raises(ValueError):
        market_value_diagnostics(_read(foundation), (_bar(adjustment=Adjustment.FORWARD),))


def test_bar_order_and_timezone_spelling_do_not_change_matching_identity(foundation):
    _ingest(foundation)
    snapshot = _read(foundation)
    bars = (_bar(timestamp=QUOTE - timedelta(days=1)), _bar())
    first = market_value_diagnostics(snapshot, bars)
    assert first == market_value_diagnostics(snapshot, tuple(reversed(bars)))
    zoned = replace(snapshot, as_of=snapshot.as_of.astimezone(ZoneInfo("Asia/Shanghai")))
    assert first["diagnostic_hash"] == market_value_diagnostics(zoned, bars)["diagnostic_hash"]


def test_research_context_binding_uses_actual_cutoff_and_rejects_stale_receipts(foundation):
    _ingest(foundation)
    snapshot = _read(foundation)
    snapshot.validate_context(symbol="002624", market=Market.CHINA_A,
                              as_of=CUTOFF.astimezone(ZoneInfo("Asia/Shanghai")))
    with pytest.raises(ValueError):
        snapshot.validate_context(symbol="002624", market=Market.CHINA_A,
                                  as_of=CUTOFF + timedelta(seconds=1))
    with pytest.raises(ValueError):
        snapshot.validate_context(symbol="000063", market=Market.CHINA_A, as_of=CUTOFF)


def test_capture_cli_prefetches_before_cutoff_without_weakening_strict_ingestion(
    foundation, monkeypatch, capsys,
):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    import capture_market_value as script

    store, artifacts = foundation

    class Clock:
        tick = 0

        @classmethod
        def now(cls, zone):
            cls.tick += 1
            return NOW + timedelta(seconds=cls.tick)

    def service(store, *, artifact_store):
        return ProviderNeutralIngestionService(
            store, artifact_store=artifact_store, clock=lambda: NOW + timedelta(seconds=1))

    monkeypatch.setattr(script, "datetime", Clock)
    monkeypatch.setattr(script, "download_quote", lambda _: QuoteHttpCapture(302, b"redirect"))
    monkeypatch.setattr(script, "ProviderNeutralIngestionService", service)
    monkeypatch.setattr(sys, "argv", ["capture", "--symbol", "002624", "--database",
                                     str(store.path), "--artifact-root", str(artifacts.root)])
    with pytest.raises(SystemExit) as error:
        script.main()
    assert error.value.code == 2
    body = json.loads(capsys.readouterr().out)
    assert body["source_bound"] and body["status"] == "unavailable"
    assert body["reasons"] == ["HTTP_302"]
    assert store.table_count("provider_evidence_records") == 1


def test_combined_cli_reads_market_value_receipts_deterministically_without_database_write(
    foundation,
):
    store, artifacts = foundation
    _ingest(foundation)
    args = [sys.executable, "scripts/inspect_candidate_inputs.py", "--database", str(store.path),
            "--artifact-root", str(artifacts.root), "--symbol", "002624", "--metrics", "revenue",
            "--sector-profile", "nonfinancial", "--as-of", CUTOFF.isoformat()]
    before = store.path.read_bytes()
    first = subprocess.run(args, capture_output=True, text=True, check=False)
    second = subprocess.run(args, capture_output=True, text=True, check=False)
    assert first.returncode == second.returncode == 2, first.stderr
    assert first.stdout == second.stdout and store.path.read_bytes() == before
    body = json.loads(first.stdout)
    assert body["market_value_inputs"]["inspections"][0]["source_bound"]
    assert body["market_value_diagnostics"]["status"] == "observed_unqualified"
    assert body["market_value_diagnostics"]["valuation_multiple"] is None
    assert not body["research_report_created"] and not body["investment_scoring_authorized"]
