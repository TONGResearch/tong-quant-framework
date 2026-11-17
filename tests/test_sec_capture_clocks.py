"""Synthetic SEC clock contracts, not source/accounting or live access approval."""

import runpy
from dataclasses import replace
from datetime import datetime, timedelta
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.providers import sec_body as body
from tong_quant.data.providers import sec_concept as concept
from tong_quant.data.providers import sec_filing_page as page
from tong_quant.data.providers import sec_submissions as sec
from tong_quant.data.providers.contracts import ProviderDatasetRequest, provider_evidence_id
from tong_quant.data.sec_body_inputs import build_sec_body_request, read_sec_body_inputs
from tong_quant.data.sec_concept_inputs import read_sec_concept_inputs
from tong_quant.data.sec_filing_archive import read_sec_filing_archive_inputs
from tong_quant.data.sec_filing_inputs import read_sec_filing_inputs
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market

KINDS = ("submissions", "concept", "page", "body")
TABLES = ("ingestion_batches", "provider_artifacts", "provider_evidence_records",
          "raw_dataset_fingerprints", "provider_limitations")


@lru_cache
def _helpers(kind):
    names = {"submissions": "test_sec_submissions.py", "concept": "test_sec_concept.py",
             "page": "test_sec_filing_archive.py", "body": "test_sec_body.py"}
    return runpy.run_path(str(Path(__file__).with_name(names[kind])))


def _footprint(store, artifacts):
    paths = [store.path]
    wal = store.path.with_name(store.path.name + "-wal")
    if wal.exists():
        paths.append(wal)
    paths += [path for path in artifacts.root.rglob("*") if path.is_file()]
    return {path: sha256(path.read_bytes()).hexdigest() for path in paths}


def _case(kind, tmp_path):
    helpers = _helpers(kind)
    at = helpers["NOW"]
    store = SQLiteStore(tmp_path / "sec-clock.sqlite3")
    store.initialize()
    artifacts = FileSystemArtifactStore(tmp_path / "raw")
    foundation = store, artifacts
    if kind == "page":
        helpers["_parent"](foundation)
    elif kind == "body":
        request = ProviderDatasetRequest(sec.DATASET, Market.US, helpers["CIK"], at)
        capture = sec.SECSubmissionsCapture(helpers["_catalog"]())
        ProviderNeutralIngestionService(store, artifact_store=artifacts, clock=lambda: at).ingest(
            sec.SECSubmissionsAdapter(download=lambda _: capture, clock=lambda: at), request)
        at += timedelta(seconds=1)
    if kind == "submissions":
        request = helpers["_request"](at)
        capture = sec.SECSubmissionsCapture(helpers["_payload"]())
        adapter_class = sec.SECSubmissionsAdapter
    elif kind == "concept":
        request = helpers["_request"](at)
        capture = sec.SECSubmissionsCapture(helpers["_payload"]())
        adapter_class = concept.SECConceptAdapter
    elif kind == "page":
        request = helpers["_request"](foundation, at)
        capture = sec.SECSubmissionsCapture(helpers["_older"]())
        adapter_class = page.SECFilingPageAdapter
    else:
        request = build_sec_body_request(*foundation, helpers["CIK"], helpers["ACCESSION"],
                                         as_of=at)
        capture = body.SECBodyCapture(helpers["_xml"]())
        adapter_class = body.SECBodyAdapter

    def adapter(clock, response=capture):
        return adapter_class(download=lambda _: response, clock=lambda: clock)

    def read(cutoff):
        if kind == "submissions":
            result = read_sec_filing_inputs(*foundation, helpers["CIK"], as_of=cutoff)
        elif kind == "concept":
            result = read_sec_concept_inputs(*foundation, helpers["CIK"], helpers["TAXONOMY"],
                                             helpers["TAG"], as_of=cutoff)
        elif kind == "page":
            result = read_sec_filing_archive_inputs(*foundation, helpers["CIK"], as_of=cutoff)
        else:
            result = read_sec_body_inputs(*foundation, helpers["CIK"], helpers["ACCESSION"],
                                          as_of=cutoff, tags=(helpers["TAG"],))
        return result, result["pages"][0] if kind == "page" else result

    return {"store": store, "artifacts": artifacts, "at": at, "request": request,
            "capture": capture, "adapter": adapter, "read": read, "kind": kind}


@pytest.fixture(params=KINDS)
def sec_case(request, tmp_path):
    return _case(request.param, tmp_path)


