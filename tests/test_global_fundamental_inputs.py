"""Native annual evidence remains unqualified even when all seven fields exist."""

import json
import subprocess
import sys
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from urllib.error import HTTPError
from zoneinfo import ZoneInfo

import pytest

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.global_fundamental_inputs import read_global_fundamental_inputs
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.native_financial_inputs import (
    NativeFinancialResearchInput,
    read_native_financial_research_input,
)
from tong_quant.data.providers import yahoo_fundamentals as provider
from tong_quant.data.providers.contracts import ProviderDatasetRequest, provider_evidence_id
from tong_quant.data.providers.yahoo_fundamentals import (
    DATASET,
    MAX_BYTES,
    NATIVE_METRICS,
    YahooFundamentalCapture,
    YahooFundamentalSnapshotAdapter,
    download_fundamentals,
    native_fundamentals,
)
from tong_quant.data.providers.yahoo_snapshot import (
    DATASET as PRICE_DATASET,
)
from tong_quant.data.providers.yahoo_snapshot import (
    YahooGlobalSnapshotAdapter,
    YahooSnapshotCapture,
)
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.research.financial.native_review import review_native_financials

NOW = datetime(2026, 10, 27, 10, tzinfo=UTC)
SCOPES = [(Market.US, "MSFT", "USD"), (Market.HONG_KONG, "0700.HK", "CNY"),
          (Market.MALAYSIA, "1155.KL", "MYR")]


def _request(scope=SCOPES[0], at=NOW):
    return ProviderDatasetRequest(DATASET, scope[0], scope[1], at,
                                  {"start_date": "2020-01-01", "end_date": "2026-10-26"})


def _capture(scope=SCOPES[0]):
    return YahooFundamentalCapture({"timeseries": {"error": None, "result": [
        {"meta": {"symbol": [scope[1]], "type": [metric]},
         "timestamp": [1719705600, 1751241600],
         metric: [{"asOfDate": f"{year}-06-30", "periodType": "12M", "currencyCode": scope[2],
                   "reportedValue": {"raw": value, "fmt": "999.99B"}}
                  for year, value in ((2024, 1000000), (2025, 1200000))]}
        for metric in NATIVE_METRICS]}})


@pytest.fixture
def foundation(tmp_path):
    store = SQLiteStore(tmp_path / "native.sqlite3")
    store.initialize()
    return store, FileSystemArtifactStore(tmp_path / "artifacts")


def _ingest(foundation, capture=None, *, scope=SCOPES[0], at=NOW, completed=None):
    store, artifacts = foundation
    return ProviderNeutralIngestionService(store, artifact_store=artifacts,
        clock=lambda: completed or at).ingest(YahooFundamentalSnapshotAdapter(
            download=lambda _: capture or _capture(scope), clock=lambda: at), _request(scope, at))


def _read(foundation, scope=SCOPES[0], at=NOW):
    return read_global_fundamental_inputs(*foundation, scope[1], scope[0], as_of=at)


def _native_clock_footprint(foundation):
    store, artifacts = foundation
    paths = [store.path]
    wal = store.path.with_name(store.path.name + "-wal")
    if wal.exists():
        paths.append(wal)
    paths += [path for path in artifacts.root.rglob("*") if path.is_file()]
    return {path: sha256(path.read_bytes()).hexdigest() for path in paths}


@pytest.mark.parametrize("scope", SCOPES)
@pytest.mark.parametrize("clock_label", ("naive", "malaysia", "ny_first", "ny_second"))
@pytest.mark.parametrize("failed", (False, True))
def test_native_invalid_capture_clock_rejects_before_retention(
    foundation, scope, clock_label, failed,
):
    captured = datetime(2026, 11, 1, 1, 30)
    if clock_label == "malaysia":
        captured = captured.replace(tzinfo=ZoneInfo("Asia/Kuala_Lumpur"))
    elif clock_label.startswith("ny"):
        captured = captured.replace(tzinfo=ZoneInfo("America/New_York"),
                                    fold=int(clock_label.endswith("second")))
    capture = YahooFundamentalCapture(None, "network_unavailable") if failed else _capture(scope)
    downloads = []

    def download(request):
        downloads.append(request)
        return capture

    store, artifacts = foundation
    request = _request(scope)
    before = _native_clock_footprint(foundation)
    with pytest.raises(ValueError, match="timezone|capture clock must use UTC"):
        ProviderNeutralIngestionService(store, artifact_store=artifacts, clock=lambda: NOW).ingest(
            YahooFundamentalSnapshotAdapter(download=download, clock=lambda: captured), request)
    assert downloads == [request]  # Capture-clock validation occurs after download.
    assert _native_clock_footprint(foundation) == before and not artifacts.root.exists()
    for table in ("ingestion_batches", "provider_artifacts", "provider_evidence_records",
                  "raw_dataset_fingerprints", "provider_limitations"):
        assert store.table_count(table) == 0


