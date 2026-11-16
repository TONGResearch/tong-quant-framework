"""XBRL units, vintages and exact filing references stay unqualified and PIT-visible."""

import json
import subprocess
import sys
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pytest

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.providers import sec_concept as concept
from tong_quant.data.providers import sec_submissions as sec
from tong_quant.data.providers.contracts import ProviderDatasetRequest
from tong_quant.data.sec_concept_inputs import read_sec_concept_inputs
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market

NOW = datetime(2026, 10, 27, 10, tzinfo=UTC)
CIK, TAXONOMY, TAG = "0000789019", "us-gaap", "Revenues"


def _request(at=NOW):
    return ProviderDatasetRequest(concept.DATASET, Market.US,
                                  concept.concept_subject(CIK, TAXONOMY, TAG), at)


def _payload():
    annual = {"start": "2024-07-01", "end": "2025-06-30", "val": 120,
              "accn": "0001193125-25-123456", "fy": 2025, "fp": "FY", "form": "10-K",
              "filed": "2025-07-30", "frame": "CY2025"}
    previous = {**annual, "start": "2023-07-01", "end": "2024-06-30", "val": 100}
    amended = {**annual, "val": 110, "accn": "0001193125-25-123457",
               "filed": "2025-08-01", "form": "10-K/A"}
    return {"cik": 789019, "taxonomy": TAXONOMY, "tag": TAG, "label": "Synthetic revenues",
            "units": {"USD": [annual, previous, amended]}}


def _catalog():
    return {"cik": 789019, "filings": {"files": [], "recent": {
        "accessionNumber": ["0001193125-25-123456", "0001193125-25-123457"],
        "filingDate": ["2025-07-30", "2025-08-01"],
        "acceptanceDateTime": ["2025-07-30T20:05:12Z", "2025-08-01T20:05:12Z"],
        "reportDate": ["2025-06-30", "2025-06-30"], "form": ["10-K", "10-K/A"],
        "primaryDocument": ["annual.htm", "amendment.htm"]}}}


@pytest.fixture
def foundation(tmp_path):
    store = SQLiteStore(tmp_path / "concept.sqlite3")
    store.initialize()
    return store, FileSystemArtifactStore(tmp_path / "raw")


def _ingest(foundation, capture=None, at=NOW, *, kind="concept", completed=None):
    service = ProviderNeutralIngestionService(*foundation[:1], artifact_store=foundation[1],
                                              clock=lambda: completed or at)
    capture = capture or sec.SECSubmissionsCapture(_payload() if kind == "concept" else _catalog())
    if kind == "concept":
        adapter = concept.SECConceptAdapter(download=lambda _: capture, clock=lambda: at)
        request = _request(at)
    else:
        adapter = sec.SECSubmissionsAdapter(download=lambda _: capture, clock=lambda: at)
        request = ProviderDatasetRequest(sec.DATASET, Market.US, CIK, at)
    return service.ingest(adapter, request)


def _read(foundation, at=NOW):
    return read_sec_concept_inputs(*foundation, CIK, TAXONOMY, TAG, as_of=at)


@pytest.mark.parametrize("cik,taxonomy,tag", [("MSFT", TAXONOMY, TAG),
    ("0000000000", TAXONOMY, TAG), (CIK, "custom", TAG), (CIK, TAXONOMY, "../Revenues"),
    (CIK, TAXONOMY, "Revenues?token=x"), (CIK, TAXONOMY, ""),
    (CIK, TAXONOMY, "x" * 129)])
def test_explicit_composite_identity_has_no_alias_or_url_escape(cik, taxonomy, tag):
    with pytest.raises(ValueError):
        concept.concept_subject(cik, taxonomy, tag)


@pytest.mark.parametrize("changes", [{"market": Market.HONG_KONG},
    {"dataset": "sec_issuer_filings_snapshot"}, {"parameters": {"unit": "USD"}}])
def test_request_scope_cannot_be_silently_changed(changes):
    with pytest.raises(ValueError):
        concept.concept_url(replace(_request(), **changes))


def test_native_periods_units_and_amended_values_are_not_collapsed_or_relabelled():
    payload = _payload()
    payload["units"]["CNY"] = [deepcopy(payload["units"]["USD"][0])]
    result = concept.normalize_concept(sec.SECSubmissionsCapture(payload), _request(), NOW)
    assert result["status"] == "observed_native_unqualified"
    assert result["units"] == ["CNY", "USD"]
    assert len(result["observations"]) == 4
    rows = [row for row in result["observations"] if row["unit"] == "USD"]
    assert [row["value"] for row in rows] == ["120", "100", "110"]
    assert len({row["row_id"] for row in rows}) == 3
    for row in rows:
        assert row["published_at"] is row["numeric_revision"] is None
        assert row["available_at"] == NOW.isoformat()
        assert row["accounting_definition_qualified"] is False
    assert rows[0]["period_start"] == "2024-07-01"
    assert rows[0]["period_shape"] == "duration_label"


