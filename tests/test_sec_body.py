"""Bounded filing bytes and numeric correspondence never grant source admission."""

import base64
import json
import runpy
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pytest

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.providers import sec_body as body
from tong_quant.data.providers import sec_concept as concept
from tong_quant.data.providers import sec_submissions as sec
from tong_quant.data.providers import yahoo_fundamentals as financial
from tong_quant.data.providers import yahoo_snapshot as prices
from tong_quant.data.providers.contracts import ProviderDatasetRequest
from tong_quant.data.sec_body_inputs import build_sec_body_request, read_sec_body_inputs
from tong_quant.data.sec_inline_review import review_inline_body
from tong_quant.data.sec_period_inputs import (
    SECPeriodResearchInput,
    SECPeriodSelection,
    parse_sec_period_selections,
    read_sec_period_inputs,
    read_sec_period_research_input,
)
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.version import (
    EQUITY_HOLDING_DISPLAY_VERSION,
    SEC_PERIOD_INPUT_VERSION,
    US_SEC_DISPLAY_VERSION,
    US_SEC_IDENTITY_DISPLAY_VERSION,
    US_SEC_PERIOD_DISPLAY_VERSION,
    US_SEC_SOURCE_ROOT_VERSION,
)

NOW = datetime(2026, 10, 27, 10, tzinfo=UTC)
CIK, ACCESSION, TAG = "0000789019", "0001193125-25-123456", "Revenues"


def _xml(*, text="120", attributes="", extra="", context_extra="", namespace=None):
    namespace = namespace or "http://fasb.org/us-gaap/2025"
    return f'''<!DOCTYPE html><html xmlns="http://www.w3.org/1999/xhtml"
      xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"
      xmlns:xbrli="http://www.xbrl.org/2003/instance"
      xmlns:us-gaap="{namespace}" xmlns:iso="http://www.xbrl.org/2003/iso4217"
      xmlns:ixt="http://www.xbrl.org/inlineXBRL/transformation/2020-02-12"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><head/><body>
      <xbrli:context id="c"><xbrli:entity><xbrli:identifier
       scheme="http://www.sec.gov/CIK">{CIK}</xbrli:identifier>{context_extra}</xbrli:entity>
       <xbrli:period><xbrli:startDate>2024-07-01</xbrli:startDate>
       <xbrli:endDate>2025-06-30</xbrli:endDate></xbrli:period></xbrli:context>
      <xbrli:unit id="u"><xbrli:measure>iso:USD</xbrli:measure></xbrli:unit>
      <ix:nonFraction name="us-gaap:{TAG}" contextRef="c" unitRef="u"
       decimals="-6" scale="6" {attributes}>{text}</ix:nonFraction>{extra}
      </body></html>'''.encode()


def _review(content=None):
    return review_inline_body(content or _xml(), CIK, as_of=NOW, tags=(TAG,))


def _catalog():
    return {"cik": 789019, "filings": {"files": [], "recent": {
        "accessionNumber": [ACCESSION], "filingDate": ["2025-07-30"],
        "acceptanceDateTime": ["2025-07-30T20:05:12Z"], "reportDate": ["2025-06-30"],
        "form": ["10-K"], "primaryDocument": ["annual.htm"]}}}


@pytest.fixture
def foundation(tmp_path):
    store = SQLiteStore(tmp_path / "body.sqlite3")
    store.initialize()
    artifacts = FileSystemArtifactStore(tmp_path / "raw")
    request = ProviderDatasetRequest(sec.DATASET, Market.US, CIK, NOW)
    ProviderNeutralIngestionService(store, artifact_store=artifacts, clock=lambda: NOW).ingest(
        sec.SECSubmissionsAdapter(download=lambda _: sec.SECSubmissionsCapture(_catalog()),
                                  clock=lambda: NOW), request)
    return store, artifacts


def _capture(foundation, content=None, *, at=NOW + timedelta(seconds=1), error="", completed=None):
    request = build_sec_body_request(*foundation, CIK, ACCESSION, as_of=at)
    capture = body.SECBodyCapture(None if error else content or _xml(), error)
    return ProviderNeutralIngestionService(foundation[0], artifact_store=foundation[1],
        clock=lambda: completed or at).ingest(
            body.SECBodyAdapter(download=lambda _: capture, clock=lambda: at), request)


def _concept(foundation, value=120_000_000, *, tag=TAG):
    payload = {"cik": 789019, "taxonomy": "us-gaap", "tag": tag, "label": "Synthetic",
        "units": {"USD": [{"start": "2024-07-01", "end": "2025-06-30", "val": value,
            "accn": ACCESSION, "fy": 2025, "fp": "FY", "form": "10-K", "filed": "2025-07-30"}]}}
    at = NOW + timedelta(seconds=1)
    request = ProviderDatasetRequest(concept.DATASET, Market.US,
                                     concept.concept_subject(CIK, "us-gaap", tag), at)
    ProviderNeutralIngestionService(foundation[0], artifact_store=foundation[1],
        clock=lambda: at).ingest(concept.SECConceptAdapter(
            download=lambda _: sec.SECSubmissionsCapture(payload), clock=lambda: at), request)


def _read(foundation, at=NOW + timedelta(seconds=2)):
    return read_sec_body_inputs(*foundation, CIK, ACCESSION, as_of=at, tags=(TAG,))


def test_numeric_subset_keeps_context_unit_precision_and_original_text():
    result = _review(_xml(text="<span>1,234.5</span>",
                         attributes='format="ixt:num-dot-decimal" sign="-"'))
    assert result["status"] == "SUBSET_REVIEW_UNQUALIFIED"
    row = result["facts"][0]
    assert row["status"] == "OBSERVED_UNQUALIFIED" and row["value"] == "-1234500000.0"
    assert row["native_attributes"]["decimals"] == "-6"
    assert row["raw_text"] == "1,234.5" and row["unit"] == "USD"
    assert row["period_start"] == "2024-07-01" and row["entity_cik"] == CIK
    assert not result["financial_scoring_authorized"]


@pytest.mark.parametrize("kind", [
    "segment", "scenario", "both", "other_child", "missing", "duplicate",
    "nested", "targeted", "wrong_unit", "wrong_cik", "future_period",
])
def test_optional_exclusion_audit_observes_structure_without_recovering_values(kind):
    content = _xml()
    if kind in {"segment", "both"}:
        content = _xml(context_extra="<xbrli:segment><unvalidated/></xbrli:segment>")
    if kind in {"scenario", "both"}:
        content = content.replace(b"</xbrli:context>",
            b"<xbrli:scenario><unvalidated/></xbrli:scenario></xbrli:context>")
    if kind == "other_child":
        content = content.replace(b"</xbrli:context>", b"<other/></xbrli:context>")
    if kind == "missing":
        content = content.replace(b'contextRef="c"', b'contextRef="absent"')
    if kind == "duplicate":
        content = content.replace(b'<xbrli:context id="c">',
            b'<span id="c"/><xbrli:context id="c">')
    if kind == "nested":
        content = content.replace(b"<ix:nonFraction", b"<ix:nonNumeric><ix:nonFraction").replace(
            b"</ix:nonFraction>", b"</ix:nonFraction></ix:nonNumeric>")
    if kind == "targeted":
        content = _xml(attributes='target="alternate"')
    if kind == "wrong_unit":
        content = content.replace(b"iso:USD", b"iso:CNY")
    if kind == "wrong_cik":
        content = content.replace(CIK.encode(), b"0000000001")
    if kind == "future_period":
        content = content.replace(b"2025-06-30", b"2027-06-30")
    legacy = _review(content)
    extended = review_inline_body(content, CIK, as_of=NOW, tags=(TAG,), explain_exclusions=True)
    audit = extended.pop("exclusion_audit")
    assert extended == legacy and legacy["facts"][0]["value"] is None
    assert audit["inventory_status"] == "STRUCTURE_OBSERVED"
    assert audit["selected_occurrence_count"] == audit["excluded_occurrence_count"] == 1
    assert audit["source_body_sha256"] == sha256(content).hexdigest()
    row = audit["occurrences"][0]
    assert row["original_reason"] == legacy["facts"][0]["reason"]
    assert row["context_validity"] == row["dimension_semantics"] == "NOT_VALIDATED"
    assert row["excluded_value_admitted"] is False and "value" not in row
    assert row["segment_count"] == (None if kind in {"missing", "duplicate"}
                                    else 1 if kind in {"segment", "both"} else 0)
    assert row["scenario_count"] == (None if kind in {"missing", "duplicate"}
                                     else 1 if kind in {"scenario", "both"} else 0)
    assert row["other_context_child_count"] == (None if kind in {"missing", "duplicate"}
                                               else 1 if kind == "other_child" else 0)
    assert row["inline_ancestor_scope_blocked"] is (kind == "nested")
    assert row["targeted_document_present"] is (kind == "targeted")
    body_doc = {key: value for key, value in audit.items() if key != "input_hash"}
    assert audit["input_hash"] == sha256(financial_input_json(body_doc).encode()).hexdigest()
    assert all(audit[name] is False for name in (
        "values_changed", "financial_scoring_authorized", "historical_replay_eligible",
        "validation_authorized", "execution_authorized"))


