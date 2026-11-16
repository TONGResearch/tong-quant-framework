"""Explicit HK/MY PDF retention is not issuer, publication or accounting approval."""

import base64
import json
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock
from urllib.error import HTTPError, URLError
from zoneinfo import ZoneInfo

import pytest

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.global_document_inputs import read_global_document_inputs
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.providers import global_documents as documents
from tong_quant.data.providers.contracts import ProviderDatasetRequest
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market

NOW = datetime(2026, 10, 28, tzinfo=UTC)
HK_URL = "https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0409/2026040901231.pdf"
MY_URL = ("https://www.maybank.com/iwov-resources/documents/pdf/annual-report/2025/"
          "maybank-ar2025-financial-statements.pdf")
PDF = b"%PDF-1.7\nSynthetic bytes, NOT a validated PDF document.\n%%EOF"


def _request(market=Market.HONG_KONG, at=NOW):
    malaysia = market is Market.MALAYSIA
    return ProviderDatasetRequest(documents.DATASET, market, "1155.KL" if malaysia else "0700.HK",
        at, {"document_url": MY_URL if malaysia else HK_URL,
             "landing_url": ("https://www.maybank.com/en/investor-relations/"
                             "financial-overview/annual-reports.page") if malaysia else HK_URL,
             "issuer_label": "Synthetic annotation", "period_end": "2025-12-31",
             "document_kind": "annual_financial_statements" if malaysia else "annual_report"})


@pytest.fixture
def foundation(tmp_path):
    store = SQLiteStore(tmp_path / "documents.sqlite3")
    store.initialize()
    return store, FileSystemArtifactStore(tmp_path / "raw")


def _ingest(foundation, *, market=Market.HONG_KONG, at=NOW, content=PDF, error="", completed=None):
    capture = documents.DocumentCapture(None if error else content, error)
    return ProviderNeutralIngestionService(foundation[0], artifact_store=foundation[1],
        clock=lambda: completed or at).ingest(documents.GlobalDocumentAdapter(market,
            download=lambda _: capture, clock=lambda: at), _request(market, at))


def _read(foundation, market=Market.HONG_KONG, at=NOW):
    request = _request(market, at)
    return read_global_document_inputs(*foundation, market, request.subject,
                                       request.parameters["document_url"], as_of=at)


@pytest.mark.parametrize("market", [Market.HONG_KONG, Market.MALAYSIA])
def test_pdf_bytes_and_manual_annotations_are_preserved_without_authority(foundation, market):
    _ingest(foundation, market=market)
    _ingest(foundation, market=market)
    before = foundation[0].path.read_bytes()
    result = _read(foundation, market)
    assert result["status"] == "captured_pdf_unqualified" and result["source_bound"]
    assert len(result["captures"]) == 1  # Idempotence is scoped to the same capture identity.
    envelope = json.loads(foundation[1].read_content(result["captures"][0]["raw_data_hash"],
                         "application/json", max_bytes=documents.MAX_ENVELOPE_BYTES))
    assert base64.b64decode(envelope["document_base64"], validate=True) == PDF
    assert result["annotations"]["issuer_label"] == "Synthetic annotation"
    assert result["trust_ceiling"] == "LOW" and result["availability_precision"] == "retrieval_time"
    assert all(result[name] is False for name in ("published_at_known", "landing_link_verified",
        "issuer_to_instrument_verified", "numeric_extraction_authorized",
        "financial_scoring_authorized", "validation_authorized", "historical_replay_eligible",
        "execution_authorized"))
    assert result["input_hash"] == _read(foundation, market)["input_hash"]
    assert result["input_hash"] == _read(foundation, market,
        NOW.astimezone(ZoneInfo("Asia/Kuala_Lumpur")))["input_hash"]
    assert before == foundation[0].path.read_bytes()


@pytest.mark.parametrize("url", ["http://www1.hkexnews.hk/listedco/listconews/sehk/2026/0409/x.pdf",
    HK_URL + "?token=synthetic", HK_URL + "#fragment", HK_URL.replace("www1.", "www1.evil."),
    HK_URL.replace("https://", "https://user@"), MY_URL,
    HK_URL.replace("2026040901231.pdf", "../2026040901231.pdf"),
    "file:///tmp/report.pdf", HK_URL.replace(".pdf", ".htm")])