@pytest.mark.parametrize("value", [0, -100])
def test_exact_signed_integer_values_remain_visible_without_interpretation(value):
    payload = _payload()
    payload["units"]["USD"][0]["val"] = value
    result = concept.normalize_concept(sec.SECSubmissionsCapture(payload), _request(), NOW)
    assert result["observations"][0]["value"] == str(value)
    assert result["financial_scoring_authorized"] is False


@pytest.mark.parametrize("defect", ["boolean", "text", "float", "oversize_amount", "end",
    "future_period", "start", "accession", "filed", "form", "null"])
def test_bad_native_rows_are_not_hidden_or_replaced_by_other_vintages(defect):
    payload = _payload()
    row = payload["units"]["USD"][2]
    changes = {"boolean": {"val": True}, "text": {"val": "110"}, "float": {"val": 1.1},
        "oversize_amount": {"val": 10**25}, "end": {"end": "invalid"},
        "future_period": {"end": "2027-06-30"}, "start": {"start": "2026-01-01"},
        "accession": {"accn": "bad"}, "filed": {"filed": "unknown"}, "form": {"form": None}}
    if defect == "null":
        payload["units"]["USD"][2] = None
    else:
        row.update(changes[defect])
    result = concept.normalize_concept(sec.SECSubmissionsCapture(payload), _request(), NOW)
    assert len(result["observations"]) == 3
    assert result["status"] == "partial_native"
    assert result["observations"][2]["value"] is None
    assert result["observations"][2]["status"] != "OBSERVED_NATIVE_UNQUALIFIED"


@pytest.mark.parametrize("defect", ["cik", "taxonomy", "tag", "units", "unit_name", "rows"])
def test_wrong_identity_or_structure_never_becomes_a_different_concept(defect):
    payload = _payload()
    if defect in {"cik", "taxonomy", "tag"}:
        payload[defect] = {"cik": 1, "taxonomy": "ifrs-full", "tag": "ProfitLoss"}[defect]
    elif defect == "units":
        payload["units"] = []
    elif defect == "unit_name":
        payload["units"]["https://elsewhere"] = []
    else:
        payload["units"]["USD"] = None
    result = concept.normalize_concept(sec.SECSubmissionsCapture(payload), _request(), NOW)
    assert result["status"] == "invalid_response" and result["observations"] == []


def test_ambiguous_fact_contexts_are_retained_not_ranked_or_averaged():
    payload = _payload()
    payload["units"]["USD"].append({**payload["units"]["USD"][0], "val": 999})
    result = concept.normalize_concept(sec.SECSubmissionsCapture(payload), _request(), NOW)
    assert len(result["observations"]) == 4
    assert result["observations"][0]["status"] == "DUPLICATE_FACT_CONTEXT"
    assert result["observations"][3]["status"] == "DUPLICATE_FACT_CONTEXT"
    assert result["observations"][0]["value"] is None


def test_fiscal_labels_do_not_turn_comparative_or_instant_values_into_annual_growth():
    payload = _payload()
    row = payload["units"]["USD"][0]
    row["fy"] = 2027
    del row["start"]
    result = concept.normalize_concept(sec.SECSubmissionsCapture(payload), _request(), NOW)
    assert result["observations"][0]["native"]["fy"] == 2027
    assert result["observations"][0]["period_shape"] == "instant_label"
    assert result["accounting_definition_qualified"] is False


def test_provider_uses_shared_bounded_transport_and_fixed_url(monkeypatch):
    download = Mock(return_value=sec.SECSubmissionsCapture(_payload()))
    monkeypatch.setattr(concept, "download_sec_json", download)
    concept.download_concept(_request())
    download.assert_called_once_with(
        f"https://data.sec.gov/api/xbrl/companyconcept/CIK{CIK}/{TAXONOMY}/{TAG}.json")
    for url in ("https://example.invalid/data", "https://data.sec.gov/private",
                "https://data.sec.gov/submissions/CIK0000789019.json?token=synthetic"):
        with pytest.raises(ValueError):
            sec.download_sec_json(url)