@pytest.mark.parametrize("content", [
    b"<html>", b"", b"\xff", b'<!DOCTYPE html SYSTEM "file:///invalid"><html/>',
    b'<!DOCTYPE html [<!ENTITY x "expanded">]><html>&x;</html>',
    b"<a>" * 130 + b"</a>" * 130,
])
def test_exclusion_audit_cannot_claim_an_inventory_for_unsupported_document(content):
    result = review_inline_body(content, CIK, as_of=NOW, tags=(TAG,), explain_exclusions=True)
    audit = result.pop("exclusion_audit")
    assert result == review_inline_body(content, CIK, as_of=NOW, tags=(TAG,))
    assert audit["inventory_status"] == "DOCUMENT_UNAVAILABLE"
    assert audit["occurrences"] == [] and audit["selected_occurrence_count"] == 0


@pytest.mark.parametrize("value", [None, 1, "true", []])
def test_exclusion_flag_is_exact_boolean_before_database_access(value):
    with pytest.raises(ValueError, match="explicit boolean"):
        read_sec_body_inputs(None, None, CIK, ACCESSION, as_of=NOW,
                             explain_exclusions=value)


def test_default_and_explicit_false_review_are_exact_and_empty_audit_is_deterministic():
    assert _review() == review_inline_body(_xml(), CIK, as_of=NOW, tags=(TAG,),
                                          explain_exclusions=False)
    first = review_inline_body(_xml(), CIK, as_of=NOW, tags=(TAG,), explain_exclusions=True)
    other = review_inline_body(_xml(), CIK, as_of=NOW.astimezone(ZoneInfo("Asia/Kuala_Lumpur")),
                               tags=(TAG,), explain_exclusions=True)
    assert first == other and first["exclusion_audit"]["occurrences"] == []
    assert first["facts"] == _review()["facts"]


def test_retained_exclusion_audit_preserves_parent_source_values_and_numeric_comparisons(
    foundation,
):
    _capture(foundation, _xml(context_extra="<xbrli:segment/>"))
    _concept(foundation)
    store, _ = foundation
    before = store.path.read_bytes()
    legacy = _read(foundation)
    extended = read_sec_body_inputs(*foundation, CIK, ACCESSION,
        as_of=NOW + timedelta(seconds=2), tags=(TAG,), explain_exclusions=True)
    assert extended == read_sec_body_inputs(*foundation, CIK, ACCESSION,
        as_of=NOW + timedelta(seconds=2), tags=(TAG,), explain_exclusions=True)
    assert extended.pop("exclusion_review_version") == "sec-inline-exclusion-structure-v1"
    audit = extended["body_review"].pop("exclusion_audit")
    extended.pop("input_hash")
    assert financial_input_json(extended) == financial_input_json(
        {key: value for key, value in legacy.items() if key != "input_hash"})
    assert audit["excluded_occurrence_count"] == 1 and audit["occurrences"][0]["segment_count"] == 1
    assert store.path.read_bytes() == before


@pytest.mark.parametrize("kind", ["future", "latest_failure", "missing_raw"])
def test_exclusion_audit_cannot_bypass_retained_source_gates(foundation, kind):
    _capture(foundation, _xml(context_extra="<xbrli:segment/>"))
    at = NOW if kind == "future" else NOW + timedelta(seconds=3)
    if kind == "latest_failure":
        _capture(foundation, at=NOW + timedelta(seconds=2), error="http_403")
    elif kind == "missing_raw":
        for path in foundation[1].root.rglob("*"):
            if path.is_file():
                path.unlink()
    result = read_sec_body_inputs(*foundation, CIK, ACCESSION, as_of=at, tags=(TAG,),
                                  explain_exclusions=True)
    assert result["body_review"] is None and not result["comparisons"]
    assert result["financial_scoring_authorized"] is False


def test_exclusion_cli_flag_is_read_only_before_any_database_or_artifact_creation(tmp_path):
    path = tmp_path / "absent.sqlite3"
    raw = tmp_path / "absent-raw"
    result = subprocess.run([sys.executable, "scripts/inspect_sec_body.py", "--database", str(path),
        "--artifact-root", str(raw), "--cik", CIK, "--accession", ACCESSION, "--capture",
        "--explain-exclusions"], capture_output=True, text=True)
    assert result.returncode == 2 and "exclusion explanation is read-only" in result.stderr
    assert not path.exists() and not raw.exists()


def test_exclusion_cli_retained_read_repeats_and_is_source_bound(foundation):
    _capture(foundation, _xml(context_extra="<xbrli:segment/>"))
    store, artifacts = foundation
    before = store.path.read_bytes()
    args = [sys.executable, "scripts/inspect_sec_body.py", "--database", str(store.path),
        "--artifact-root", str(artifacts.root), "--cik", CIK, "--accession", ACCESSION,
        "--as-of", (NOW + timedelta(seconds=2)).isoformat(), "--explain-exclusions"]
    first = subprocess.run(args, capture_output=True, text=True)
    second = subprocess.run(args, capture_output=True, text=True)
    assert first.returncode == second.returncode == 2 and not (first.stderr or second.stderr)
    assert first.stdout == second.stdout
    result = json.loads(first.stdout)
    assert result["source_bound"] is True
    assert result["body_review"]["exclusion_audit"]["inventory_status"] == "STRUCTURE_OBSERVED"
    assert store.path.read_bytes() == before


def test_exclusion_audit_does_not_hash_or_parse_an_oversized_body():
    content = b"x" * (body.MAX_BODY_BYTES + 1)
    result = review_inline_body(content, CIK, as_of=NOW, tags=(TAG,), explain_exclusions=True)
    assert result["exclusion_audit"]["source_body_sha256"] is None
    assert result["exclusion_audit"]["inventory_status"] == "DOCUMENT_UNAVAILABLE"
    assert result["facts"] == []


def test_shared_context_structure_does_not_merge_distinct_fact_scope_flags():
    extra = f'''<ix:nonNumeric><ix:nonFraction name="us-gaap:{TAG}" contextRef="c"
      unitRef="u" decimals="-6" scale="6">120</ix:nonFraction></ix:nonNumeric>'''
    content = _xml(context_extra="<xbrli:segment/>", extra=extra)
    result = review_inline_body(content, CIK, as_of=NOW, tags=(TAG,), explain_exclusions=True)
    rows = result["exclusion_audit"]["occurrences"]
    assert len(rows) == 2 and all(row["segment_count"] == 1 for row in rows)
    assert [row["inline_ancestor_scope_blocked"] for row in rows] == [False, True]
    assert result["facts"] == _review(content)["facts"]


@pytest.mark.parametrize("content", [b"<html>", b"", b"\xff", b"<html>&nbsp;</html>",
    b'<!DOCTYPE html SYSTEM "file:///etc/passwd"><html/>',
    b'<!DOCTYPE html [<!ENTITY x "expanded">]><html>&x;</html>',
    b"<a>" * 130 + b"</a>" * 130])
def test_malformed_dtd_entities_and_excessive_depth_are_not_repaired(content):
    result = review_inline_body(content, CIK, as_of=NOW, tags=(TAG,))
    assert result["status"] == "UNSUPPORTED_OR_INVALID_DOCUMENT" and not result["facts"]


@pytest.mark.parametrize("change", [
    lambda xml: xml.replace(b"2025-06-30", b"2027-06-30"),
    lambda xml: xml.replace(CIK.encode(), b"0000000001"),
    lambda xml: xml.replace(b'contextRef="c"', b'contextRef="missing"'),
    lambda xml: xml.replace(b'unitRef="u"', b'unitRef="missing"'),
    lambda xml: xml.replace(b"iso:USD", b"iso:CNY"),
    lambda xml: xml.replace(b"http://www.xbrl.org/2003/iso4217", b"https://wrong.invalid"),
    lambda xml: xml.replace(b'<xbrli:unit id="u">',
        b'<span id="u"/><xbrli:unit id="u">'),
    lambda xml: xml.replace(b'<xbrli:context id="c">',
        b'<span id="c"/><xbrli:context id="c">'),
    lambda xml: xml.replace(b'scale="6"', b'scale="99"'),
    lambda xml: xml.replace(b'decimals="-6"', b'decimals="unknown"'),
    lambda xml: xml.replace(b'scale="6"', b'scale="6" xsi:nil="true"'),
    lambda xml: xml.replace(b'scale="6"', b'scale="6" continuedAt="next"'),
    lambda xml: xml.replace(b'<body>', b'<body target="other">'),
])
def test_invalid_context_units_scale_scope_or_nil_stay_visible_without_values(change):
    result = _review(change(_xml()))
    assert len(result["facts"]) == 1
    assert result["facts"][0]["status"] == "UNSUPPORTED_FACT"
    assert result["facts"][0]["value"] is None and result["facts"][0]["reason"]