def test_no_arbitrary_url_redirect_or_market_crossing(url):
    with pytest.raises(ValueError):
        documents.validate_document_url(Market.HONG_KONG, url)


@pytest.mark.parametrize("values", [{"issuer_label": ""}, {"issuer_label": "x\nvalue"},
    {"period_end": "2027-01-01"}, {"period_end": "2025-02-30"},
    {"document_kind": "buy_signal"}, {"landing_url": "https://example.invalid"},
    {"issuer_label": "api_key=synthetic-not-real"}, {"issuer_label": False}])
def test_unsupported_or_sensitive_annotations_are_rejected(values):
    request = _request()
    with pytest.raises(ValueError):
        documents.validate_request(replace(request, parameters={**request.parameters, **values}))


@pytest.mark.parametrize("changes", [{"subject": "MSFT"}, {"market": Market.US},
    {"dataset": "global_native_fundamental_snapshot"}, {"parameters": {}}])
def test_no_equity_or_dataset_identity_guessing(changes):
    with pytest.raises(ValueError):
        documents.validate_request(replace(_request(), **changes))


@pytest.mark.parametrize("content,error", [(None, ""), (b"", ""), (PDF, "http_403"),
    (None, "raw_exception_detail"), (b"<html>denied</html>", ""),
    (b"%PDF-1.7\npassword=synthetic-not-real", "")])
def test_invalid_and_sensitive_content_is_not_hidden_inside_base64(content, error):
    with pytest.raises(ValueError):
        documents.DocumentCapture(content, error)


def test_latest_failure_no_favorable_fallback_and_explicit_history_survives(foundation):
    _ingest(foundation)
    later = NOW + timedelta(seconds=1)
    _ingest(foundation, at=later, error="http_403")
    result = _read(foundation, at=later)
    assert result["status"] == "http_403" and result["source_bound"]
    assert result["document_sha256"] is None and len(result["captures"]) == 2
    assert _read(foundation)["status"] == "captured_pdf_unqualified"


@pytest.mark.parametrize("market", [Market.HONG_KONG, Market.MALAYSIA])
def test_same_issuer_documents_and_their_latest_failures_are_isolated(foundation, market):
    _ingest(foundation, market=market)
    later, failed_at = NOW + timedelta(seconds=1), NOW + timedelta(seconds=2)
    original = _read(foundation, market, at=failed_at)
    request = _request(market, later)
    sibling_url = (request.parameters["document_url"].replace("01231.pdf", "01232.pdf")
        if market is Market.HONG_KONG else MY_URL.replace(".pdf", "-integrated.pdf"))
    request = replace(request, parameters={**request.parameters,
        "document_url": sibling_url, "document_kind": "annual_report",
        "landing_url": sibling_url if market is Market.HONG_KONG
            else request.parameters["landing_url"]})
    for at, capture in ((later, documents.DocumentCapture(PDF + b"\nSibling edition")),
                       (failed_at, documents.DocumentCapture(None, "http_403"))):
        ProviderNeutralIngestionService(foundation[0], artifact_store=foundation[1],
            clock=lambda at=at: at).ingest(documents.GlobalDocumentAdapter(market,
                download=lambda _, capture=capture: capture, clock=lambda at=at: at),
                replace(request, as_of=at))
    assert _read(foundation, market, at=failed_at) == original
    assert read_global_document_inputs(*foundation, market, request.subject, sibling_url,
                                        as_of=NOW)["status"] == "missing"
    sibling = read_global_document_inputs(*foundation, market, request.subject, sibling_url,
                                          as_of=later)
    assert sibling["source_bound"] and sibling["document_sha256"] != original["document_sha256"]
    assert sibling["annotations"]["document_kind"] == "annual_report"
    failed = read_global_document_inputs(*foundation, market, request.subject, sibling_url,
                                         as_of=failed_at)
    assert failed["source_bound"] and failed["status"] == "http_403"
    assert failed["document_sha256"] is None and len(failed["captures"]) == 2