def test_real_contract_reconstruction_links_same_cutoff_metadata_not_publication(foundation):
    _ingest(foundation, kind="catalog")
    _ingest(foundation)
    _ingest(foundation)
    before = foundation[0].path.read_bytes()
    result = _read(foundation)
    assert result["source_bound"] and result["status"] == "observed_native_unqualified"
    assert result["metadata_reference_match_count"] == 3
    assert [row["period_relation"] for row in result["filing_references"]] == [
        "SAME_END_LABEL", "COMPARATIVE_OR_OTHER_PERIOD", "SAME_END_LABEL"]
    assert all(row["independent_numeric_corroboration"] is False
               for row in result["filing_references"])
    assert result["input_hash"] == _read(foundation)["input_hash"]
    assert result["input_hash"] == _read(
        foundation, NOW.astimezone(ZoneInfo("Asia/Kuala_Lumpur")))["input_hash"]
    assert _read(foundation, NOW - timedelta(microseconds=1))["status"] == "missing"
    assert foundation[0].path.read_bytes() == before
    assert foundation[0].table_count("provider_evidence_records") == 2
    for table in ("fundamental_facts", "daily_bars", "research_reports", "signals"):
        assert foundation[0].table_count(table) == 0


@pytest.mark.parametrize("defect", ["missing", "future_catalog", "failed", "form", "filed",
                                   "duplicate", "unusable"])
def test_catalog_problems_never_make_a_successful_reference_match(foundation, defect):
    _ingest(foundation)
    payload = _catalog()
    at = NOW
    if defect in {"form", "filed"}:
        payload["filings"]["recent"][{"form": "form", "filed": "filingDate"}[defect]][0] = (
            "8-K" if defect == "form" else "2025-07-31")
    elif defect == "duplicate":
        for values in payload["filings"]["recent"].values():
            values.append(values[0])
    elif defect == "unusable":
        payload["filings"]["recent"]["acceptanceDateTime"][0] = "2025-07-30T20:05:12"
    elif defect == "future_catalog":
        at += timedelta(seconds=1)
    capture = (sec.SECSubmissionsCapture(None, "http_403") if defect == "failed"
               else sec.SECSubmissionsCapture(payload))
    if defect != "missing":
        _ingest(foundation, capture, at=at, kind="catalog")
    result = _read(foundation)
    assert result["source_bound"]
    assert result["filing_references"][0]["status"] != "METADATA_REFERENCE_MATCH"
    if defect in {"missing", "future_catalog", "failed"}:
        assert result["filing_references"][0]["status"] == "CATALOG_UNAVAILABLE"
    assert len(result["observations"]) == 3
    assert result["financial_scoring_authorized"] is False


@pytest.mark.parametrize("which", ["concept", "catalog"])
def test_latest_failure_blocks_favorable_fallback_in_each_dataset(foundation, which):
    _ingest(foundation, kind="catalog")
    _ingest(foundation)
    _ingest(foundation, sec.SECSubmissionsCapture(None, "http_403"),
            at=NOW + timedelta(seconds=1), kind=which)
    result = _read(foundation, NOW + timedelta(seconds=1))
    if which == "concept":
        assert result["observations"] == [] and result["status"] == "http_403"
    else:
        assert result["metadata_reference_match_count"] == 0
        assert len(result["observations"]) == 3
    assert _read(foundation)["metadata_reference_match_count"] == 3


@pytest.mark.parametrize("defect", ["tamper", "tie", "future_completion"])
def test_unverified_latest_concept_stays_visible_without_usable_rows(foundation, defect):
    _ingest(foundation)
    later = NOW + timedelta(seconds=1)
    if defect == "tie":
        _ingest(foundation, at=later)
    capture = sec.SECSubmissionsCapture(None, "http_404")
    _ingest(foundation, capture, at=later,
            completed=later + timedelta(seconds=1) if defect == "future_completion" else later)
    if defect == "tamper":
        result = _read(foundation, later)
        digest = result["captures"][-1]["raw_data_hash"]
        path = foundation[1].root / "sha256" / digest[:2] / f"{digest}.bin"
        path.write_bytes(b"{}")
    result = _read(foundation, later)
    assert result["status"] == "rejected_or_ambiguous"
    assert result["observations"] == []
    assert len(result["captures"]) >= 2


def test_cli_read_only_is_deterministic_and_cannot_implicitly_capture(foundation):
    _ingest(foundation)
    store, artifacts = foundation
    before = store.path.read_bytes()
    args = [sys.executable, "scripts/inspect_sec_concept.py", "--database", str(store.path),
            "--artifact-root", str(artifacts.root), "--cik", CIK, "--taxonomy", TAXONOMY,
            "--tag", TAG]
    result = subprocess.run([*args, "--as-of", NOW.isoformat()], capture_output=True, text=True)
    assert result.returncode == 2 and not result.stderr
    assert json.loads(result.stdout)["source_bound"] is True
    assert store.path.read_bytes() == before
    invalid = subprocess.run(args, capture_output=True, text=True)
    assert invalid.returncode == 2 and "error:" in invalid.stderr