@pytest.mark.parametrize("text,attributes", [("1,20", 'format="ixt:num-dot-decimal"'),
    ("-120", 'format="ixt:num-dot-decimal"'), ("-120", 'sign="-"'),
    ("-", 'format="ixt:fixed-zero"'), ("120%", ""), ("$120", ""), ("(120)", ""),
    ("120", 'format="ixt:unknown"'), ("120", 'format="wrong:num-dot-decimal"')])
def test_no_guessing_of_unknown_numeric_transformations(text, attributes):
    assert _review(_xml(text=text, attributes=attributes))["facts"][0]["value"] is None


def test_namespace_and_dimensions_are_not_inferred_from_local_name():
    assert _review(_xml(namespace="https://wrong.invalid"))["facts"][0]["value"] is None
    assert _review(_xml(context_extra="<xbrli:segment/>"))["facts"][0]["value"] is None
    content = _xml(attributes='xmlns:ixt="https://wrong.invalid" format="ixt:num-dot-decimal"')
    assert _review(content)["facts"][0]["value"] is None


def test_targeted_inline_resources_cannot_supply_a_context_to_default_document():
    content = _xml().replace(b'<xbrli:context id="c">',
        b'<ix:resources target="other"><xbrli:context id="c">').replace(
        b'</xbrli:context>', b'</xbrli:context></ix:resources>')
    assert _review(content)["facts"][0]["value"] is None


def test_exact_bytes_retained_and_same_accession_comparison_is_not_qualification(foundation):
    _capture(foundation)
    _concept(foundation)
    before = foundation[0].path.read_bytes()
    result = _read(foundation)
    assert result["source_bound"] and result["status"] == "captured_body_unqualified"
    assert result["comparisons"][0]["status"] == "SUPPORTED_OCCURRENCES_AGREE_UNQUALIFIED"
    assert result["comparisons"][0]["complete_numeric_validation"] is False
    record_hash = result["captures"][-1]["raw_data_hash"]
    envelope = json.loads(foundation[1].read_content(record_hash, "application/json",
                                                   max_bytes=body.MAX_ENVELOPE_BYTES))
    assert base64.b64decode(envelope["body_base64"]) == _xml()
    assert not result["independent_numeric_corroboration"]
    assert result["input_hash"] == _read(foundation)["input_hash"]
    assert foundation[0].path.read_bytes() == before
    assert result["input_hash"] == _read(foundation,
        (NOW + timedelta(seconds=2)).astimezone(ZoneInfo("Asia/Kuala_Lumpur")))["input_hash"]


@pytest.mark.parametrize("extra_value,status", [("120", "SUPPORTED_OCCURRENCES_AGREE_UNQUALIFIED"),
                                               ("121", "NUMERIC_CONFLICT")])
def test_all_supported_duplicate_occurrences_compared_without_favorable_selection(
        foundation, extra_value, status):
    extra = f'''<ix:nonFraction name="us-gaap:{TAG}" contextRef="c" unitRef="u"
        decimals="-6" scale="6">{extra_value}</ix:nonFraction>'''
    _capture(foundation, _xml(extra=extra))
    _concept(foundation)
    result = _read(foundation)["comparisons"][0]
    assert result["status"] == status and len(result["body_occurrences"]) == 2


def test_unsupported_matching_occurrence_blocks_favorable_numeric_status(foundation):
    extra = f'''<ix:nonFraction name="us-gaap:{TAG}" contextRef="c" unitRef="u"
        decimals="-6" scale="99">120</ix:nonFraction>'''
    _capture(foundation, _xml(extra=extra))
    _concept(foundation)
    assert _read(foundation)["comparisons"][0]["status"] == "UNSUPPORTED_MATCHING_BODY_OCCURRENCE"


def test_capture_and_concept_are_visible_only_after_real_completion(foundation):
    _capture(foundation, completed=NOW + timedelta(seconds=3))
    _concept(foundation)
    assert _read(foundation, NOW)["status"] == "missing"
    assert not _read(foundation)["source_bound"]
    assert _read(foundation, NOW + timedelta(seconds=3))["source_bound"]


def test_latest_failed_body_does_not_fall_back(foundation):
    _capture(foundation)
    _concept(foundation)
    _capture(foundation, at=NOW + timedelta(seconds=2), error="http_403")
    result = _read(foundation)
    assert result["source_bound"] and result["status"] == "http_403"
    assert result["body_review"] is None and result["comparisons"] == []
    assert len(result["captures"]) == 2


def test_tied_body_versions_and_tampering_are_rejected(foundation):
    _capture(foundation)
    _capture(foundation, _xml(text="121"))
    assert _read(foundation)["status"] == "rejected_or_ambiguous"


def test_tampered_latest_body_has_no_old_positive_fallback(foundation):
    _capture(foundation)
    _capture(foundation, _xml(text="121"), at=NOW + timedelta(seconds=2))
    result = _read(foundation)
    digest = result["captures"][-1]["raw_data_hash"]
    path = foundation[1].root / "sha256" / digest[:2] / f"{digest}.bin"
    path.write_bytes(b"{}")
    result = _read(foundation)
    assert result["status"] == "rejected_or_ambiguous" and not result["source_bound"]
    assert result["body_review"] is None and len(result["captures"]) == 2


def test_conflicting_and_missing_api_values_are_not_backfilled_from_body(foundation):
    _capture(foundation)
    _concept(foundation, value=121_000_000)
    assert _read(foundation)["comparisons"][0]["status"] == "NUMERIC_CONFLICT"
    at = NOW + timedelta(seconds=2)
    ProviderNeutralIngestionService(foundation[0], artifact_store=foundation[1],
        clock=lambda: at).ingest(concept.SECConceptAdapter(
            download=lambda _: sec.SECSubmissionsCapture(None, "http_403"), clock=lambda: at),
            ProviderDatasetRequest(concept.DATASET, Market.US,
                concept.concept_subject(CIK, "us-gaap", TAG), at))
    assert _read(foundation)["comparisons"][0]["status"] == "NO_VISIBLE_TARGET_ACCESSION_FACTS"


@pytest.mark.parametrize("text,attributes,value", [("0", "", "0"),
    ("-120", "", "-120000000"), ("0.25", "", "250000.00")])
def test_supported_amounts_are_exact_decimals_not_floats(text, attributes, value):
    assert _review(_xml(text=text, attributes=attributes))["facts"][0]["value"] == value


@pytest.mark.parametrize("changes", [("MSFT", (TAG,)), (CIK, ()), (CIK, (TAG, TAG)),
                                    (CIK, ("../Revenues",))])
def test_no_implicit_identity_or_unbounded_tag_scope(changes):
    cik, tags = changes
    with pytest.raises(ValueError):
        review_inline_body(_xml(), cik, as_of=NOW, tags=tags)


def test_factory_does_not_guess_missing_accession_or_missing_catalog(foundation):
    for cik, accession in (("0000000001", ACCESSION), (CIK, "0001193125-25-999999")):
        with pytest.raises(ValueError):
            build_sec_body_request(*foundation, cik, accession, as_of=NOW)


def test_read_only_cli_cannot_capture_implicitly(foundation):
    _capture(foundation)
    store, artifacts = foundation
    args = [sys.executable, "scripts/inspect_sec_body.py", "--database", str(store.path),
        "--artifact-root", str(artifacts.root), "--cik", CIK, "--accession", ACCESSION]
    before = store.path.read_bytes()
    result = subprocess.run([*args, "--as-of", (NOW + timedelta(seconds=2)).isoformat()],
                             capture_output=True, text=True)
    assert result.returncode == 2 and not result.stderr
    assert json.loads(result.stdout)["source_bound"]
    assert store.path.read_bytes() == before
    assert "error:" in subprocess.run(args, capture_output=True, text=True).stderr


def test_transport_reports_empty_or_oversized_body_without_retaining_remote_bytes(monkeypatch):
    monkeypatch.setenv(sec.ACCESS_IDENTITY_ENV, "Synthetic contact@example.invalid")
    monkeypatch.setattr(sec, "sleep", lambda _: None)
    reply = Mock()
    reply.__enter__ = Mock(return_value=reply)
    reply.__exit__ = Mock(return_value=False)
    opener = Mock()
    opener.open.return_value = reply
    monkeypatch.setattr(sec, "build_opener", lambda *_: opener)
    url = "https://www.sec.gov/Archives/edgar/data/789019/000119312525123456/annual.htm"
    for raw, expected in ((b"", "empty_response"), (b"123456", "response_too_large")):
        reply.read.return_value = raw
        assert sec.download_sec_bytes(url, max_bytes=5) == (None, expected)
        reply.read.assert_called_with(6)
    with pytest.raises(ValueError):
        sec.download_sec_bytes(url + "?secret=synthetic", max_bytes=5)


@pytest.mark.parametrize("content", [b"\xff", b"<html>\x00</html>",
    "<html>contact@example.invalid</html>".encode("utf-16")])
