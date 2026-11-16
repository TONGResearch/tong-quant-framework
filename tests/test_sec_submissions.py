"""SEC metadata receipts never backdate availability or qualify financial scores."""

import json
import subprocess
import sys
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from io import BytesIO
from unittest.mock import Mock
from urllib.error import HTTPError, URLError
from zoneinfo import ZoneInfo

import pytest

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.providers import sec_submissions as sec
from tong_quant.data.providers.contracts import ProviderDatasetRequest
from tong_quant.data.sec_filing_inputs import read_sec_filing_inputs, read_sec_issuer_claims
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market
from tong_quant.version import SEC_ISSUER_CLAIMS_VERSION

NOW = datetime(2026, 10, 27, 10, tzinfo=UTC)
CIK = "0000789019"
CONTACT = "TongQuant contact@example.com"


def _request(at=NOW):
    return ProviderDatasetRequest(sec.DATASET, Market.US, CIK, at)


def _payload():
    return {"cik": 789019, "name": "Synthetic issuer", "tickers": ["MSFT"], "filings": {
        "recent": {"accessionNumber": ["0001193125-25-123456", "0001193125-25-123457"],
            "filingDate": ["2025-07-30", "2025-08-01"],
            "reportDate": ["2025-06-30", "2025-06-30"],
            "acceptanceDateTime": ["2025-07-30T20:05:12Z", "2025-08-01T20:05:12+00:00"],
            "form": ["10-K", "10-K/A"], "primaryDocument": ["annual.htm", "amendment.htm"]},
        "files": [{"name": f"CIK{CIK}-submissions-001.json", "filingCount": 2,
                   "filingFrom": "2020-01-01", "filingTo": "2021-01-01"}]}}


@pytest.fixture
def foundation(tmp_path):
    store = SQLiteStore(tmp_path / "sec.sqlite3")
    store.initialize()
    return store, FileSystemArtifactStore(tmp_path / "raw")


def _ingest(foundation, capture=None, at=NOW, completed=None):
    store, artifacts = foundation
    return ProviderNeutralIngestionService(store, artifact_store=artifacts,
        clock=lambda: completed or at).ingest(sec.SECSubmissionsAdapter(
            download=lambda _: capture or sec.SECSubmissionsCapture(_payload()),
            clock=lambda: at), _request(at))


def _read(foundation, at=NOW):
    return read_sec_filing_inputs(*foundation, CIK, as_of=at)


@pytest.mark.parametrize("changes", [{"subject": "MSFT"}, {"subject": "789019"},
    {"subject": "0000000000"}, {"subject": "００００７８９０１９"},
    {"subject": "../789019"}, {"market": Market.CHINA_A}, {"dataset": "companyfacts"},
    {"parameters": {"token": "synthetic-prohibited"}}])
def test_request_requires_explicit_issuer_not_ticker_or_guessed_mapping(changes):
    from dataclasses import replace
    with pytest.raises(ValueError):
        sec.submissions_url(replace(_request(), **changes))


def test_metadata_preserves_amendment_vintages_without_publication_or_numeric_revision():
    result = sec.normalize_submissions(sec.SECSubmissionsCapture(_payload()), _request(), NOW)
    assert result["status"] == "observed_metadata_unqualified"
    assert result["recent_row_count"] == 2
    assert [row["amendment_label"] for row in result["filings"]] == [False, True]
    for row in result["filings"]:
        assert row["available_at"] == NOW.isoformat()
        assert row["published_at"] is row["numeric_revision"] is None
        assert row["restatement_verified"] is False
    assert result["filings"][0]["acceptanceDateTime"].endswith("Z")
    assert result["filings"][0]["acceptance_at"] == "2025-07-30T20:05:12+00:00"
    assert result["older_pages"][0]["capture_status"] == "NOT_CAPTURED"
    assert result["historical_continuity_verified"] is False
    assert result["issuer_to_instrument_verified"] is False


@pytest.mark.parametrize("defect", ["cik", "cik_bool", "cik_unicode", "column_missing",
    "column_ragged", "columns_oversize", "files_url", "files_wrong_cik", "files_dates",
    "files_bool", "files_missing"])