@pytest.mark.parametrize("scope", SCOPES)
@pytest.mark.parametrize("zone", ("UTC", "Etc/GMT", "Europe/London"))
@pytest.mark.parametrize("failed", (False, True))
def test_native_zero_offset_clocks_preserve_bytes_ids_and_readback(
    foundation, scope, zone, failed,
):
    capture = YahooFundamentalCapture(None, "network_unavailable") if failed else _capture(scope)
    labelled = NOW.astimezone(ZoneInfo(zone))
    canonical = YahooFundamentalSnapshotAdapter(
        download=lambda _: capture, clock=lambda: NOW).fetch(_request(scope))
    actual = YahooFundamentalSnapshotAdapter(
        download=lambda _: capture, clock=lambda: labelled).fetch(_request(scope, labelled))
    assert actual == canonical
    assert actual.artifacts[0].content == canonical.artifacts[0].content
    assert actual.records[0].evidence_id == canonical.records[0].evidence_id
    _ingest(foundation, capture, scope=scope, at=labelled)
    result = _read(foundation, scope)
    assert result["source_bound"] is True
    assert result["status"] == ("network_unavailable" if failed else "observed_unqualified")
    assert len(result["observations"]) == (0 if failed else 14)
    assert result["trust_ceiling"] == "LOW" and result["availability_precision"] == "retrieval_time"
    assert not result["accounting_definitions_admitted"]
    assert not result["historical_replay_eligible"] and not result["financial_scoring_authorized"]
    assert not result["execution_authorized"]


@pytest.mark.parametrize("scope", SCOPES)
@pytest.mark.parametrize("zone", ("Asia/Kuala_Lumpur", "America/New_York"))
def test_native_non_utc_request_and_read_cutoffs_remain_supported(foundation, scope, zone):
    labelled = NOW.astimezone(ZoneInfo(zone))
    store, artifacts = foundation
    ProviderNeutralIngestionService(store, artifact_store=artifacts, clock=lambda: NOW).ingest(
        YahooFundamentalSnapshotAdapter(download=lambda _: _capture(scope), clock=lambda: NOW),
        _request(scope, labelled))
    canonical = _read(foundation, scope)
    same = _read(foundation, scope, labelled)
    assert same["input_hash"] == canonical["input_hash"]
    assert financial_input_json(same) == financial_input_json(canonical)
    assert same["source_bound"] and same["status"] == "observed_unqualified"


@pytest.mark.parametrize("scope", SCOPES)
@pytest.mark.parametrize("zone", ("Asia/Kuala_Lumpur", "America/New_York"))
@pytest.mark.parametrize("utc_hour", (0, 20))
def test_native_offset_cutoffs_preserve_utc_visibility_across_local_dates(
    foundation, scope, zone, utc_hour,
):
    captured = datetime(2026, 11, 1, utc_hour, 30, tzinfo=UTC)
    labelled = captured.astimezone(ZoneInfo(zone))
    early = (captured - timedelta(microseconds=1)).astimezone(ZoneInfo(zone))
    crosses_date = (zone == "America/New_York" and utc_hour == 0) or (
        zone == "Asia/Kuala_Lumpur" and utc_hour == 20)
    assert (labelled.date() != captured.date()) is crosses_date
    store, artifacts = foundation
    before = _native_clock_footprint(foundation)
    adapter = YahooFundamentalSnapshotAdapter(download=lambda _: _capture(scope),
                                               clock=lambda: captured)
    with pytest.raises(ValueError, match="future event"):
        ProviderNeutralIngestionService(store, artifact_store=artifacts,
            clock=lambda: captured).ingest(adapter, _request(scope, early))
    assert _native_clock_footprint(foundation) == before and not artifacts.root.exists()
    for table in ("ingestion_batches", "provider_artifacts", "provider_evidence_records",
                  "raw_dataset_fingerprints", "provider_limitations"):
        assert store.table_count(table) == 0
    ProviderNeutralIngestionService(store, artifact_store=artifacts,
        clock=lambda: captured).ingest(adapter, _request(scope, labelled))
    pinned = _native_clock_footprint(foundation)
    missing = _read(foundation, scope, early)
    assert missing["status"] == "missing" and missing["captures"] == []
    assert not missing["source_bound"] and missing["observations"] == []
    local_result = _read(foundation, scope, labelled)
    utc_result = _read(foundation, scope, captured)
    assert local_result["source_bound"] and local_result["status"] == "observed_unqualified"
    assert financial_input_json(local_result) == financial_input_json(utc_result)
    assert _native_clock_footprint(foundation) == pinned