def test_unsupported_encodings_cannot_hide_sensitive_content_in_base64(content):
    with pytest.raises(ValueError):
        body.SECBodyCapture(content)


def test_changed_parent_requires_explicit_recapture(foundation):
    _capture(foundation)
    at = NOW + timedelta(seconds=2)
    ProviderNeutralIngestionService(foundation[0], artifact_store=foundation[1],
        clock=lambda: at).ingest(sec.SECSubmissionsAdapter(
            download=lambda _: sec.SECSubmissionsCapture(_catalog()), clock=lambda: at),
            ProviderDatasetRequest(sec.DATASET, Market.US, CIK, at))
    assert not _read(foundation)["source_bound"]
    assert _read(foundation, NOW + timedelta(seconds=1))["source_bound"]


@pytest.mark.parametrize("parameters", [{"primary_document": "../private.htm"},
    {"primary_document": "https://elsewhere.invalid/a.htm"}, {"form": "DEF 14A"},
    {"filed": "2027-01-01"}, {"parent_raw_data_hash": "bad"},
    {"parent_available_at": "2027-01-01T00:00:00+00:00"}])
def test_only_pinned_bounded_periodic_requests_are_accepted(foundation, parameters):
    request = build_sec_body_request(*foundation, CIK, ACCESSION, as_of=NOW)
    with pytest.raises(ValueError):
        body.body_url(replace(request, parameters={**request.parameters, **parameters}))


def test_transport_url_is_pinned_and_secret_bodies_are_rejected(foundation, monkeypatch):
    request = build_sec_body_request(*foundation, CIK, ACCESSION, as_of=NOW)
    downloader = Mock(return_value=(_xml(), ""))
    monkeypatch.setattr(body, "download_sec_bytes", downloader)
    assert body.download_body(request).content == _xml()
    downloader.assert_called_once_with(
        "https://www.sec.gov/Archives/edgar/data/789019/000119312525123456/annual.htm",
        max_bytes=body.MAX_BODY_BYTES)
    monkeypatch.setenv(sec.ACCESS_IDENTITY_ENV, "Synthetic contact@example.invalid")
    for content in (b"<html>token=synthetic-not-a-credential</html>",
                    b"<html>contact&#64;example.invalid</html>"):
        with pytest.raises(ValueError):
            body.SECBodyCapture(content)
        downloader.return_value = (content, "")
        assert body.download_body(request).error_code == "invalid_decoded_response"


def _us_prices(store, artifacts, *, failed=False, at=NOW):
    request = ProviderDatasetRequest(prices.DATASET, Market.US, "MSFT", at, {
        "start_date": "2025-01-01", "end_date": "2026-10-26", "currency": "USD",
        "exchange": "NMS", "timezone": prices.TIMEZONES[Market.US]})
    start = datetime(2025, 1, 1, 15, tzinfo=UTC)
    closes = [10 + index / 100 for index in range(100)]
    capture = prices.YahooSnapshotCapture(None, "provider_unavailable") if failed else (
        prices.YahooSnapshotCapture({"chart": {"error": None, "result": [{
            "meta": {"symbol": "MSFT", "currency": "USD", "exchangeName": "NMS",
                "instrumentType": "EQUITY", "exchangeTimezoneName": prices.TIMEZONES[Market.US],
                "dataGranularity": "1d"},
            "timestamp": [int((start + timedelta(days=i)).timestamp()) for i in range(100)],
            "indicators": {"quote": [{"open": closes, "close": closes,
                "high": [p + 1 for p in closes], "low": [p - 1 for p in closes],
                "volume": [10000] * 100}]}}]}}))
    ProviderNeutralIngestionService(store, artifact_store=artifacts, clock=lambda: at).ingest(
        prices.YahooGlobalSnapshotAdapter(download=lambda _: capture, clock=lambda: at), request)


def _us_arguments(price_store, foundation, *, at=NOW + timedelta(seconds=2), extra=()):
    store, artifacts = foundation
    return ["scripts/inspect_global_technical.py", "--database", str(price_store.path),
        "--artifact-root", str(artifacts.root), "--market", "us", "--symbol", "MSFT",
        "--as-of", at.isoformat(), "--sec-database", str(store.path), "--sec-cik", CIK,
        "--sec-accession", ACCESSION, *extra]


def _us_run(price_store, foundation, **kwargs):
    return subprocess.run([sys.executable, *_us_arguments(price_store, foundation, **kwargs)],
                          capture_output=True, text=True)


def _separate_root_arguments(price_store, price_artifacts, foundation, **kwargs):
    arguments = _us_arguments(price_store, foundation, **kwargs)
    arguments[arguments.index("--artifact-root") + 1] = str(price_artifacts.root)
    return [*arguments, "--sec-artifact-root", str(foundation[1].root)]


def _holding_annotation(path, quantity="0.1"):
    path.write_text(f'''[holding]
symbol = "MSFT"
market = "us"
currency = "USD"
quantity = "{quantity}"
reported_average_cost = "10"
observed_at = "{(NOW - timedelta(hours=1)).isoformat()}"
recorded_at = "{NOW.isoformat()}"
investment_intent = "long_term"
loss_review_percent = "30"
maximum_context_age_seconds = 604800
maximum_price_age_seconds = 604800
''')
    return path


@pytest.mark.parametrize("extension", [(), ("--sec-identity",),
    ("--fundamentals", "--sector-profile", "nonfinancial", "--sec-period",
     "NetIncomeLoss=2024-07-01/2025-06-30")])
def test_separate_sec_root_reads_exact_sources_without_moving_or_admitting_data(
    foundation, tmp_path, extension,
):
    store, artifacts = foundation
    price_store = SQLiteStore(tmp_path / "prices.sqlite3")
    price_store.initialize()
    price_artifacts = FileSystemArtifactStore(tmp_path / "price_raw")
    _us_prices(price_store, price_artifacts)
    _capture(foundation, _xml().replace(TAG.encode(), b"NetIncomeLoss"))
    before = {item.path: sha256(item.path.read_bytes()).hexdigest()
              for item in (store, price_store)}
    files = {path: sha256(path.read_bytes()).hexdigest()
             for root in (artifacts.root, price_artifacts.root) for path in root.rglob("*.bin")}
    arguments = _separate_root_arguments(price_store, price_artifacts, foundation, extra=extension)
    first = subprocess.run([sys.executable, *arguments], capture_output=True, text=True)
    second = subprocess.run([sys.executable, *arguments], capture_output=True, text=True)
    assert first.returncode == second.returncode == 2 and not first.stderr
    assert first.stdout == second.stdout
    doc = json.loads(first.stdout)
    assert doc["inputs"]["status"] == "observed_unqualified"
    assert doc["sec_filing_status"] == "captured_body_unqualified"
    selection = doc["sec_source_selection"]
    assert selection["model_version"] == US_SEC_SOURCE_ROOT_VERSION
    assert selection["shared_artifact_root"] is False
    assert not selection["source_root_binding_verified"]
    assert not selection["cross_store_atomicity_verified"]
    assert not selection["automatic_fallback_allowed"]
    assert not doc["execution_authorized"] and not doc["financial_scoring_authorized"]
    assert doc["combined_snapshot_scope"] == "separate_database_snapshots_shared_cutoff"
    assert str(tmp_path) not in first.stdout
    digest = doc.pop("combined_evidence_hash")
    assert digest == sha256(financial_input_json(doc).encode()).hexdigest()
    assert all(sha256(path.read_bytes()).hexdigest() == digest for path, digest in before.items())
    assert files == {path: sha256(path.read_bytes()).hexdigest()
                     for root in (artifacts.root, price_artifacts.root)
                     for path in root.rglob("*.bin")}


@pytest.mark.parametrize("kind", ["wrong_root", "future", "failure", "tampered"])
def test_explicit_sec_root_never_falls_back_or_hides_missing_sources(foundation, tmp_path, kind):
    store, artifacts = foundation
    _us_prices(store, artifacts)
    _capture(foundation, at=NOW + timedelta(seconds=3) if kind == "future" else
             NOW + timedelta(seconds=1))
    if kind == "failure":
        _capture(foundation, at=NOW + timedelta(seconds=2), error="http_403")
    if kind == "tampered":
        digest = _read(foundation)["captures"][-1]["raw_data_hash"]
        (artifacts.root / "sha256" / digest[:2] / f"{digest}.bin").write_bytes(b"{}")
    if kind == "wrong_root":
        price_store = SQLiteStore(tmp_path / "other.sqlite3")
        price_store.initialize()
        _us_prices(price_store, artifacts)
        root = tmp_path / "absent_root"
    else:
        price_store, root = store, artifacts.root
    arguments = [*_us_arguments(price_store, foundation), "--sec-artifact-root", str(root)]
    result = subprocess.run([sys.executable, *arguments], capture_output=True, text=True)
    assert result.returncode == 2 and not result.stderr
    doc = json.loads(result.stdout)
    expected = {"wrong_root": "rejected_or_ambiguous", "future": "missing",
                "failure": "http_403", "tampered": "rejected_or_ambiguous"}
    assert doc["sec_filing_status"] == expected[kind]
    assert doc["sec_filing"]["body_review"] is None
    assert doc["diagnostics"]["macd_dif"] is not None
    assert not doc["combined_inputs_admitted"]
    if kind == "wrong_root":
        assert not root.exists()