def test_invalid_envelope_is_retained_but_no_metadata_selected(defect):
    payload = _payload()
    recent = payload["filings"]["recent"]
    if defect.startswith("cik"):
        payload["cik"] = {"cik": 1, "cik_bool": True, "cik_unicode": "７８９０１９"}[defect]
    elif defect == "column_missing":
        del recent["acceptanceDateTime"]
    elif defect == "column_ragged":
        recent["reportDate"].pop()
    elif defect == "columns_oversize":
        for key in recent:
            recent[key] = [recent[key][0]] * 10001
    elif defect == "files_url":
        payload["filings"]["files"][0]["name"] = "https://example.invalid/private"
    elif defect == "files_wrong_cik":
        payload["filings"]["files"][0]["name"] = "CIK0000000001-submissions-001.json"
    elif defect == "files_dates":
        payload["filings"]["files"][0]["filingTo"] = "2019-01-01"
    elif defect == "files_bool":
        payload["filings"]["files"][0]["filingCount"] = True
    else:
        del payload["filings"]["files"]
    result = sec.normalize_submissions(sec.SECSubmissionsCapture(payload), _request(), NOW)
    assert result["status"] == "invalid_response"
    assert result["filings"] == []


@pytest.mark.parametrize("field,value", [("acceptanceDateTime", "2025-07-30T20:05:12"),
    ("acceptanceDateTime", "2026-10-27T10:00:00.000001Z"),
    ("reportDate", "2027-01-01"),
    ("filingDate", "not-a-date"), ("accessionNumber", "bad"), ("form", True),
    ("primaryDocument", "../private.htm"), ("primaryDocument", "/private.htm"),
    ("primaryDocument", "https://example.invalid/body.htm"),
    ("primaryDocument", "folder//body.htm")])
def test_bad_metadata_rows_preserve_rejections_without_timestamp_guess(field, value):
    payload = _payload()
    payload["filings"]["recent"][field][1] = value
    result = sec.normalize_submissions(sec.SECSubmissionsCapture(payload), _request(), NOW)
    assert result["status"] == "partial_metadata"
    assert len(result["filings"]) == 2
    assert result["filings"][1]["status"] != "OBSERVED_METADATA_UNQUALIFIED"
    assert result["filings"][1]["published_at"] is None
    assert result["filings"][1][field] == value


def test_submission_agent_prefix_relative_document_and_empty_report_date_are_not_guessed():
    payload = _payload()
    row = payload["filings"]["recent"]
    row["primaryDocument"][0] = "xslF345X05/ownership.xml"
    row["reportDate"][0] = ""
    row["form"][0] = "4"
    result = sec.normalize_submissions(sec.SECSubmissionsCapture(payload), _request(), NOW)
    assert result["filings"][0]["status"] == "OBSERVED_METADATA_UNQUALIFIED"
    assert result["filings"][0]["reportDate"] == ""


def test_duplicate_accessions_remain_visible_and_ambiguous():
    payload = _payload()
    payload["filings"]["recent"]["accessionNumber"][1] = "0001193125-25-123456"
    result = sec.normalize_submissions(sec.SECSubmissionsCapture(payload), _request(), NOW)
    assert len(result["filings"]) == 2
    assert all(row["status"] == "DUPLICATE_ACCESSION" for row in result["filings"])


def test_official_filing_date_label_is_not_a_publication_or_availability_timestamp():
    payload = _payload()
    row = payload["filings"]["recent"]
    row["filingDate"][1] = "2026-10-28"
    row["acceptanceDateTime"][1] = "2026-10-27T09:59:59Z"
    result = sec.normalize_submissions(sec.SECSubmissionsCapture(payload), _request(), NOW)
    assert result["status"] == "observed_metadata_unqualified"
    assert result["filings"][1]["future_filing_date_label"] is True
    assert result["filings"][1]["available_at"] == NOW.isoformat()
    assert result["filings"][1]["published_at"] is None


@pytest.mark.parametrize("form", ["DEF 14A", "DEFA14A", "8-K", "4"])
def test_known_prospective_event_date_does_not_become_future_information(form):
    payload = _payload()
    rows = payload["filings"]["recent"]
    rows["form"][1] = form
    rows["reportDate"][1] = "2026-12-08"
    current = sec.normalize_submissions(sec.SECSubmissionsCapture(payload), _request(), NOW)
    assert current["status"] == "observed_metadata_unqualified"
    row = current["filings"][1]
    assert row["reportDate"] == "2026-12-08"
    assert row["report_date_role"] == "FORM_SPECIFIC_DATE_UNQUALIFIED"
    assert row["future_report_date_label"] is True
    assert row["published_at"] is None and row["available_at"] == NOW.isoformat()
    legacy = sec.normalize_submissions(sec.SECSubmissionsCapture(payload), _request(), NOW,
                                       version=sec.LEGACY_VERSION)
    assert legacy["status"] == "partial_metadata"
    assert legacy["filings"][1]["status"] == "FUTURE_METADATA"
    assert "report_date_role" not in legacy["filings"][1]