@pytest.mark.parametrize("scope", SCOPES)
@pytest.mark.parametrize("predecessor", (False, True))
def test_native_legacy_offset_identity_remains_blocked_without_old_good_fallback(
    foundation, scope, predecessor,
):
    if predecessor:
        _ingest(foundation, scope=scope)
    later = NOW + timedelta(seconds=1)
    labelled = later.astimezone(ZoneInfo("Asia/Kuala_Lumpur"))
    canonical = YahooFundamentalSnapshotAdapter(download=lambda _: _capture(scope),
        clock=lambda: later).fetch(_request(scope, later))
    original = canonical.records[0]
    record = replace(original, available_at=labelled, retrieved_at=labelled,
        evidence_id=provider_evidence_id(provider=original.provider, dataset=original.dataset,
            market=original.market, subject=original.subject, available_at=labelled,
            source_reference=original.source_reference, payload=original.payload))
    legacy = replace(canonical, retrieved_at=labelled, records=(record,), artifacts=(replace(
        canonical.artifacts[0], published_at=labelled, retrieved_at=labelled),))

    class LegacyFixtureAdapter:
        provider_id = canonical.provider

        def capabilities(self):
            return YahooFundamentalSnapshotAdapter().capabilities()

        def fetch(self, request):
            return legacy

    # Test-only representation of an old offset identity, not a production bypass.
    store, artifacts = foundation
    ProviderNeutralIngestionService(store, artifact_store=artifacts, clock=lambda: later).ingest(
        LegacyFixtureAdapter(), _request(scope, labelled))
    before = _native_clock_footprint(foundation)
    result = _read(foundation, scope, later)
    assert result["status"] == "rejected_or_ambiguous" and not result["source_bound"]
    assert result["observations"] == [] and result["latest"] == {}
    assert len(result["captures"]) == 1 + int(predecessor)
    assert result["captures"][-1]["evidence_id"] == record.evidence_id
    assert not result["financial_scoring_authorized"] and not result["execution_authorized"]
    assert _native_clock_footprint(foundation) == before
    assert store.table_count("provider_evidence_records") == 1 + int(predecessor)
    if predecessor:
        assert _read(foundation, scope)["status"] == "observed_unqualified"


@pytest.mark.parametrize("scope", SCOPES)
@pytest.mark.parametrize("failed", (False, True))
def test_native_bad_capture_cannot_replace_or_freshen_retained_evidence(foundation, scope, failed):
    _ingest(foundation, scope=scope)
    original = _read(foundation, scope)
    before = _native_clock_footprint(foundation)
    later = NOW + timedelta(seconds=1)
    capture = YahooFundamentalCapture(None, "network_unavailable") if failed else _capture(scope)
    with pytest.raises(ValueError, match="capture clock must use UTC"):
        _ingest(foundation, capture, scope=scope,
                at=later.astimezone(ZoneInfo("Asia/Kuala_Lumpur")))
    assert _native_clock_footprint(foundation) == before
    after = _read(foundation, scope, later)
    assert after["selected_evidence_id"] == original["selected_evidence_id"]
    assert after["captures"] == original["captures"]
    assert after["observations"] == original["observations"]
    assert after["freshness"] == "UNASSESSED"
    assert foundation[0].table_count("ingestion_batches") == 1
    assert foundation[0].table_count("fundamental_facts") == 0


@pytest.mark.parametrize("scope", SCOPES)
@pytest.mark.parametrize("profile", ["nonfinancial", "bank", "securities", "insurance", "unknown"])
def test_native_research_binding_copies_mutable_documents(foundation, scope, profile):
    _ingest(foundation, scope=scope)
    before = foundation[0].path.read_bytes()
    bound = read_native_financial_research_input(*foundation, scope[1], scope[0],
                                                as_of=NOW, sector_profile=profile)
    assert bound.document()["input_hash"] == _read(foundation, scope)["input_hash"]
    document = bound.document()
    document["observations"][0]["value"] = "999999999"
    assert bound.document() != document
    bound.validate_context(symbol=scope[1], market=scope[0],
                           as_of=NOW.astimezone(ZoneInfo("Asia/Kuala_Lumpur")))
    assert foundation[0].path.read_bytes() == before