@pytest.mark.parametrize("kind", ["no_sec", "partial", "same_db_other_root", "capture", "hk"])
def test_invalid_sec_root_options_fail_before_creating_files(tmp_path, kind):
    database = tmp_path / "absent.sqlite3"
    extra = ["--sec-artifact-root", str(tmp_path / "sec_raw")]
    if kind != "no_sec":
        extra += ["--sec-database", str(database), "--sec-cik", CIK]
    if kind not in {"no_sec", "partial"}:
        extra += ["--sec-accession", ACCESSION]
    if kind == "capture":
        extra += ["--capture"]
    result = subprocess.run([sys.executable, "scripts/inspect_global_technical.py",
        "--database", str(database), "--artifact-root", str(tmp_path / "price_raw"),
        "--market", "hong_kong" if kind == "hk" else "us", "--symbol", "MSFT", *extra],
        capture_output=True, text=True)
    assert result.returncode == 2 and "error:" in result.stderr
    assert not result.stdout and "Traceback" not in result.stderr
    assert not database.exists() and not (tmp_path / "sec_raw").exists()


@pytest.mark.parametrize("explicit_root", [False, True])
def test_combined_sec_hash_covers_complete_holding_context(foundation, tmp_path, explicit_root):
    store, artifacts = foundation
    _us_prices(store, artifacts)
    _capture(foundation)
    annotation = _holding_annotation(tmp_path / "holding.toml")
    extra = ["--holding-context", str(annotation)]
    if explicit_root:
        extra += ["--sec-artifact-root", str(artifacts.root)]
    first = _us_run(store, foundation, extra=extra)
    _holding_annotation(annotation, quantity="0.2")
    second = _us_run(store, foundation, extra=extra)
    assert first.returncode == second.returncode == 2 and not first.stderr
    first_doc, second_doc = json.loads(first.stdout), json.loads(second.stdout)
    assert first_doc["combined_evidence_hash"] != second_doc["combined_evidence_hash"]
    for doc in (first_doc, second_doc):
        assert doc["combined_evidence_version"] == EQUITY_HOLDING_DISPLAY_VERSION
        assert not doc["holding_review"]["holding_management_authorized"]
        assert doc["holding_review"]["comparison_status"] == "BLOCKED"
        digest = doc.pop("combined_evidence_hash")
        assert digest == sha256(financial_input_json(doc).encode()).hexdigest()


def test_explicit_shared_root_is_opt_in_and_offline(foundation, monkeypatch, capsys):
    store, artifacts = foundation
    _us_prices(store, artifacts)
    _capture(foundation)
    baseline = _us_run(store, foundation).stdout

    def no_network(*args, **kwargs):
        raise AssertionError("offline explicit-root read cannot fetch")

    monkeypatch.setattr(prices, "download_snapshot", no_network)
    monkeypatch.setattr(sec, "download_sec_bytes", no_network)
    arguments = _us_arguments(store, foundation, extra=("--sec-artifact-root", str(artifacts.root)))
    monkeypatch.setattr(sys, "argv", arguments)
    with pytest.raises(SystemExit) as stopped:
        runpy.run_path(arguments[0], run_name="__main__")
    assert stopped.value.code == 2
    doc = json.loads(capsys.readouterr().out)
    assert doc["sec_source_selection"]["shared_artifact_root"] is True
    doc.pop("sec_source_selection")
    doc.pop("combined_evidence_hash")
    original = json.loads(baseline)
    original.pop("combined_evidence_hash")
    assert doc == original
    assert _us_run(store, foundation).stdout == baseline


@pytest.mark.parametrize("shared", [False, True])
def test_us_technical_and_sec_display_is_repeatable_read_only_and_unqualified(
    foundation, tmp_path, shared,
):
    store, artifacts = foundation
    price_store = store if shared else SQLiteStore(tmp_path / "prices.sqlite3")
    if not shared:
        price_store.initialize()
    _us_prices(price_store, artifacts)
    _capture(foundation, _xml().replace(TAG.encode(), b"NetIncomeLoss"))
    _concept(foundation, tag="NetIncomeLoss")
    before = {item.path: sha256(item.path.read_bytes()).hexdigest()
              for item in (store, price_store)}
    first = _us_run(price_store, foundation)
    second = _us_run(price_store, foundation)
    assert first.returncode == second.returncode == 2 and not first.stderr
    assert first.stdout == second.stdout
    doc = json.loads(first.stdout)
    assert doc["combined_evidence_version"] == US_SEC_DISPLAY_VERSION
    assert doc["diagnostics"]["macd_dif"] is not None
    assert doc["sec_filing_status"] == "captured_body_unqualified"
    assert doc["sec_filing"]["body_review"]["facts"][0]["value"] == "120000000"
    assert any(row["status"] == "SUPPORTED_OCCURRENCES_AGREE_UNQUALIFIED"
               for row in doc["sec_filing"]["comparisons"])
    assert doc["combined_snapshot_scope"] == ("single_database_snapshot" if shared
                                             else "separate_database_snapshots_shared_cutoff")
    assert doc["issuer_pairing_status"] == "CALLER_SELECTED_UNVERIFIED"
    assert doc["provider_numeric_consistency"] == "NOT_ASSESSED"
    assert doc["sec_freshness_status"] == "UNASSESSED"
    assert all(doc[key] is False for key in ("issuer_to_instrument_verified",
        "combined_inputs_admitted", "valuation_authorized", "financial_scoring_authorized",
        "investment_scoring_authorized", "historical_replay_eligible", "validation_authorized",
        "execution_authorized", "research_report_created", "readiness_promoted"))
    digest = doc.pop("combined_evidence_hash")
    assert digest == sha256(financial_input_json(doc).encode()).hexdigest()
    assert all(sha256(item.path.read_bytes()).hexdigest() == before[item.path]
               for item in (store, price_store))
    assert store.table_count("research_reports") == store.table_count("signals") == 0
    local = (NOW + timedelta(seconds=2)).astimezone(ZoneInfo("Asia/Kuala_Lumpur"))
    assert _us_run(price_store, foundation, at=local).stdout == first.stdout


@pytest.mark.parametrize("kind", ["missing", "future", "failure", "tampered", "conflict"])
def test_us_display_preserves_sec_missing_failures_and_numeric_conflicts(foundation, kind):
    store, artifacts = foundation
    _us_prices(store, artifacts)
    if kind != "missing":
        _capture(foundation, _xml().replace(TAG.encode(), b"NetIncomeLoss"),
                 at=NOW + timedelta(seconds=3) if kind == "future" else NOW + timedelta(seconds=1))
        _concept(foundation, tag="NetIncomeLoss", value=121_000_000 if kind == "conflict"
                 else 120_000_000)
    if kind == "failure":
        _capture(foundation, at=NOW + timedelta(seconds=2), error="http_403")
    if kind == "tampered":
        receipt = read_sec_body_inputs(*foundation, CIK, ACCESSION,
                                       as_of=NOW + timedelta(seconds=2))
        digest = receipt["captures"][-1]["raw_data_hash"]
        (artifacts.root / "sha256" / digest[:2] / f"{digest}.bin").write_bytes(b"{}")
    result = _us_run(store, foundation, extra=("--fundamentals", "--sector-profile", "bank"))
    assert result.returncode == 2 and not result.stderr
    doc = json.loads(result.stdout)
    assert doc["diagnostics"]["macd_dif"] is not None
    assert doc["fundamentals_status"] == "missing"
    expected = {"missing": "missing", "future": "missing", "failure": "http_403",
                "tampered": "rejected_or_ambiguous", "conflict": "captured_body_unqualified"}
    assert doc["sec_filing_status"] == expected[kind]
    assert not doc["financial_scoring_authorized"] and not doc["validation_authorized"]
    if kind == "conflict":
        assert any(row["status"] == "NUMERIC_CONFLICT" for row in doc["sec_filing"]["comparisons"])
    else:
        assert not doc["sec_filing"]["comparisons"]
        assert doc["sec_filing"]["body_review"] is None


def test_us_missing_price_does_not_hide_sec_or_gain_technical_readiness(foundation):
    store, artifacts = foundation
    _capture(foundation)
    _us_prices(store, artifacts)
    _us_prices(store, artifacts, failed=True, at=NOW + timedelta(seconds=2))
    result = _us_run(store, foundation)
    assert result.returncode == 2 and not result.stderr
    doc = json.loads(result.stdout)
    assert doc["diagnostics"]["technical_input_status"] == "MISSING"
    assert doc["diagnostics"]["macd_dif"] is None
    assert doc["sec_filing_status"] == "captured_body_unqualified"
    assert not doc["combined_inputs_admitted"]