def test_legacy_capture_keeps_its_original_payload_and_remains_reconstructible(foundation):
    payload = _payload()
    payload["filings"]["recent"]["form"][1] = "DEF 14A"
    payload["filings"]["recent"]["reportDate"][1] = "2026-12-08"
    store, artifacts = foundation
    adapter = sec.SECSubmissionsAdapter(download=lambda _: sec.SECSubmissionsCapture(payload),
                                      clock=lambda: NOW, model_version=sec.LEGACY_VERSION)
    ProviderNeutralIngestionService(store, artifact_store=artifacts,
                                   clock=lambda: NOW).ingest(adapter, _request())
    result = _read(foundation)
    assert result["source_bound"] and result["status"] == "partial_metadata"
    assert result["filings"][1]["status"] == "FUTURE_METADATA"


@pytest.mark.parametrize("identity,expected", [(None, "access_identity_missing"),
    ("TongQuant", "access_identity_invalid"),
    ("TongQuant contact@example.com\r\nX-Injected: yes", "access_identity_invalid"),
    ("TongQuant contact@example.com token=synthetic", "access_identity_invalid")])
def test_identity_is_environment_only_and_invalid_identity_never_reaches_network(
    monkeypatch, identity, expected,
):
    if identity is None:
        monkeypatch.delenv(sec.ACCESS_IDENTITY_ENV, raising=False)
    else:
        monkeypatch.setenv(sec.ACCESS_IDENTITY_ENV, identity)
    opener = Mock()
    monkeypatch.setattr(sec, "build_opener", opener)
    assert sec.download_submissions(_request()).error_code == expected
    opener.assert_not_called()


@pytest.mark.parametrize("defect", ["none", "oversize", "invalid_json", "secret", "echo",
                                   "duplicate_keys"])
def test_http_capture_is_bounded_and_never_retains_access_identity(monkeypatch, defect):
    monkeypatch.setenv(sec.ACCESS_IDENTITY_ENV, CONTACT)
    payload = _payload()
    if defect == "secret":
        payload["password"] = "synthetic-prohibited"
    elif defect == "echo":
        payload["echo"] = "contact@example.com"
    raw = json.dumps(payload).encode()
    if defect == "oversize":
        raw = b"x" * (sec.MAX_BYTES + 1)
    elif defect == "invalid_json":
        raw = b"invalid-json"
    elif defect == "duplicate_keys":
        raw = b'{"cik":789019,"cik":1}'
    reply = Mock(wraps=BytesIO(raw))
    reply.__enter__ = Mock(return_value=reply)
    reply.__exit__ = Mock(return_value=False)
    opener = Mock()
    opener.open.return_value = reply
    monkeypatch.setattr(sec, "build_opener", Mock(return_value=opener))
    monkeypatch.setattr(sec, "sleep", Mock())
    capture = sec.download_submissions(_request())
    assert capture.error_code == ("" if defect == "none" else "invalid_decoded_response")
    reply.read.assert_called_once_with(sec.MAX_BYTES + 1)
    call = opener.open.call_args
    assert call.args[0].full_url == f"https://data.sec.gov/submissions/CIK{CIK}.json"
    assert call.args[0].get_header("User-agent") == CONTACT
    assert call.kwargs["timeout"] == 10
    assert "contact@example.com" not in repr(capture)


@pytest.mark.parametrize("code,attempts", [(403, 1), (404, 1), (429, 2), (500, 2), (302, 1)])
def test_http_failures_are_sanitized_and_retries_are_bounded(monkeypatch, code, attempts):
    monkeypatch.setenv(sec.ACCESS_IDENTITY_ENV, CONTACT)
    opener = Mock()
    opener.open.side_effect = HTTPError("https://data.sec.gov", code, CONTACT, {}, None)
    monkeypatch.setattr(sec, "build_opener", Mock(return_value=opener))
    pause = Mock()
    monkeypatch.setattr(sec, "sleep", pause)
    result = sec.download_submissions(_request())
    assert opener.open.call_count == attempts
    assert result.error_code == (f"http_{code}" if code in {403, 404, 429} else "http_error")
    assert "contact@example.com" not in repr(result)
    assert [call.args[0] for call in pause.call_args_list] == [1, 5][:attempts]
    assert sec._NoRedirect().redirect_request(None, None, 302, "", {}, "https://elsewhere") is None