@pytest.mark.parametrize("defect", ["checksum", "scoring", "replay", "trust", "precision",
    "future_capture", "future_row", "naive_capture", "sector", "secret", "version"])
def test_native_research_binding_rejects_integrity_authority_and_clock_defects(foundation, defect):
    _ingest(foundation)
    document = _read(foundation)
    profile = "nonfinancial"
    if defect == "checksum":
        document["status"] = "forged"
    elif defect in {"scoring", "replay"}:
        document[{"scoring": "financial_scoring_authorized",
                  "replay": "historical_replay_eligible"}[defect]] = True
    elif defect == "trust":
        document["trust_ceiling"] = "VERIFIED"
    elif defect == "precision":
        document["availability_precision"] = "exact"
    elif defect in {"future_capture", "future_row", "naive_capture"}:
        collection = "observations" if defect == "future_row" else "captures"
        document[collection][0]["available_at"] = (
            NOW.replace(tzinfo=None).isoformat() if defect == "naive_capture"
            else (NOW + timedelta(microseconds=1)).isoformat())
    elif defect == "sector":
        profile = "all_sectors_admitted"
    elif defect == "secret":
        document["api_key"] = "synthetic-prohibited-value"
    else:
        document["model_version"] = "unknown"
    if defect != "checksum":
        document.pop("input_hash")
        document["input_hash"] = sha256(financial_input_json(document).encode()).hexdigest()
    with pytest.raises(ValueError):
        NativeFinancialResearchInput(financial_input_json(document), profile)


@pytest.mark.parametrize("defect", ["symbol", "market", "cutoff", "naive_cutoff"])
def test_native_research_binding_requires_exact_context(foundation, defect):
    _ingest(foundation)
    bound = read_native_financial_research_input(*foundation, "MSFT", Market.US,
                                                as_of=NOW, sector_profile="nonfinancial")
    values = dict(symbol="MSFT", market=Market.US, as_of=NOW)
    values.update({"symbol": {"symbol": "AAPL"}, "market": {"market": Market.HONG_KONG},
        "cutoff": {"as_of": NOW + timedelta(seconds=1)},
        "naive_cutoff": {"as_of": NOW.replace(tzinfo=None)}}[defect])
    with pytest.raises(ValueError):
        bound.validate_context(**values)


@pytest.mark.parametrize("scope", SCOPES)
def test_native_financials_are_bound_current_observations_not_canonical_facts(foundation, scope):
    _ingest(foundation, scope=scope)
    before = foundation[0].path.read_bytes()
    result = _read(foundation, scope)
    assert result["status"] == "observed_unqualified" and result["source_bound"]
    assert len(result["observations"]) == 14
    assert result["reporting_currencies"] == [scope[2]]
    assert result["latest"]["annualNetIncome"]["value"] == "1200000"
    assert result["latest"]["annualNetIncome"]["period_end"] == "2025-06-30"
    for row in result["observations"]:
        assert row["published_at"] is row["issuer_revision"] is row["period_start"] is None
        assert row["accounting_scope"] == "UNVERIFIED"
        assert row["available_at"] == NOW.isoformat()
    assert result["freshness"] == "UNASSESSED"
    for name in ("financial_scoring_authorized", "historical_replay_eligible",
                 "investment_scoring_authorized", "validation_authorized", "execution_authorized"):
        assert result[name] is False
    assert _read(foundation, scope, NOW - timedelta(microseconds=1))["status"] == "missing"
    assert _read(foundation, scope)["input_hash"] == result["input_hash"]
    assert foundation[0].path.read_bytes() == before
    for table in ("fundamental_facts", "instruments", "research_reports", "signals"):
        assert foundation[0].table_count(table) == 0


def test_retry_preserves_snapshot_identity_and_equivalent_utc_cutoffs(foundation):
    _ingest(foundation)
    _ingest(foundation)
    local = NOW.astimezone(ZoneInfo("Asia/Kuala_Lumpur"))
    assert _read(foundation, at=local)["input_hash"] == _read(foundation)["input_hash"]
    assert foundation[0].table_count("provider_evidence_records") == 1
    assert foundation[0].table_count("provider_artifacts") == 1