@pytest.mark.parametrize("sector", ["nonfinancial", "bank", "securities", "insurance", "unknown"])
def test_us_present_native_financials_and_sec_are_not_automatically_mapped(foundation, sector):
    store, artifacts = foundation
    _us_prices(store, artifacts)
    _capture(foundation, _xml().replace(TAG.encode(), b"NetIncomeLoss"))
    _concept(foundation, tag="NetIncomeLoss")
    # Deliberately incompatible period/value: co-display must not infer a numeric vote.
    payload = {"timeseries": {"error": None, "result": [{
        "meta": {"symbol": ["MSFT"], "type": ["annualNetIncome"]},
        "annualNetIncome": [{"asOfDate": "2025-12-31", "periodType": "12M",
            "currencyCode": "USD", "reportedValue": {"raw": 999}}]}]}}
    at = NOW + timedelta(seconds=1)
    request = ProviderDatasetRequest(financial.DATASET, Market.US, "MSFT", at,
                                    {"start_date": "2020-01-01", "end_date": "2026-10-26"})
    ProviderNeutralIngestionService(store, artifact_store=artifacts, clock=lambda: at).ingest(
        financial.YahooFundamentalSnapshotAdapter(
            download=lambda _: financial.YahooFundamentalCapture(payload), clock=lambda: at),
        request)
    before = sha256(store.path.read_bytes()).hexdigest()
    result = _us_run(store, foundation, extra=("--fundamentals", "--sector-profile", sector))
    assert result.returncode == 2 and not result.stderr
    doc = json.loads(result.stdout)
    assert doc["fundamentals"]["observations"][0]["value"] == "999"
    assert doc["sec_filing_status"] == "captured_body_unqualified"
    assert any(row["status"] == "SUPPORTED_OCCURRENCES_AGREE_UNQUALIFIED"
               for row in doc["sec_filing"]["comparisons"])
    assert doc["requested_sector_profile"] == sector
    assert doc["sector_policy_status"] == "NOT_ADMITTED"
    assert doc["accounting_field_correspondence"] == "NOT_REVIEWED"
    assert doc["provider_numeric_consistency"] == "NOT_ASSESSED"
    assert not doc["financial_scoring_authorized"] and not doc["valuation_authorized"]
    assert not doc["validation_authorized"] and not doc["issuer_to_instrument_verified"]
    assert sha256(store.path.read_bytes()).hexdigest() == before


def test_us_display_is_opt_in_and_never_requests_network(foundation, monkeypatch, capsys):
    store, artifacts = foundation
    _us_prices(store, artifacts)
    arguments = _us_arguments(store, foundation)
    legacy = arguments[:arguments.index("--sec-database")]
    before = subprocess.run([sys.executable, *legacy], capture_output=True, text=True)
    _capture(foundation)
    after = subprocess.run([sys.executable, *legacy], capture_output=True, text=True)
    assert before.stdout == after.stdout and not after.stderr
    assert "sec_filing" not in json.loads(after.stdout)

    def no_network(*args, **kwargs):
        raise AssertionError("retained evidence display must not request network")

    monkeypatch.setattr(prices, "download_snapshot", no_network)
    monkeypatch.setattr(sec, "download_sec_bytes", no_network)
    monkeypatch.setattr(sys, "argv", arguments)
    with pytest.raises(SystemExit) as stopped:
        runpy.run_path(arguments[0], run_name="__main__")
    assert stopped.value.code == 2
    assert json.loads(capsys.readouterr().out)["sec_filing_status"] == "captured_body_unqualified"


@pytest.mark.parametrize("tickers,expected", [
    (["MSFT"], "TICKER_DECLARED_UNVERIFIED"), (["OTHER"], "TICKER_NOT_DECLARED"),
    ([], "NO_DECLARED_TICKERS"), (["MSFT", "MSFT"], "AMBIGUOUS_TICKER_DECLARATIONS"),
])
def test_us_optional_issuer_claims_do_not_promote_pairing_or_change_v1_output(
    foundation, tickers, expected,
):
    store, artifacts = foundation
    _us_prices(store, artifacts)
    payload = _catalog()
    payload.update(name="Synthetic issuer", tickers=tickers, exchanges=["Nasdaq"])
    at = NOW + timedelta(microseconds=1)
    ProviderNeutralIngestionService(store, artifact_store=artifacts, clock=lambda: at).ingest(
        sec.SECSubmissionsAdapter(download=lambda _: sec.SECSubmissionsCapture(payload),
                                  clock=lambda: at),
        ProviderDatasetRequest(sec.DATASET, Market.US, CIK, at))
    _capture(foundation)
    before = store.path.read_bytes()
    legacy = _us_run(store, foundation).stdout
    first = _us_run(store, foundation, extra=("--sec-identity",))
    second = _us_run(store, foundation, extra=("--sec-identity",))
    assert first.returncode == second.returncode == 2 and not first.stderr
    assert first.stdout == second.stdout
    doc = json.loads(first.stdout)
    assert doc["combined_evidence_version"] == US_SEC_IDENTITY_DISPLAY_VERSION
    assert doc["sec_issuer_claims"]["status"] == expected
    assert doc["issuer_pairing_status"] == "CALLER_SELECTED_UNVERIFIED"
    assert not doc["issuer_to_instrument_verified"] and not doc["financial_scoring_authorized"]
    assert not doc["combined_inputs_admitted"] and not doc["execution_authorized"]
    digest = doc.pop("combined_evidence_hash")
    assert digest == sha256(financial_input_json(doc).encode()).hexdigest()
    assert _us_run(store, foundation).stdout == legacy
    assert "sec_issuer_claims" not in json.loads(legacy)
    assert store.path.read_bytes() == before


@pytest.mark.parametrize("shared", [False, True])
def test_us_display_snapshot_scope_is_honest_during_competing_write(
    foundation, tmp_path, monkeypatch, capsys, shared,
):
    from tong_quant.data import global_price_inputs

    store, artifacts = foundation
    price_store = store if shared else SQLiteStore(tmp_path / "prices.sqlite3")
    if not shared:
        price_store.initialize()
    _us_prices(price_store, artifacts)
    _capture(foundation)
    original = global_price_inputs.read_global_price_inputs
    writes = []

    def competing_write(*args, **kwargs):
        result = original(*args, **kwargs)
        _capture((SQLiteStore(store.path), artifacts), error="http_403",
                 at=NOW + timedelta(seconds=2))
        writes.append(True)
        return result

    monkeypatch.setattr(global_price_inputs, "read_global_price_inputs", competing_write)
    arguments = _us_arguments(price_store, foundation)
    monkeypatch.setattr(sys, "argv", arguments)
    with pytest.raises(SystemExit) as stopped:
        runpy.run_path(arguments[0], run_name="__main__")
    assert stopped.value.code == 2 and writes == [True]
    doc = json.loads(capsys.readouterr().out)
    assert doc["sec_filing_status"] == ("captured_body_unqualified" if shared else "http_403")
    assert json.loads(_us_run(price_store, foundation).stdout)["sec_filing_status"] == "http_403"


@pytest.mark.parametrize("options", [
    ["--sec-identity"],
    ["--sec-period", "NetIncomeLoss=2024-07-01/2025-06-30"],
    ["--sec-cik", CIK], ["--sec-accession", ACCESSION], ["--sec-database", "absent.sqlite3"],
    ["--sec-database", "absent.sqlite3", "--sec-cik", CIK],
    ["--sec-database", "absent.sqlite3", "--sec-cik", "bad", "--sec-accession", ACCESSION],
    ["--sec-database", "absent.sqlite3", "--sec-cik", CIK, "--sec-accession", "bad"],
    ["--sec-database", "absent.sqlite3", "--sec-cik", CIK, "--sec-accession", ACCESSION,
     "--market", "hong_kong"],
    ["--sec-database", "absent.sqlite3", "--sec-cik", CIK, "--sec-accession", ACCESSION,
     "--capture"],
])
def test_us_invalid_sec_options_fail_before_database_access(tmp_path, options):
    result = subprocess.run([sys.executable, "scripts/inspect_global_technical.py", "--database",
        str(tmp_path / "absent.sqlite3"), "--artifact-root", str(tmp_path / "raw"),
        "--market", "us", "--symbol", "MSFT", "--as-of", NOW.isoformat(), *options],
        capture_output=True, text=True)
    assert result.returncode == 2 and "error:" in result.stderr and not result.stdout
    assert "Traceback" not in result.stderr
    assert not (tmp_path / "absent.sqlite3").exists()


def _periods(foundation, *, selections=None, at=NOW + timedelta(seconds=2), sector="nonfinancial"):
    return read_sec_period_inputs(*foundation, CIK, ACCESSION, as_of=at,
        selections=selections if selections is not None else (
            SECPeriodSelection(TAG, date(2024, 7, 1), date(2025, 6, 30)),),
        sector_profile=sector)