@pytest.mark.parametrize("defect", ["tie", "tamper", "future_completion"])
def test_latest_unverified_capture_cannot_be_used(foundation, defect):
    _ingest(foundation)
    later = NOW + timedelta(seconds=1)
    if defect == "tie":
        _ingest(foundation, at=later)
    _ingest(foundation, content=PDF + b"\nNew version", at=later,
            completed=later + timedelta(seconds=1) if defect == "future_completion" else later)
    if defect == "tamper":
        digest = _read(foundation, at=later)["captures"][-1]["raw_data_hash"]
        (foundation[1].root / "sha256" / digest[:2] / f"{digest}.bin").write_bytes(b"{}")
    result = _read(foundation, at=later)
    assert result["status"] == "rejected_or_ambiguous" and not result["source_bound"]


def test_future_capture_does_not_enter_past_context_and_market_reads_are_separate(foundation):
    _ingest(foundation, at=NOW + timedelta(seconds=1))
    assert _read(foundation)["status"] == "missing"
    assert _read(foundation, Market.MALAYSIA, at=NOW + timedelta(seconds=1))["status"] == "missing"


@pytest.mark.parametrize("error,attempts", [(403, 1), (404, 1), (429, 2), (503, 2),
                                          ("network", 2)])
def test_transport_errors_are_sanitized_and_retries_bounded(monkeypatch, error, attempts):
    monkeypatch.setattr(documents, "sleep", lambda _: None)
    opener = Mock()
    opener.open.side_effect = (URLError("Do not retain token=synthetic") if error == "network"
        else HTTPError(HK_URL, error, "Do not retain secret=synthetic", {}, None))
    monkeypatch.setattr(documents, "build_opener", lambda *_: opener)
    result = documents.download_document(_request())
    assert result.content is None and result.error_code in {
        "http_403", "http_404", "http_429", "http_error", "network_unavailable"}
    assert opener.open.call_count == attempts
    assert "synthetic" not in result.error_code


@pytest.mark.parametrize("raw,expected", [(PDF, ""), (b"", "empty_response"),
    (b"123456789", "response_too_large"), (b"denied", "invalid_pdf_payload")])
def test_bounded_transport_requires_pdf_bytes_not_http_success(monkeypatch, raw, expected):
    monkeypatch.setattr(documents, "sleep", lambda _: None)
    monkeypatch.setattr(documents, "MAX_BYTES", 8 if expected == "response_too_large" else 1024)
    reply = Mock()
    reply.__enter__ = Mock(return_value=reply)
    reply.__exit__ = Mock(return_value=False)
    reply.read.return_value = raw
    opener = Mock()
    opener.open.return_value = reply
    monkeypatch.setattr(documents, "build_opener", lambda *_: opener)
    result = documents.download_document(_request())
    assert result.error_code == expected
    assert result.content == (None if expected else PDF)
    headers = dict(opener.open.call_args.args[0].header_items())
    assert "Authorization" not in headers and "Cookie" not in headers


def test_provider_market_and_naive_clock_are_rejected():
    with pytest.raises(ValueError):
        documents.GlobalDocumentAdapter(Market.MALAYSIA).fetch(_request())
    with pytest.raises(ValueError):
        documents.GlobalDocumentAdapter(Market.HONG_KONG,
            download=lambda _: documents.DocumentCapture(PDF),
            clock=lambda: NOW.replace(tzinfo=None)).fetch(_request())


def test_offline_cli_is_explicit_and_does_not_change_database(foundation):
    _ingest(foundation)
    store, artifacts = foundation
    before = store.path.read_bytes()
    args = [sys.executable, "scripts/inspect_global_document.py", "--database", str(store.path),
        "--artifact-root", str(artifacts.root), "--market", Market.HONG_KONG.value,
        "--subject", "0700.HK", "--document-url", HK_URL]
    result = subprocess.run([*args, "--as-of", NOW.isoformat()], capture_output=True, text=True)
    assert result.returncode == 2 and not result.stderr
    assert json.loads(result.stdout)["source_bound"]
    assert store.path.read_bytes() == before
    assert "error:" in subprocess.run(args, capture_output=True, text=True).stderr
    assert "error:" in subprocess.run([*args, "--capture"], capture_output=True, text=True).stderr