@pytest.mark.parametrize("defect", ["boolean", "text", "null", "period_type", "currency",
    "future_period", "bad_date", "duplicate", "wrong_symbol", "duplicate_group"])
def test_bad_latest_native_rows_never_select_an_older_favorable_value(defect):
    payload = deepcopy(_capture().payload)
    groups = payload["timeseries"]["result"]
    metric = NATIVE_METRICS[0]
    row = groups[0][metric][-1]
    if defect in {"boolean", "text", "null"}:
        row["reportedValue"]["raw"] = {"boolean": True, "text": "1200000", "null": None}[defect]
    elif defect == "period_type":
        row["periodType"] = "3M"
    elif defect == "currency":
        row["currencyCode"] = "unknown"
    elif defect == "future_period":
        row["asOfDate"] = "2027-06-30"
    elif defect == "bad_date":
        row["asOfDate"] = "not a date"
    elif defect == "duplicate":
        groups[0][metric].append(deepcopy(row))
    elif defect == "wrong_symbol":
        groups[0]["meta"]["symbol"] = ["OTHER"]
    else:
        groups.append(deepcopy(groups[0]))
    result = native_fundamentals(YahooFundamentalCapture(payload), _request(), NOW)
    assert result["status"] in {"partial_unqualified", "invalid_response"}
    if result["latest"]:
        assert result["latest"][metric]["value"] is None
        assert result["latest"][metric]["status"] != "OBSERVED_UNQUALIFIED"


@pytest.mark.parametrize("value", [0, -1200000])
def test_zero_and_negative_native_values_are_preserved_without_financial_interpretation(value):
    payload = deepcopy(_capture().payload)
    payload["timeseries"]["result"][1]["annualNetIncome"][-1]["reportedValue"]["raw"] = value
    result = native_fundamentals(YahooFundamentalCapture(payload), _request(), NOW)
    assert result["latest"]["annualNetIncome"]["value"] == str(value)
    assert result["financial_scoring_authorized"] is False


@pytest.mark.parametrize("count", [0, 1, 6])
def test_unavailable_metrics_and_empty_results_are_not_zero_or_complete(count):
    payload = deepcopy(_capture().payload)
    payload["timeseries"]["result"] = payload["timeseries"]["result"][:count]
    result = native_fundamentals(YahooFundamentalCapture(payload), _request(), NOW)
    assert len(result["missing_metrics"]) == 7 - count
    assert result["status"] == ("no_observations" if count == 0 else "partial_unqualified")


def test_all_bad_latest_values_are_visible_as_insufficient_not_partial_success():
    payload = deepcopy(_capture().payload)
    for group in payload["timeseries"]["result"]:
        group[group["meta"]["type"][0]][-1]["reportedValue"]["raw"] = None
    result = native_fundamentals(YahooFundamentalCapture(payload), _request(), NOW)
    assert result["status"] == "insufficient_native_data"
    assert result["usable_native_metric_count"] == 0
    assert len(result["observations"]) == 14
    assert result["financial_scoring_authorized"] is False


@pytest.mark.parametrize("kind", ["payload", "bytes", "registry", "batch_hash", "batch_status",
                                  "batch_parameters", "batch_time", "batch_naive"])
def test_native_snapshot_binding_rejects_corruption_and_future_ingestion(foundation, kind):
    ingestion = _ingest(foundation)
    store, artifacts = foundation
    digest = _read(foundation)["captures"][0]["raw_data_hash"]
    with store._connect() as connection:
        if kind == "payload":
            connection.execute("UPDATE provider_evidence_records SET payload_json='{}'")
        elif kind == "registry":
            connection.execute("UPDATE provider_artifacts SET source_identity='synthetic tamper'")
        elif kind.startswith("batch_"):
            column, value = {"batch_hash": ("raw_response_hash", "a" * 64),
                "batch_status": ("status", "failed"), "batch_parameters": ("parameters_json", "{}"),
                "batch_time": ("completed_at", (NOW + timedelta(seconds=1)).isoformat()),
                "batch_naive": ("completed_at", NOW.astimezone().replace(
                    tzinfo=None).isoformat())}[kind]
            connection.execute(f"UPDATE ingestion_batches SET {column}=? WHERE batch_id=?",
                               (value, ingestion.batch_id))
    if kind == "bytes":
        (artifacts.root / "sha256" / digest[:2] / f"{digest}.bin").write_bytes(b"synthetic tamper")
    result = _read(foundation)
    assert result["status"] == "rejected_or_ambiguous" and not result["source_bound"]
    assert not result["observations"] and not result["latest"]


