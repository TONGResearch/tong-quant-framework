"""Older SEC references remain pinned, retrieval-time, opt-in and fail-closed."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pytest

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.providers import sec_filing_page as page
from tong_quant.data.providers import sec_submissions as sec
from tong_quant.data.providers.contracts import ProviderDatasetRequest
from tong_quant.data.providers.sec_concept import DATASET as CONCEPT_DATASET
from tong_quant.data.providers.sec_concept import SECConceptAdapter, concept_subject
from tong_quant.data.sec_concept_inputs import read_sec_concept_inputs
from tong_quant.data.sec_filing_archive import (
    build_sec_page_request,
    read_sec_filing_archive_inputs,
)
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.version import SEC_FILING_PAGE_LEGACY_VERSION

NOW = datetime(2026, 10, 27, 10, tzinfo=UTC)
CIK = "0000789019"
PAGE = f"CIK{CIK}-submissions-001.json"


def _columns(dates, accessions):
    return {"accessionNumber": accessions, "filingDate": dates,
        "reportDate": ["2019-06-30"] * len(dates), "form": ["10-K"] * len(dates),
        "acceptanceDateTime": [value + "T20:01:00Z" for value in dates],
        "primaryDocument": ["annual.htm"] * len(dates)}


def _older():
    return _columns(["2019-07-30", "2020-07-30"],
                    ["0001193125-19-123456", "0001193125-20-123456"])


def _catalog():
    return {"cik": 789019, "filings": {"recent": _columns(["2025-07-30"],
        ["0001193125-25-123456"]), "files": [{"name": PAGE, "filingCount": 2,
            "filingFrom": "2019-07-30", "filingTo": "2020-07-30"}]}}


@pytest.fixture
def foundation(tmp_path):
    store = SQLiteStore(tmp_path / "archive.sqlite3")
    store.initialize()
    return store, FileSystemArtifactStore(tmp_path / "raw")


def _parent(foundation, payload=None, at=NOW - timedelta(seconds=10), capture=None):
    service = ProviderNeutralIngestionService(foundation[0], artifact_store=foundation[1],
                                              clock=lambda: at)
    capture = capture or sec.SECSubmissionsCapture(payload or _catalog())
    return service.ingest(sec.SECSubmissionsAdapter(download=lambda _: capture, clock=lambda: at),
                          ProviderDatasetRequest(sec.DATASET, Market.US, CIK, at))


def _request(foundation, at=NOW):
    return build_sec_page_request(*foundation, CIK, PAGE, as_of=at)


def _page(foundation, payload=None, capture=None, at=NOW, request=None, completed=None,
          version=None):
    request = request or _request(foundation, at)
    capture = capture or sec.SECSubmissionsCapture(payload or _older())
    adapter = page.SECFilingPageAdapter(download=lambda _: capture, clock=lambda: at)
    if version:
        adapter.model_version = version
    return ProviderNeutralIngestionService(foundation[0], artifact_store=foundation[1],
        clock=lambda: completed or at).ingest(adapter, request)


def _concept(foundation):
    rows = [{"end": "2019-06-30", "start": "2018-07-01", "val": 100,
             "accn": accession, "form": "10-K", "filed": filed}
            for accession, filed in zip(["0001193125-19-123456", "0001193125-20-123456",
                "0001193125-25-123456"], ["2019-07-30", "2020-07-30", "2025-07-30"], strict=True)]
    capture = sec.SECSubmissionsCapture({"cik": 789019, "taxonomy": "us-gaap", "tag": "Revenues",
                                        "units": {"USD": rows}})
    ProviderNeutralIngestionService(foundation[0], artifact_store=foundation[1], clock=lambda: NOW
        ).ingest(SECConceptAdapter(download=lambda _: capture, clock=lambda: NOW),
            ProviderDatasetRequest(CONCEPT_DATASET, Market.US,
                concept_subject(CIK, "us-gaap", "Revenues"), NOW))


def _read(foundation, at=NOW):
    return read_sec_filing_archive_inputs(*foundation, CIK, as_of=at)


def _values(foundation, at=NOW, archive=True):
    return read_sec_concept_inputs(*foundation, CIK, "us-gaap", "Revenues", as_of=at,
                                   include_older_pages=archive)


@pytest.mark.parametrize("cik,name", [("MSFT", PAGE), (CIK, "../page.json"),
    (CIK, "https://data.sec.gov/submissions/" + PAGE),
    (CIK, "CIK0000000001-submissions-001.json"), ("0000000000", PAGE)])
def test_page_identity_is_explicit_not_arbitrary_url(cik, name):
    with pytest.raises(ValueError):
        page.page_subject(cik, name)


@pytest.mark.parametrize("name,value", [("parent_evidence_id", "bad"),
    ("parent_raw_data_hash", "A" * 64), ("parent_available_at", "2026-10-28T00:00:00Z"),
    ("parent_available_at", "2026-10-26T00:00:00"), ("filing_count", "True"),
    ("filing_count", "10001"), ("filing_from", "2021-01-01"), ("filing_to", "not-a-date")])
def test_pinned_descriptor_request_rejects_bad_values(foundation, name, value):
    _parent(foundation)
    request = _request(foundation)
    with pytest.raises(ValueError):
        page.page_url(replace(request, parameters={**request.parameters, name: value}))


def test_request_factory_requires_verified_unique_parent_reference(foundation):
    with pytest.raises(ValueError):
        _request(foundation)
    _parent(foundation)
    with pytest.raises(ValueError):
        build_sec_page_request(*foundation, CIK, f"CIK{CIK}-submissions-999.json", as_of=NOW)
    request = _request(foundation)
    assert len(request.parameters["parent_evidence_id"]) == 64
    assert request.parameters["filing_count"] == "2"


def test_page_cannot_be_published_before_its_parent_even_with_later_request_cutoff(foundation):
    _parent(foundation)
    request = _request(foundation)
    with pytest.raises(ValueError, match="parent availability"):
        _page(foundation, at=NOW - timedelta(seconds=11), request=request)
    assert foundation[0].table_count("provider_evidence_records") == 1
    assert foundation[0].table_count("provider_artifacts") == 1


@pytest.mark.parametrize("defect", ["count", "outside", "missing_column", "null_date"])
def test_page_descriptor_mismatch_is_retained_not_admitted(foundation, defect):
    _parent(foundation)
    request = _request(foundation)
    payload = _older()
    if defect == "count":
        for values in payload.values():
            values.pop()
    elif defect == "outside":
        payload["filingDate"][1] = "2020-07-31"
    elif defect == "missing_column":
        del payload["acceptanceDateTime"]
    else:
        payload["filingDate"][1] = None
    normalized = page.normalize_page(sec.SECSubmissionsCapture(payload), request, NOW)
    assert normalized["descriptor_consistent"] is False
    assert normalized["historical_replay_eligible"] is False
    _page(foundation, payload=payload)
    assert _read(foundation)["pages"][0]["usable"] is False


def test_declared_interval_is_not_observed_extrema_and_v1_is_preserved(foundation):
    parent = _catalog()
    parent["filings"]["files"][0]["filingTo"] = "2020-08-31"
    _parent(foundation, parent)
    request = _request(foundation)
    capture = sec.SECSubmissionsCapture(_older())
    current = page.normalize_page(capture, request, NOW)
    assert current["descriptor_consistent"] is True
    assert current["observed_filing_to"] == "2020-07-30"
    legacy = page.normalize_page(capture, request, NOW, version=SEC_FILING_PAGE_LEGACY_VERSION)
    assert legacy["descriptor_consistent"] is False
    assert "observed_filing_to" not in legacy
    _page(foundation, version=SEC_FILING_PAGE_LEGACY_VERSION)
    assert _read(foundation)["pages"][0]["usable"] is False
    _page(foundation, at=NOW + timedelta(seconds=1))
    assert _read(foundation, NOW + timedelta(seconds=1))["pages"][0]["usable"] is True
    assert _read(foundation)["pages"][0]["status"] == "descriptor_mismatch"


def test_reference_expansion_is_opt_in_pit_safe_and_preserves_old_hash(foundation):
    _parent(foundation)
    _concept(foundation)
    before = _values(foundation, archive=False)
    assert before["metadata_reference_match_count"] == 1
    assert _values(foundation)["metadata_reference_match_count"] == 1
    _page(foundation)
    _page(foundation)
    database_before = foundation[0].path.read_bytes()
    result = _values(foundation)
    assert result["metadata_reference_match_count"] == 3
    assert all(row["reference_source"]["evidence_id"] for row in result["filing_references"])
    assert _values(foundation, archive=False)["input_hash"] == before["input_hash"]
    assert result["input_hash"] == _values(foundation)["input_hash"]
    assert result["input_hash"] == _values(
        foundation, NOW.astimezone(ZoneInfo("Asia/Kuala_Lumpur")))["input_hash"]
    assert _read(foundation, NOW - timedelta(microseconds=1))["pages"][0]["status"] == "missing"
    assert foundation[0].path.read_bytes() == database_before
    assert foundation[0].table_count("provider_evidence_records") == 3
    for table in ("fundamental_facts", "research_reports", "signals"):
        assert foundation[0].table_count(table) == 0


@pytest.mark.parametrize("defect", ["failure", "tamper", "tie", "future_completion"])
def test_newest_page_defect_never_falls_back_to_old_positive_rows(foundation, defect):
    _parent(foundation)
    _concept(foundation)
    _page(foundation)
    later = NOW + timedelta(seconds=1)
    if defect == "tie":
        _page(foundation, at=later)
    _page(foundation, capture=sec.SECSubmissionsCapture(None, "http_403"), at=later,
          completed=later + timedelta(seconds=1) if defect == "future_completion" else later)
    if defect == "tamper":
        archive = _read(foundation, later)
        digest = archive["pages"][0]["captures"][-1]["raw_data_hash"]
        path = foundation[1].root / "sha256" / digest[:2] / f"{digest}.bin"
        path.write_bytes(b"{}")
    result = _values(foundation, later)
    assert result["metadata_reference_match_count"] == 1
    assert result["filing_references"][0]["status"] == "ARCHIVE_PAGE_UNAVAILABLE"
    assert _values(foundation)["metadata_reference_match_count"] == 3


def test_page_from_another_parent_cannot_silently_bind_to_a_new_catalog(foundation):
    _parent(foundation)
    _concept(foundation)
    _page(foundation)
    _parent(foundation, at=NOW + timedelta(seconds=1))
    result = _values(foundation, NOW + timedelta(seconds=1))
    assert result["archive_pages"][0]["use_status"] == "PARENT_MISMATCH"
    assert result["metadata_reference_match_count"] == 1


def test_missing_or_corrupt_current_parent_cannot_use_older_pages(foundation):
    _parent(foundation)
    _concept(foundation)
    _page(foundation)
    _parent(foundation, capture=sec.SECSubmissionsCapture(None, "http_403"),
            at=NOW + timedelta(seconds=1))
    result = _values(foundation, NOW + timedelta(seconds=1))
    assert result["metadata_reference_match_count"] == 0
    with pytest.raises(ValueError):
        _request(foundation, NOW + timedelta(seconds=1))


def test_cross_page_duplicate_accessions_are_ambiguous_not_deduplicated(foundation):
    parent = _catalog()
    parent["filings"]["files"][0].update(filingCount=3, filingTo="2025-07-30")
    _parent(foundation, parent)
    _concept(foundation)
    payload = _older()
    recent = parent["filings"]["recent"]
    for key in payload:
        payload[key].append(recent[key][0])
    _page(foundation, payload)
    result = _values(foundation)
    assert result["filing_references"][2]["status"] == "AMBIGUOUS_FILING_REFERENCE"


def test_invalid_recent_row_keeps_partial_status_even_when_all_pages_are_captured(foundation):
    parent = _catalog()
    parent["filings"]["recent"]["acceptanceDateTime"][0] = "2026-10-28T20:01:00Z"
    _parent(foundation, parent)
    _page(foundation)
    result = _read(foundation)
    assert result["status"] == "partial_metadata"
    assert len(result["filings"]) == 3
    assert result["filings"][0]["status"] == "FUTURE_METADATA"


def test_page_network_path_is_fixed_and_uses_the_shared_transport(foundation, monkeypatch):
    _parent(foundation)
    download = Mock(return_value=sec.SECSubmissionsCapture(_older()))
    monkeypatch.setattr(page, "download_sec_json", download)
    page.download_page(_request(foundation))
    download.assert_called_once_with(f"https://data.sec.gov/submissions/{PAGE}")


@pytest.mark.parametrize("value", ["false", 1, None])
def test_archive_expansion_cannot_be_enabled_by_truthy_nonboolean_inputs(foundation, value):
    with pytest.raises(ValueError, match="boolean opt-in"):
        read_sec_concept_inputs(*foundation, CIK, "us-gaap", "Revenues", as_of=NOW,
                                include_older_pages=value)