def _ingest(case, clock, *, request=None, adapter=None):
    return ProviderNeutralIngestionService(case["store"], artifact_store=case["artifacts"],
        clock=lambda: clock).ingest(adapter or case["adapter"](clock), request or case["request"])


@pytest.mark.parametrize("clock_label", ("naive", "malaysia", "ny_first", "ny_second"))
@pytest.mark.parametrize("failed", (False, True))
def test_unsupported_sec_clock_rejects_before_any_retention(sec_case, clock_label, failed):
    case = sec_case
    captured = datetime(2026, 11, 1, 1, 30)
    if clock_label == "malaysia":
        captured = captured.replace(tzinfo=ZoneInfo("Asia/Kuala_Lumpur"))
    elif clock_label.startswith("ny"):
        captured = captured.replace(tzinfo=ZoneInfo("America/New_York"),
                                    fold=int(clock_label.endswith("second")))
    response = case["capture"]
    if failed:
        response = (body.SECBodyCapture(None, "network_unavailable") if case["kind"] == "body"
                    else sec.SECSubmissionsCapture(None, "network_unavailable"))
    before_counts = {table: case["store"].table_count(table) for table in TABLES}
    before = _footprint(case["store"], case["artifacts"])
    with pytest.raises(ValueError, match="timezone|capture clock must use UTC"):
        _ingest(case, case["at"], adapter=case["adapter"](captured, response))
    assert _footprint(case["store"], case["artifacts"]) == before
    assert {table: case["store"].table_count(table) for table in TABLES} == before_counts


@pytest.mark.parametrize("zone", ("UTC", "Etc/GMT", "Europe/London"))
def test_zero_offset_sec_clocks_keep_original_bytes_ids_and_readback(sec_case, zone):
    case = sec_case
    labelled = case["at"].astimezone(ZoneInfo(zone))
    canonical = case["adapter"](case["at"]).fetch(case["request"])
    actual = case["adapter"](labelled).fetch(replace(case["request"], as_of=labelled))
    assert actual == canonical
    assert actual.artifacts[0].content == canonical.artifacts[0].content
    _ingest(case, labelled, request=replace(case["request"], as_of=labelled))
    full, target = case["read"](case["at"])
    assert target.get("usable", target.get("source_bound")) is True
    assert all(full[name] is False for name in ("execution_authorized",
        "validation_authorized", "historical_replay_eligible", "financial_scoring_authorized"))


@pytest.mark.parametrize("zone", ("Asia/Kuala_Lumpur", "America/New_York"))
def test_non_utc_sec_request_and_read_cutoffs_remain_supported(sec_case, zone):
    case = sec_case
    labelled = case["at"].astimezone(ZoneInfo(zone))
    _ingest(case, case["at"], request=replace(case["request"], as_of=labelled))
    before = _footprint(case["store"], case["artifacts"])
    original, original_target = case["read"](case["at"])
    equivalent, target = case["read"](labelled)
    assert target.get("usable", target.get("source_bound")) is True
    assert original == equivalent and original_target == target
    assert _footprint(case["store"], case["artifacts"]) == before


@pytest.mark.parametrize("predecessor", (False, True))
def test_legacy_sec_clock_identity_preserved_without_old_good_fallback(sec_case, predecessor):
    case = sec_case
    if predecessor:
        _ingest(case, case["at"])
    current = case["at"] + timedelta(seconds=1)
    labelled = current.astimezone(ZoneInfo("Asia/Kuala_Lumpur"))
    request = replace(case["request"], as_of=current)
    canonical = case["adapter"](current).fetch(request)
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
            return case["adapter"](current).capabilities()

        def fetch(self, actual_request):
            return legacy

    _ingest(case, current, request=replace(request, as_of=labelled), adapter=LegacyFixtureAdapter())
    before = _footprint(case["store"], case["artifacts"])
    full, target = case["read"](current)
    assert target["status"] == "rejected_or_ambiguous"
    assert target.get("usable", target.get("source_bound")) is False
    assert len(target["captures"]) == 1 + int(predecessor)
    assert any(item["evidence_id"] == record.evidence_id for item in target["captures"])
    assert full["execution_authorized"] is False and full["validation_authorized"] is False
    assert _footprint(case["store"], case["artifacts"]) == before
    if predecessor:
        _, old_target = case["read"](case["at"])
        assert old_target.get("usable", old_target.get("source_bound")) is True