def test_latest_failure_and_equal_time_captures_do_not_use_old_financials(foundation):
    _ingest(foundation)
    at = NOW + timedelta(seconds=1)
    _ingest(foundation, YahooFundamentalCapture(None, "http_403"), at=at)
    assert _read(foundation, at=at)["status"] == "http_403"
    assert _read(foundation, at=at)["observations"] == []
    _ingest(foundation, at=at)
    assert _read(foundation, at=at)["status"] == "rejected_or_ambiguous"


def test_incomplete_batches_do_not_become_visible_financial_data(foundation):
    _ingest(foundation, completed=NOW + timedelta(seconds=1))
    assert not _read(foundation)["source_bound"]
    assert _read(foundation, at=NOW + timedelta(seconds=1))["source_bound"]


@pytest.mark.parametrize("key", ["token", "api_key", "secret", "password", "webhook_url"])
def test_native_credential_fields_are_rejected_before_encoding(key):
    with pytest.raises(ValueError, match="credential"):
        YahooFundamentalCapture({key: "synthetic fixture only"})


@pytest.mark.parametrize("payload", [[], {"x": float("nan")}, {"x": float("inf")},
                                    {"x": "x" * MAX_BYTES}])
def test_invalid_and_unbounded_native_captures_are_rejected(payload):
    with pytest.raises(ValueError):
        YahooFundamentalCapture(payload)


@pytest.mark.parametrize("code", [401, 403, 404])
def test_http_permissions_and_missing_endpoint_have_sanitized_failure_codes(monkeypatch, code):
    calls = []

    def fail(*args, **kwargs):
        calls.append(True)
        raise HTTPError("https://example.test", code, "synthetic detail must not be persisted",
                        None, None)

    monkeypatch.setattr(provider, "urlopen", fail)
    result = download_fundamentals(_request())
    assert result.payload is None and result.error_code == f"http_{code}"
    assert len(calls) == 1


def test_capture_cannot_be_backdated_to_make_annual_facts_visible(foundation):
    store, artifacts = foundation
    adapter = YahooFundamentalSnapshotAdapter(download=lambda _: _capture(), clock=lambda: NOW)
    with pytest.raises(ValueError, match="future event"):
        ProviderNeutralIngestionService(store, artifact_store=artifacts, clock=lambda: NOW).ingest(
            adapter, _request(at=NOW - timedelta(seconds=1)))
    assert store.table_count("provider_evidence_records") == 0


@pytest.mark.parametrize("profile", ["nonfinancial", "bank", "securities", "insurance", "unknown"])
def test_combined_cli_uses_one_cutoff_without_admitting_any_sector_policy(foundation, profile):
    _ingest(foundation, scope=SCOPES[1])
    store, artifacts = foundation
    args = [sys.executable, "scripts/inspect_global_technical.py", "--market", "hong_kong",
        "--symbol", "0700.HK", "--database", str(store.path),
        "--artifact-root", str(artifacts.root),
        "--as-of", NOW.isoformat(), "--fundamentals", "--sector-profile", profile]
    before = store.path.read_bytes()
    first = subprocess.run(args, capture_output=True, text=True, check=False)
    second = subprocess.run(args, capture_output=True, text=True, check=False)
    assert first.returncode == second.returncode == 2, first.stderr
    assert first.stdout == second.stdout and store.path.read_bytes() == before
    result = json.loads(first.stdout)
    assert result["fundamentals"]["reporting_currencies"] == ["CNY"]
    assert result["fundamentals"]["as_of"] == result["inputs"]["as_of"]
    assert result["sector_policy_status"] == "NOT_ADMITTED"
    assert result["requested_sector_profile"] == profile
    assert result["financial_review"]["requested_sector_profile"] == profile
    assert result["financial_review"]["financial_condition_state"] == "EVIDENCE_INSUFFICIENT"
    assert not result["financial_review"]["investment_scoring_authorized"]
    assert result["valuation_authorized"] is False
    assert not result["research_report_created"] and not result["readiness_promoted"]