def test_network_exception_never_leaks_contact(monkeypatch):
    monkeypatch.setenv(sec.ACCESS_IDENTITY_ENV, CONTACT)
    opener = Mock()
    opener.open.side_effect = URLError(CONTACT)
    monkeypatch.setattr(sec, "build_opener", Mock(return_value=opener))
    monkeypatch.setattr(sec, "sleep", Mock())
    result = sec.download_submissions(_request())
    assert result.error_code == "network_unavailable"
    assert "contact@example.com" not in repr(result)
    assert opener.open.call_count == 2


def test_retained_reconstruction_is_pit_safe_idempotent_and_read_only(foundation):
    _ingest(foundation)
    _ingest(foundation)
    before = foundation[0].path.read_bytes()
    result = _read(foundation)
    assert result["status"] == "observed_metadata_unqualified" and result["source_bound"]
    assert len(result["filings"]) == 2
    assert _read(foundation, NOW - timedelta(microseconds=1))["status"] == "missing"
    assert result["input_hash"] == _read(foundation)["input_hash"]
    assert result["input_hash"] == _read(
        foundation, NOW.astimezone(ZoneInfo("Asia/Kuala_Lumpur")))["input_hash"]
    assert result["trust_ceiling"] == "LOW"
    assert result["availability_precision"] == "retrieval_time"
    assert result["financial_scoring_authorized"] is result["historical_replay_eligible"] is False
    assert foundation[0].path.read_bytes() == before
    assert foundation[0].table_count("provider_evidence_records") == 1
    for table in ("fundamental_facts", "daily_bars", "research_reports", "signals"):
        assert foundation[0].table_count(table) == 0
    capability = sec.SECSubmissionsAdapter().capabilities()[0]
    assert capability.trust_level is DataTrustLevel.LOW
    assert capability.availability_precision is AvailabilityPrecision.RETRIEVAL_TIME
    assert capability.historical_continuity is False


@pytest.mark.parametrize("latest", ["failed", "invalid", "tie", "tampered", "unfinished"])
def test_newest_bad_capture_never_uses_old_favorable_metadata(foundation, latest):
    _ingest(foundation)
    later = NOW + timedelta(seconds=1)
    if latest == "failed":
        capture = sec.SECSubmissionsCapture(None, "http_403")
    else:
        payload = _payload()
        payload["cik"] = 1
        capture = sec.SECSubmissionsCapture(payload)
    if latest == "tie":
        _ingest(foundation, at=later)
    _ingest(foundation, capture, at=later,
            completed=later + timedelta(seconds=1) if latest == "unfinished" else later)
    if latest == "tampered":
        result = _read(foundation, later)
        digest = result["captures"][-1]["raw_data_hash"]
        path = foundation[1].root / "sha256" / digest[:2] / f"{digest}.bin"
        path.write_bytes(b"{}")
    result = _read(foundation, later)
    assert result["filings"] == []
    assert len(result["captures"]) >= 2
    assert _read(foundation)["status"] == "observed_metadata_unqualified"


def test_cli_read_only_requires_cutoff_and_returns_unqualified_status(foundation):
    _ingest(foundation)
    store, artifacts = foundation
    before = store.path.read_bytes()
    args = [sys.executable, "scripts/inspect_sec_filings.py", "--database", str(store.path),
            "--artifact-root", str(artifacts.root), "--cik", CIK]
    result = subprocess.run([*args, "--as-of", NOW.isoformat()], capture_output=True, text=True)
    assert result.returncode == 2 and not result.stderr
    assert json.loads(result.stdout)["status"] == "observed_metadata_unqualified"
    assert store.path.read_bytes() == before
    for more in ([], ["--capture", "--as-of", NOW.isoformat()]):
        invalid = subprocess.run([*args, *more], capture_output=True, text=True)
        assert invalid.returncode == 2 and "error:" in invalid.stderr


def _claims(foundation, *, symbol="MSFT", at=NOW):
    return read_sec_issuer_claims(*foundation, CIK, symbol=symbol, as_of=at)