@pytest.mark.parametrize("invalid", [
    [], ["revenue=2024/2025"], ["NetIncomeLoss=FY2025"], ["NetIncomeLoss=2025-06-30"],
    ["NetIncomeLoss=2025-01-01/2024-12-31"], ["NetIncomeLoss=2025-02-30/2025-06-30"],
    ["NetIncomeLoss =2024-07-01/2025-06-30"], ["NetIncomeLoss=@2025-6-30"],
    ["NetIncomeLoss=@２０２５-06-30"], ["NetIncomeLoss=@2025-06-30"] * 2,
    ["NetIncomeLoss=@2025-06-30"] * 17, [True], ["A" * 129 + "=@2025-06-30"],
])
def test_sec_period_parser_requires_bounded_unique_exact_dates(invalid):
    with pytest.raises(ValueError):
        parse_sec_period_selections(invalid)


def test_sec_period_selections_keep_instant_duration_and_canonical_order():
    raw = ["NetIncomeLoss=2024-07-01/2025-06-30", "Assets=@2025-06-30"]
    first = parse_sec_period_selections(raw)
    assert first == parse_sec_period_selections(list(reversed(raw)))
    assert first[0] == SECPeriodSelection("Assets", None, date(2025, 6, 30))
    assert first[1].period_start == date(2024, 7, 1)
    with pytest.raises(ValueError):
        SECPeriodSelection("NetIncomeLoss", None, datetime(2025, 6, 30))


def test_sec_exact_period_read_keeps_duplicate_occurrences_without_summing_or_annualizing(
    foundation,
):
    extra = f'''<ix:nonFraction name="us-gaap:{TAG}" contextRef="c" unitRef="u"
        decimals="-6" scale="6">120</ix:nonFraction>'''
    _capture(foundation, _xml(extra=extra))
    _concept(foundation)
    before = foundation[0].path.read_bytes()
    source_hash = _read(foundation)["input_hash"]
    result = _periods(foundation)
    assert result["model_version"] == SEC_PERIOD_INPUT_VERSION
    assert result["status"] == "SOURCE_SUBSET_REVIEW" and result["source_bound"]
    assert result["source_input_hash"] == source_hash
    check = result["checks"][0]
    assert check["status"] == "OBSERVED_SUBSET_UNQUALIFIED"
    assert check["duration_calendar_days"] == 365 and check["period_basis"] == "duration"
    assert check["numeric_agreement_within_subset"] is True
    assert [row["value"] for row in check["matching_occurrences"]] == ["120000000"] * 2
    assert not check["amount_aggregation_authorized"]
    assert check["annual_or_quarter_classification"] == "NOT_ADMITTED"
    assert check["statement_and_consolidation_scope"] == "NOT_QUALIFIED"
    assert all(result[key] is False for key in ("issuer_to_instrument_verified",
        "sector_classification_verified", "accounting_definitions_admitted",
        "financial_scoring_authorized", "investment_scoring_authorized",
        "historical_replay_eligible", "validation_authorized", "execution_authorized",
        "research_report_created"))
    assert result["input_hash"] == _periods(foundation)["input_hash"]
    local = (NOW + timedelta(seconds=2)).astimezone(ZoneInfo("Asia/Kuala_Lumpur"))
    assert result["input_hash"] == _periods(foundation, at=local)["input_hash"]
    digest = result.pop("input_hash")
    assert digest == sha256(financial_input_json(result).encode()).hexdigest()
    assert foundation[0].path.read_bytes() == before


@pytest.mark.parametrize("kind,expected", [
    ("wrong_start", "MISSING_EXACT_PERIOD"), ("instant", "MISSING_EXACT_PERIOD"),
    ("missing_tag", "MISSING_EXACT_PERIOD"), ("future", "FUTURE_TARGET"),
    ("after_report_end", "AFTER_FILING_REPORT_END"),
])
def test_sec_periods_never_choose_a_nearby_period_or_infer_quarter_from_annual(
    foundation, kind, expected,
):
    _capture(foundation)
    selection = {
        "wrong_start": SECPeriodSelection(TAG, date(2025, 1, 1), date(2025, 6, 30)),
        "instant": SECPeriodSelection(TAG, None, date(2025, 6, 30)),
        "missing_tag": SECPeriodSelection("Assets", None, date(2025, 6, 30)),
        "future": SECPeriodSelection(TAG, date(2027, 1, 1), date(2027, 12, 31)),
        "after_report_end": SECPeriodSelection(TAG, date(2025, 7, 1), date(2026, 6, 30)),
    }[kind]
    check = _periods(foundation, selections=(selection,))["checks"][0]
    assert check["status"] == expected and check["matching_occurrences"] == []
    assert check["numeric_agreement_within_subset"] is None


@pytest.mark.parametrize("kind,expected", [
    ("conflict", "NUMERIC_CONFLICT"), ("unsupported", "UNSUPPORTED_MATCHING_OCCURRENCE"),
])
def test_sec_period_matching_bad_occurrences_block_favorable_numeric_selection(
    foundation, kind, expected,
):
    extra = f'''<ix:nonFraction name="us-gaap:{TAG}" contextRef="c" unitRef="u"
        decimals="-6" scale="{'99' if kind == 'unsupported' else '6'}">121</ix:nonFraction>'''
    _capture(foundation, _xml(extra=extra))
    check = _periods(foundation)["checks"][0]
    assert check["status"] == expected and len(check["matching_occurrences"]) == 2
    assert not check["numeric_agreement_within_subset"]


def test_sec_periods_keep_unresolved_dimensions_separate_from_supported_subset(foundation):
    context = '''<xbrli:context id="dim"><xbrli:entity><xbrli:identifier
        scheme="http://www.sec.gov/CIK">0000789019</xbrli:identifier><xbrli:segment/>
        </xbrli:entity><xbrli:period><xbrli:startDate>2024-07-01</xbrli:startDate>
        <xbrli:endDate>2025-06-30</xbrli:endDate></xbrli:period></xbrli:context>'''
    extra = context + f'''<ix:nonFraction name="us-gaap:{TAG}" contextRef="dim" unitRef="u"
        decimals="-6" scale="6">999</ix:nonFraction>'''
    _capture(foundation, _xml(extra=extra))
    result = _periods(foundation)
    check = result["checks"][0]
    assert check["status"] == "OBSERVED_SUBSET_UNQUALIFIED"
    assert check["unresolved_tag_contexts_present"] and check["unresolved_tag_occurrence_indices"]
    assert result["unsupported_fact_occurrence_count"] == 1
    assert not result["accounting_definitions_admitted"]


@pytest.mark.parametrize("weeks", [52, 53])
def test_sec_periods_count_native_week_year_dates_without_365_day_or_calendar_ytd_assumption(
    foundation, weeks,
):
    start = date(2024, 7, 1)
    end = start + timedelta(days=weeks * 7 - 1)
    payload = _catalog()
    payload["filings"]["recent"]["reportDate"] = [end.isoformat()]
    at = NOW + timedelta(microseconds=1)
    ProviderNeutralIngestionService(foundation[0], artifact_store=foundation[1],
        clock=lambda: at).ingest(sec.SECSubmissionsAdapter(
            download=lambda _: sec.SECSubmissionsCapture(payload), clock=lambda: at),
            ProviderDatasetRequest(sec.DATASET, Market.US, CIK, at))
    _capture(foundation, _xml().replace(b"2025-06-30", end.isoformat().encode()))
    result = _periods(foundation, selections=(SECPeriodSelection(TAG, start, end),))
    check = result["checks"][0]
    assert check["status"] == "OBSERVED_SUBSET_UNQUALIFIED"
    assert check["duration_calendar_days"] == weeks * 7
    assert check["annual_or_quarter_classification"] == "NOT_ADMITTED"


@pytest.mark.parametrize("kind", ["missing", "future_completion", "failure", "tampered"])
def test_sec_period_reads_keep_source_gaps_and_latest_failure_without_fallback(foundation, kind):
    if kind != "missing":
        _capture(foundation, completed=NOW + timedelta(seconds=3)
                 if kind == "future_completion" else None)
    if kind == "failure":
        _capture(foundation, at=NOW + timedelta(seconds=2), error="http_403")
    if kind == "tampered":
        source = _read(foundation)
        digest = source["captures"][-1]["raw_data_hash"]
        (foundation[1].root / "sha256" / digest[:2] / f"{digest}.bin").write_bytes(b"{}")
    result = _periods(foundation)
    assert result["status"] == "SOURCE_UNAVAILABLE"
    assert result["checks"][0]["status"] == "SOURCE_UNAVAILABLE"
    assert not result["checks"][0]["matching_occurrences"]