def test_hkd_quotes_and_cny_native_statements_remain_separate_without_fx(foundation):
    _ingest(foundation, scope=SCOPES[1])
    store, artifacts = foundation
    capture = YahooSnapshotCapture({"chart": {"error": None, "result": [{
        "meta": {"symbol": "0700.HK", "currency": "HKD", "exchangeName": "HKG",
            "exchangeTimezoneName": "Asia/Hong_Kong", "instrumentType": "EQUITY",
            "dataGranularity": "1d"},
        "timestamp": [int(datetime(2026, 10, 23, 1, 30, tzinfo=UTC).timestamp())],
        "indicators": {"quote": [{"open": [15], "high": [16], "low": [14],
                                   "close": [15], "volume": [1000]}]},
    }]}})
    ProviderNeutralIngestionService(store, artifact_store=artifacts, clock=lambda: NOW).ingest(
        YahooGlobalSnapshotAdapter(download=lambda _: capture, clock=lambda: NOW),
        ProviderDatasetRequest(PRICE_DATASET, Market.HONG_KONG, "0700.HK", NOW, {
            "start_date": "2026-10-01", "end_date": "2026-10-26", "currency": "HKD",
            "exchange": "HKG", "timezone": "Asia/Hong_Kong"}))
    result = subprocess.run([sys.executable, "scripts/inspect_global_technical.py",
        "--market", "hong_kong", "--symbol", "0700.HK", "--database", str(store.path),
        "--artifact-root", str(artifacts.root), "--as-of", NOW.isoformat(),
        "--fundamentals", "--sector-profile", "nonfinancial"],
        capture_output=True, text=True, check=False)
    assert result.returncode == 2, result.stderr
    output = json.loads(result.stdout)
    assert output["quote_currency"] == "HKD"
    assert output["currency_alignment"] == "DIFFERENT_CURRENCIES_NO_FX"
    assert output["valuation_authorized"] is False


def _review(snapshot, *, profile="nonfinancial", scope=SCOPES[0], at=NOW):
    return review_native_financials(snapshot, subject=scope[1], market=scope[0], as_of=at,
                                    sector_profile=profile)


def _rehash(document):
    body = {key: value for key, value in document.items() if key != "input_hash"}
    return {**body, "input_hash": sha256(financial_input_json(body).encode()).hexdigest()}


@pytest.mark.parametrize("scope", SCOPES)
def test_native_review_shows_amount_changes_without_promoting_financial_research(foundation, scope):
    _ingest(foundation, scope=scope)
    before = foundation[0].path.read_bytes()
    snapshot = _read(foundation, scope)
    result = _review(snapshot, scope=scope)
    assert result["status"] == "EXPLORATORY_REVIEW" and result["receipt_integrity_valid"]
    assert len(result["comparisons"]) == 7
    for comparison in result["comparisons"]:
        assert comparison["status"] == "DESCRIPTIVE_UNQUALIFIED"
        assert comparison["native_amount_change"] == "200000"
        assert comparison["native_change_percent"] == "20.0000"
        assert comparison["currency"] == scope[2]
        assert not comparison["accounting_comparability_verified"]
    assert result["financial_condition_state"] == "EVIDENCE_INSUFFICIENT"
    for name in ("financial_scoring_authorized", "investment_scoring_authorized",
                 "validation_authorized", "historical_replay_eligible", "execution_authorized"):
        assert result[name] is False
    assert _review(snapshot, scope=scope) == result
    local = NOW.astimezone(ZoneInfo("Asia/Kuala_Lumpur"))
    assert _review(snapshot, scope=scope, at=local)["review_hash"] == result["review_hash"]
    assert foundation[0].path.read_bytes() == before


@pytest.mark.parametrize("defect", ["bad_latest", "bad_previous", "duplicate_current",
    "duplicate_previous", "missing_previous", "gap", "fiscal_change", "currency", "unit",
    "unknown_period", "future_period", "boolean", "nan", "tiny"])
def test_native_review_does_not_fill_or_favorably_replace_incompatible_periods(foundation, defect):
    _ingest(foundation)
    snapshot = deepcopy(_read(foundation))
    metric = NATIVE_METRICS[0]
    rows = [row for row in snapshot["observations"] if row["native_metric"] == metric]
    prior, current = rows
    if defect == "bad_latest":
        current.update(status="INVALID_NATIVE_ROW", value=None)
    elif defect == "bad_previous":
        prior.update(status="INVALID_NATIVE_ROW", value=None)
    elif defect in {"duplicate_current", "duplicate_previous"}:
        snapshot["observations"].append(deepcopy(current if defect.endswith("current") else prior))
    elif defect == "missing_previous":
        snapshot["observations"].remove(prior)
    elif defect == "gap":
        prior["period_end"] = "2023-06-30"
    elif defect == "fiscal_change":
        prior["period_end"] = "2024-12-31"
    elif defect == "currency":
        prior["currency"] = "CNY"
    elif defect == "unit":
        prior["unit"] = "million"
    elif defect == "unknown_period":
        current["period_end"] = None
    elif defect == "future_period":
        current["period_end"] = "2027-06-30"
    else:
        current["value"] = {"boolean": True, "nan": "NaN", "tiny": "1e-100"}[defect]
    # A public checksum is not authentication; even a recomputed one cannot qualify data.
    result = _review(_rehash(snapshot))
    comparison = result["comparisons"][0]
    assert comparison["status"] != "DESCRIPTIVE_UNQUALIFIED"
    assert comparison["native_amount_change"] is comparison["native_change_percent"] is None
    assert result["financial_condition_state"] == "EVIDENCE_INSUFFICIENT"