def test_issuer_declarations_are_exact_read_only_and_never_identity_approval(foundation):
    payload = _payload()
    payload["exchanges"] = ["Nasdaq"]
    _ingest(foundation, sec.SECSubmissionsCapture(payload))
    before = foundation[0].path.read_bytes()
    catalog = _read(foundation)
    result = _claims(foundation)
    assert result["model_version"] == SEC_ISSUER_CLAIMS_VERSION
    assert result["status"] == "TICKER_DECLARED_UNVERIFIED" and result["source_bound"]
    assert result["declared_tickers"] == ["MSFT"]
    assert result["declared_exchanges"] == ["Nasdaq"]
    assert result["issuer_name"] == "Synthetic issuer"
    assert result["exact_ticker_match_indices"] == [0]
    assert result["catalog_input_hash"] == catalog["input_hash"]
    assert result["catalog_evidence_id"] == catalog["selected_evidence_id"]
    assert result["catalog_raw_data_hash"] == catalog["captures"][0]["raw_data_hash"]
    assert result["exchange_association_status"] == "NOT_INFERRED"
    assert result["freshness"] == "UNASSESSED" and result["trust_ceiling"] == "LOW"
    assert result["availability_precision"] == "retrieval_time"
    assert all(result[name] is False for name in ("issuer_to_instrument_verified",
        "historical_identity_verified", "share_class_verified", "financial_scoring_authorized",
        "investment_scoring_authorized", "historical_replay_eligible", "validation_authorized",
        "execution_authorized"))
    digest = result["input_hash"]
    assert digest == sha256(financial_input_json(
        {key: value for key, value in result.items() if key != "input_hash"}).encode()).hexdigest()
    assert _claims(foundation)["input_hash"] == digest
    local = NOW.astimezone(ZoneInfo("Asia/Kuala_Lumpur"))
    assert _claims(foundation, at=local)["input_hash"] == digest
    assert _claims(foundation, at=NOW - timedelta(microseconds=1))["status"] == (
        "CATALOG_UNAVAILABLE")
    assert _read(foundation) == catalog  # Existing reader/version remains untouched.
    assert foundation[0].path.read_bytes() == before
    assert foundation[0].table_count("instruments") == 0


@pytest.mark.parametrize("tickers,symbol,expected", [
    (["OTHER"], "MSFT", "TICKER_NOT_DECLARED"),
    (["msft"], "MSFT", "TICKER_NOT_DECLARED"),
    (["BRK.B"], "BRK-B", "TICKER_NOT_DECLARED"),
    (["MSFT", "MSFT"], "MSFT", "AMBIGUOUS_TICKER_DECLARATIONS"),
    (["OTHER", "MSFT", "OTHER"], "MSFT", "AMBIGUOUS_TICKER_DECLARATIONS"),
    ([], "MSFT", "NO_DECLARED_TICKERS"),
    (None, "MSFT", "TICKER_DECLARATION_NULL"),
    ("MSFT", "MSFT", "INVALID_TICKER_DECLARATIONS"),
    ([True], "MSFT", "INVALID_TICKER_DECLARATIONS"),
    ([" MSFT"], "MSFT", "INVALID_TICKER_DECLARATIONS"),
    (["MS FT"], "MSFT", "INVALID_TICKER_DECLARATIONS"),
    (["MSFT", "BAD/UNSUPPORTED"], "MSFT", "INVALID_TICKER_DECLARATIONS"),
    (["ＭＳＦＴ"], "MSFT", "INVALID_TICKER_DECLARATIONS"),
    (["A" * 65], "MSFT", "INVALID_TICKER_DECLARATIONS"),
    (["MSFT"] * 257, "MSFT", "INVALID_TICKER_DECLARATIONS"),
])
def test_no_alias_normalization_dedup_or_favorable_ticker_selection(
    foundation, tickers, symbol, expected,
):
    payload = _payload()
    payload["tickers"] = tickers
    _ingest(foundation, sec.SECSubmissionsCapture(payload))
    result = _claims(foundation, symbol=symbol)
    assert result["status"] == expected and result["source_bound"]
    assert not result["issuer_to_instrument_verified"]
    assert not result["financial_scoring_authorized"]
    if expected == "AMBIGUOUS_TICKER_DECLARATIONS":
        assert result["declared_tickers"] == tickers
    if expected == "INVALID_TICKER_DECLARATIONS":
        assert result["declared_tickers"] is None and result["exact_ticker_match_indices"] == []


@pytest.mark.parametrize("exchanges,state", [
    (None, "NULL"), ([], "EMPTY"), (["Nasdaq", "Nasdaq"], "DUPLICATE"),
    (["NYSE", "Nasdaq"], "OBSERVED_UNQUALIFIED"), ([True], "INVALID_OR_UNSUPPORTED"),
])
def test_exchange_arrays_are_not_positional_listing_mapping(foundation, exchanges, state):
    payload = _payload()
    payload["tickers"] = ["MSFT", "OTHER", "THIRD"]
    payload["exchanges"] = exchanges
    _ingest(foundation, sec.SECSubmissionsCapture(payload))
    result = _claims(foundation)
    assert result["status"] == "TICKER_DECLARED_UNVERIFIED"
    assert result["exchange_field_status"] == state
    assert result["exchange_association_status"] == "NOT_INFERRED"
    assert not result["share_class_verified"]