@pytest.mark.parametrize("sector", ["nonfinancial", "bank", "securities", "insurance", "unknown"])
def test_us_period_cli_is_sector_explicit_opt_in_and_keeps_previous_hashes(foundation, sector):
    store, artifacts = foundation
    _us_prices(store, artifacts)
    _capture(foundation, _xml().replace(TAG.encode(), b"NetIncomeLoss"))
    options = ("--fundamentals", "--sector-profile", sector)
    previous = _us_run(store, foundation, extra=options).stdout
    before = store.path.read_bytes()
    selections = ("--sec-period", "NetIncomeLoss=2024-07-01/2025-06-30",
                  "--sec-period", "Assets=@2025-06-30")
    first = _us_run(store, foundation, extra=(*options, *selections))
    second = _us_run(store, foundation, extra=(*options, *selections[2:], *selections[:2]))
    assert first.returncode == second.returncode == 2 and not first.stderr
    assert first.stdout == second.stdout
    doc = json.loads(first.stdout)
    assert doc["combined_evidence_version"] == US_SEC_PERIOD_DISPLAY_VERSION
    period_inputs = doc["sec_period_inputs"]
    assert period_inputs["requested_sector_profile"] == sector
    assert period_inputs["checks"][0]["status"] == "MISSING_EXACT_PERIOD"
    assert period_inputs["checks"][1]["status"] == "OBSERVED_SUBSET_UNQUALIFIED"
    assert not period_inputs["sector_classification_verified"]
    assert not doc["financial_scoring_authorized"] and not doc["validation_authorized"]
    assert _us_run(store, foundation, extra=options).stdout == previous
    assert "sec_period_inputs" not in json.loads(previous)
    assert store.path.read_bytes() == before


@pytest.mark.parametrize("selection", ["NetIncomeLoss=FY2025", "bad", "A=@2025-6-30"])
def test_bad_cli_periods_fail_safely_before_database_access(tmp_path, selection):
    result = subprocess.run([sys.executable, "scripts/inspect_global_technical.py", "--database",
        str(tmp_path / "absent.sqlite3"), "--artifact-root", str(tmp_path / "raw"),
        "--market", "us", "--symbol", "MSFT", "--as-of", NOW.isoformat(),
        "--sec-database", str(tmp_path / "absent.sqlite3"), "--sec-cik", CIK,
        "--sec-accession", ACCESSION, "--fundamentals", "--sector-profile", "nonfinancial",
        "--sec-period", selection], capture_output=True, text=True)
    assert result.returncode == 2 and "error:" in result.stderr and not result.stdout
    assert "Traceback" not in result.stderr and not (tmp_path / "absent.sqlite3").exists()


@pytest.mark.parametrize("amount", ["-12", "0", "12"])
def test_sec_periods_preserve_signed_and_zero_amounts_without_financial_judgment(
    foundation, amount,
):
    _capture(foundation, _xml(text=amount))
    result = _periods(foundation)
    check = result["checks"][0]
    assert check["status"] == "OBSERVED_SUBSET_UNQUALIFIED"
    assert check["matching_occurrences"][0]["value"] == str(int(amount) * 1_000_000)
    assert not result["financial_scoring_authorized"]


def test_sec_periods_keep_instant_balance_distinct_from_flow_duration(foundation):
    content = _xml().replace(TAG.encode(), b"Assets").replace(
        b"<xbrli:startDate>2024-07-01</xbrli:startDate>", b"").replace(
        b"<xbrli:endDate>", b"<xbrli:instant>").replace(
        b"</xbrli:endDate>", b"</xbrli:instant>")
    _capture(foundation, content)
    result = _periods(foundation, selections=(SECPeriodSelection("Assets", None,
                                                               date(2025, 6, 30)),))
    check = result["checks"][0]
    assert check["status"] == "OBSERVED_SUBSET_UNQUALIFIED"
    assert check["period_basis"] == "instant" and check["duration_calendar_days"] is None
    assert check["statement_and_consolidation_scope"] == "NOT_QUALIFIED"


def _research_periods(foundation, *, at=NOW + timedelta(seconds=2), sector="nonfinancial"):
    return read_sec_period_research_input(*foundation, CIK, ACCESSION, symbol="MSFT", as_of=at,
        selections=(SECPeriodSelection(TAG, date(2024, 7, 1), date(2025, 6, 30)),),
        sector_profile=sector)


def test_sec_period_research_receipt_is_copied_context_bound_and_unqualified(foundation):
    _capture(foundation)
    before = foundation[0].path.read_bytes()
    bound = _research_periods(foundation)
    receipt = bound.document()
    assert receipt == json.loads(financial_input_json(_periods(foundation)))
    receipt["checks"][0]["matching_occurrences"][0]["value"] = "999"
    assert receipt != bound.document()
    local = bound.as_of.astimezone(ZoneInfo("Asia/Kuala_Lumpur"))
    bound.validate_context(symbol="MSFT", market=Market.US, as_of=local)
    assert bound.binding_hash == _research_periods(foundation, at=local).binding_hash
    assert bound.binding_hash != SECPeriodResearchInput(
        bound.receipt_json, "OTHER", bound.sector_profile).binding_hash
    assert not bound.document()["issuer_to_instrument_verified"]
    assert foundation[0].path.read_bytes() == before


@pytest.mark.parametrize("defect", [
    "checksum", "trust", "precision", "version", "source_version", "sector", "scoring",
    "validation", "identity", "future_capture", "missing_parent", "parent_future", "selection",
    "unit", "namespace", "entity", "amount", "future_fact", "agreement", "aggregation",
    "annual", "unresolved", "duplicate_row", "source_count", "capture_selection", "secret",
])
def test_sec_period_research_rejects_mutation_even_with_recomputed_public_checksum(
    foundation, defect,
):
    _capture(foundation)
    bound = _research_periods(foundation)
    document = bound.document()
    check = document["checks"][0]
    row = check["matching_occurrences"][0]
    if defect in {"trust", "precision", "version", "source_version", "sector"}:
        key, value = {"trust": ("trust_ceiling", "HIGH"),
            "precision": ("availability_precision", "exact"), "version": ("model_version", "old"),
            "source_version": ("source_review_version", "old"),
            "sector": ("requested_sector_profile", "bank")}[defect]
        document[key] = value
    elif defect in {"scoring", "validation", "identity"}:
        document[{"scoring": "financial_scoring_authorized", "validation": "validation_authorized",
                  "identity": "issuer_to_instrument_verified"}[defect]] = True
    elif defect == "future_capture":
        document["source_captures"][-1]["available_at"] = (
            bound.as_of + timedelta(seconds=1)).isoformat()
    elif defect == "missing_parent":
        document["source_parent_binding"] = None
    elif defect == "parent_future":
        document["source_parent_binding"]["parent_available_at"] = bound.as_of.isoformat()
    elif defect == "selection":
        check["period_start"] = None
    elif defect in {"unit", "namespace", "entity", "amount"}:
        key, value = {"unit": ("unit", "CNY"), "namespace": ("namespace", "wrong"),
            "entity": ("entity_cik", "0000000001"), "amount": ("value", "NaN")}[defect]
        row[key] = value
    elif defect == "future_fact":
        check["period_end"] = row["period_end"] = "2027-06-30"
    elif defect == "agreement":
        check["numeric_agreement_within_subset"] = False
    elif defect == "aggregation":
        check["amount_aggregation_authorized"] = True
    elif defect == "annual":
        check["annual_or_quarter_classification"] = "ANNUAL"
    elif defect == "unresolved":
        check["unresolved_tag_occurrence_indices"] = [1]
        check["unresolved_tag_contexts_present"] = True
    elif defect == "duplicate_row":
        check["matching_occurrences"].append(dict(row))
        document["selected_fact_occurrence_count"] = 2
    elif defect == "source_count":
        document["selected_fact_occurrence_count"] = True
    elif defect == "capture_selection":
        document["source_evidence_id"] = "a" * 64
    elif defect == "secret":
        document["token"] = "synthetic forbidden assignment"
    content = {key: value for key, value in document.items() if key != "input_hash"}
    body_hash = sha256(financial_input_json(content).encode()).hexdigest()
    document["input_hash"] = "a" * 64 if defect == "checksum" else body_hash
    with pytest.raises(ValueError):
        SECPeriodResearchInput(financial_input_json(document), "MSFT", "nonfinancial")


@pytest.mark.parametrize("state", ["missing", "failed", "unsupported_xml"])
def test_sec_research_receipt_preserves_unavailable_states_and_cutoff(foundation, state):
    if state == "failed":
        _capture(foundation, error="http_403")
    elif state == "unsupported_xml":
        _capture(foundation, b"<html>")
    bound = _research_periods(foundation)
    assert bound.document()["status"] == "SOURCE_UNAVAILABLE"
    assert bound.document()["checks"][0]["matching_occurrences"] == []
    assert bound.as_of == NOW + timedelta(seconds=2)


@pytest.mark.parametrize("raw", ["[]", "{}", " " * 2_097_153])
def test_sec_research_receipt_rejects_malformed_or_oversized_json(raw):
    with pytest.raises(ValueError):
        SECPeriodResearchInput(raw, "MSFT", "nonfinancial")