@pytest.mark.parametrize("baseline", ["0", "-1000000"])
def test_native_review_withholds_percentage_on_nonpositive_prior_values(foundation, baseline):
    _ingest(foundation)
    snapshot = deepcopy(_read(foundation))
    snapshot["observations"][0]["value"] = baseline
    result = _review(_rehash(snapshot))["comparisons"][0]
    assert result["status"] == "NONPOSITIVE_BASE"
    assert result["native_amount_change"] == str(1200000 - int(baseline))
    assert result["native_change_percent"] is None


@pytest.mark.parametrize("defect", ["hash", "subject", "market", "cutoff", "naive_cutoff",
    "naive_row", "future_row", "future_capture", "not_bound", "grant", "capture_tie"])
def test_native_review_rejects_mutated_or_wrong_context_receipts(foundation, defect):
    _ingest(foundation)
    snapshot = deepcopy(_read(foundation))
    if defect == "hash":
        snapshot["observations"][0]["value"] = "999"
    elif defect == "subject":
        snapshot["subject"] = "OTHER"
    elif defect == "market":
        snapshot["market"] = "malaysia"
    elif defect == "cutoff":
        snapshot["as_of"] = NOW + timedelta(seconds=1)
    elif defect == "naive_cutoff":
        snapshot["as_of"] = NOW.replace(tzinfo=None).isoformat()
    elif defect == "naive_row":
        snapshot["observations"][0]["available_at"] = NOW.replace(tzinfo=None).isoformat()
    elif defect == "future_row":
        snapshot["observations"][0]["available_at"] = (NOW + timedelta(seconds=1)).isoformat()
    elif defect == "future_capture":
        snapshot["captures"][0]["available_at"] = NOW + timedelta(seconds=1)
    elif defect == "not_bound":
        snapshot["source_bound"] = False
    elif defect == "grant":
        snapshot["financial_scoring_authorized"] = True
    else:
        snapshot["captures"].append(deepcopy(snapshot["captures"][0]))
    if defect != "hash":
        snapshot = _rehash(snapshot)
    result = _review(snapshot)
    assert result["status"] == "INPUT_REJECTED" and not result["receipt_integrity_valid"]
    assert not result["comparisons"] and not result["observations_to_review"]
    assert not result["financial_scoring_authorized"]


@pytest.mark.parametrize("profile", ["nonfinancial", "bank", "securities", "insurance", "unknown"])
def test_sector_questions_never_interpret_negative_bank_cash_flow_as_generic_failure(
    foundation, profile,
):
    _ingest(foundation)
    snapshot = deepcopy(_read(foundation))
    for row in snapshot["observations"]:
        if row["native_metric"] == "annualOperatingCashFlow" and row["period_end"] == "2025-06-30":
            row["value"] = "-1200000"
    result = _review(_rehash(snapshot), profile=profile)
    assert bool(result["observations_to_review"]) is (profile == "nonfinancial")
    assert set(result["value_research_prerequisites"]) == {
        "survival", "cycle", "valuation", "growth"}
    assert all(item["status"] == "UNASSESSED"
               for item in result["value_research_prerequisites"].values())
    assert result["sector_policy_status"] == "NOT_ADMITTED"
    assert result["financial_condition_state"] == "EVIDENCE_INSUFFICIENT"


def test_global_native_review_cannot_apply_its_contract_to_china_or_invent_a_profile(foundation):
    _ingest(foundation)
    snapshot = _read(foundation)
    with pytest.raises(ValueError, match="overseas"):
        _review(snapshot, scope=(Market.CHINA_A, "600000", "CNY"))
    with pytest.raises(ValueError, match="sector"):
        _review(snapshot, profile="fund")