def test_missing_name_and_tickers_stay_missing_without_inference_from_filing(foundation):
    payload = _payload()
    del payload["tickers"]
    del payload["name"]
    _ingest(foundation, sec.SECSubmissionsCapture(payload))
    result = _claims(foundation)
    assert result["status"] == "TICKER_DECLARATION_MISSING"
    assert result["issuer_name"] is None and result["declared_tickers"] is None
    assert result["warnings"] and result["exchange_field_status"] == "MISSING"


@pytest.mark.parametrize("latest", ["failure", "wrong_cik", "tie", "tampered", "unfinished"])
def test_issuer_claims_keep_latest_failure_and_future_completion_without_fallback(
    foundation, latest,
):
    _ingest(foundation)
    later = NOW + timedelta(seconds=1)
    payload = deepcopy(_payload())
    payload["tickers"] = ["OTHER"]
    if latest == "wrong_cik":
        payload["cik"] = 1
    capture = (sec.SECSubmissionsCapture(None, "http_403") if latest == "failure"
               else sec.SECSubmissionsCapture(payload))
    if latest == "tie":
        _ingest(foundation, at=later)
    _ingest(foundation, capture, at=later,
            completed=later + timedelta(seconds=1) if latest == "unfinished" else later)
    if latest == "tampered":
        digest = _read(foundation, later)["captures"][-1]["raw_data_hash"]
        (foundation[1].root / "sha256" / digest[:2] / f"{digest}.bin").write_bytes(b"{}")
    result = _claims(foundation, at=later)
    assert result["status"] == "CATALOG_UNAVAILABLE" and not result["source_bound"]
    assert result["declared_tickers"] is None and not result["exact_ticker_match_indices"]
    assert _claims(foundation)["status"] == "TICKER_DECLARED_UNVERIFIED"


def test_issuer_claims_reader_rechecks_bytes_after_metadata_read(foundation, monkeypatch):
    from tong_quant.data import sec_filing_inputs

    _ingest(foundation)
    original = sec_filing_inputs.read_sec_filing_inputs

    def tamper_after_metadata(*args, **kwargs):
        result = original(*args, **kwargs)
        digest = result["captures"][-1]["raw_data_hash"]
        (foundation[1].root / "sha256" / digest[:2] / f"{digest}.bin").write_bytes(b"{}")
        return result

    monkeypatch.setattr(sec_filing_inputs, "read_sec_filing_inputs", tamper_after_metadata)
    result = _claims(foundation)
    assert result["status"] == "REJECTED_OR_AMBIGUOUS" and not result["source_bound"]
    assert result["declared_tickers"] is None


def test_issuer_claims_and_catalog_share_snapshot_during_competing_write(foundation, monkeypatch):
    from tong_quant.data import sec_filing_inputs

    _ingest(foundation)
    original = sec_filing_inputs.read_sec_filing_inputs
    later = NOW + timedelta(seconds=1)
    written = []

    def write_after_metadata(*args, **kwargs):
        result = original(*args, **kwargs)
        if not written:
            payload = _payload()
            payload["tickers"] = ["OTHER"]
            _ingest((SQLiteStore(foundation[0].path), foundation[1]),
                    sec.SECSubmissionsCapture(payload), at=later)
            written.append(True)
        return result

    monkeypatch.setattr(sec_filing_inputs, "read_sec_filing_inputs", write_after_metadata)
    result = _claims(foundation, at=later)
    assert result["status"] == "TICKER_DECLARED_UNVERIFIED" and written == [True]
    assert _claims(foundation, at=later)["status"] == "TICKER_NOT_DECLARED"


@pytest.mark.parametrize("symbol", ["", "msft", "0700.HK", "MSFT/USD", "ＭＳＦＴ"])
def test_issuer_claim_request_rejects_unsupported_symbol_before_database_reads(foundation, symbol):
    with pytest.raises(ValueError):
        _claims(foundation, symbol=symbol)


def test_issuer_claim_request_rejects_naive_cutoff_before_database_reads(foundation):
    with pytest.raises(ValueError):
        _claims(foundation, at=NOW.replace(tzinfo=None))
