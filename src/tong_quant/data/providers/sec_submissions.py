"""Retain SEC issuer filing metadata, not financial facts or publication times."""

import json
import os
import re
import ssl
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from html import unescape
from pathlib import PurePosixPath
from time import sleep
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

import certifi

from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.providers.contracts import (
    EvidenceLimitation,
    ProviderArtifact,
    ProviderCapabilityStatus,
    ProviderDatasetCapability,
    ProviderDatasetRequest,
    ProviderEvidenceBatch,
    ProviderEvidenceRecord,
    provider_artifact_id,
    provider_evidence_id,
)
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market
from tong_quant.domain.models import require_timezone
from tong_quant.version import SEC_SUBMISSIONS_VERSION

PROVIDER = "sec_edgar"
DATASET = "sec_issuer_filings_snapshot"
MAX_BYTES = 2 * 1024 * 1024
ACCESS_IDENTITY_ENV = "TONG_QUANT_SEC_USER_AGENT"
_COLUMNS = ("accessionNumber", "filingDate", "reportDate", "acceptanceDateTime",
            "form", "primaryDocument")
LEGACY_VERSION = "sec-issuer-filings-snapshot-v1"
_VERSIONS = {LEGACY_VERSION, SEC_SUBMISSIONS_VERSION}
_PERIODIC_FORMS = {"10-K", "10-Q", "20-F", "40-F"}
_ERRORS = {"", "access_identity_missing", "access_identity_invalid", "http_403", "http_404",
           "http_429", "http_error", "network_unavailable", "invalid_decoded_response"}
LIMITATIONS = (
    "Issuer-level SEC submissions metadata; ticker, listing and equity identity are unverified",
    "Acceptance is not public dissemination; no exact historical published_at is inferred",
    "Availability is actual retrieval time, never the filing date or acceptance timestamp",
    "Recent filings are a bounded snapshot; older referenced pages are not captured or complete",
    "Amendment form labels do not establish restatements, revision order or numeric comparability",
    "No filing body, XBRL facts, canonical fundamentals, source promotion or scoring admission",
    "Decoded response envelope, not original HTTP bytes; independent calibration remains required",
)


def validate_request(request: ProviderDatasetRequest) -> None:
    request.__post_init__()
    if (request.dataset != DATASET or request.market is not Market.US or request.parameters
            or re.fullmatch(r"[0-9]{10}", request.subject) is None
            or int(request.subject) == 0):
        raise ValueError("SEC submissions require an explicit ten-digit CIK and no parameters")


def submissions_url(request: ProviderDatasetRequest) -> str:
    validate_request(request)
    return f"https://data.sec.gov/submissions/CIK{request.subject}.json"


def _unique_object(items: list[tuple[str, Any]]) -> dict[str, Any]:
    if len({key for key, _ in items}) != len(items):
        raise ValueError("duplicate SEC response keys")
    return dict(items)


@dataclass(frozen=True, slots=True)
class SECSubmissionsCapture:
    payload: dict[str, Any] | None
    error_code: str = ""

    def __post_init__(self) -> None:
        if (self.error_code not in _ERRORS or (self.payload is None) != bool(self.error_code)
                or self.payload is not None and not isinstance(self.payload, dict)):
            raise ValueError("invalid SEC capture state")
        reject_sensitive_structure(self.payload, path="sec_submissions_capture")
        if len(json.dumps(self.payload, sort_keys=True, separators=(",", ":"),
                          allow_nan=False).encode()) > MAX_BYTES:
            raise ValueError("SEC capture exceeds byte bound")


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: Any, msg: Any,
                         headers: Any, newurl: Any) -> None:
        # The operator's contact identity must not follow a redirect to another host.
        return None


def download_submissions(request: ProviderDatasetRequest) -> SECSubmissionsCapture:
    return download_sec_json(submissions_url(request))


def download_sec_json(url: str) -> SECSubmissionsCapture:
    """Shared bounded SEC transport; neither arbitrary URLs nor contact persistence."""
    raw, error = download_sec_bytes(url, max_bytes=MAX_BYTES)
    if raw is None:
        if error in {"response_too_large", "empty_response"}:
            error = "invalid_decoded_response"  # Preserve existing JSON capture semantics.
        return SECSubmissionsCapture(None, error)
    try:
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
        contact = re.search(r"\S+@[^\s@]+\.[^\s@]+",
                            os.environ.get(ACCESS_IDENTITY_ENV, "").strip())
        if contact is not None and contact.group() in json.dumps(payload, ensure_ascii=False):
            return SECSubmissionsCapture(None, "invalid_decoded_response")
        return SECSubmissionsCapture(payload)
    except (UnicodeDecodeError, ValueError):
        return SECSubmissionsCapture(None, "invalid_decoded_response")


def download_sec_bytes(url: str, *, max_bytes: int) -> tuple[bytes | None, str]:
    """Bounded original response bytes; no redirect or remote error body is retained."""
    if type(max_bytes) is not int or not 0 < max_bytes <= 32 * 1024 * 1024:
        raise ValueError("invalid SEC response byte bound")
    if re.fullmatch(
        r"https://(data\.sec\.gov/(submissions/CIK[0-9]{10}(-submissions-[0-9]{3,6})?\.json|"
        r"api/xbrl/companyconcept/CIK[0-9]{10}/(us-gaap|ifrs-full)/"
        r"[A-Za-z_][A-Za-z0-9_.-]{0,127}\.json)|"
        r"www\.sec\.gov/Archives/edgar/data/[1-9][0-9]{0,9}/[0-9]{18}/"
        r"(?:[A-Za-z0-9][A-Za-z0-9_.-]{0,254}/){0,7}"
        r"[A-Za-z0-9][A-Za-z0-9_.-]{0,250}\.html?)", url,
    ) is None:
        raise ValueError("unsupported SEC public endpoint")
    identity = os.environ.get(ACCESS_IDENTITY_ENV, "").strip()
    if not identity:
        return None, "access_identity_missing"
    if (not 5 <= len(identity) <= 256 or not identity.isascii()
            or any(ord(char) < 32 or ord(char) > 126 for char in identity)
            or re.search(r"\S+@[^\s@]+\.[^\s@]+", identity) is None):
        return None, "access_identity_invalid"
    try:
        reject_sensitive_structure(identity)
    except ValueError:
        return None, "access_identity_invalid"
    opener = build_opener(_NoRedirect(), HTTPSHandler(
        context=ssl.create_default_context(cafile=certifi.where())))
    error_code = "network_unavailable"
    for attempt in range(2):
        sleep(1 if attempt == 0 else 5)  # Bounded, sequential calls; no crawler or fan-out.
        try:
            with opener.open(Request(url, headers={"User-Agent": identity,
                "Accept": ("text/html,application/xhtml+xml" if url.startswith(
                    "https://www.sec.gov/") else "application/json"),
                "Accept-Encoding": "identity"}), timeout=10) as reply:
                raw = reply.read(max_bytes + 1)
            if len(raw) > max_bytes:
                return None, "response_too_large"
            if not raw:
                return None, "empty_response"
            contact = re.search(r"\S+@[^\s@]+\.[^\s@]+", identity)
            if contact is not None and contact.group().casefold() in unescape(
                raw.decode("utf-8", errors="ignore")).casefold():
                return None, "invalid_decoded_response"
            return raw, ""
        except HTTPError as error:
            error_code = f"http_{error.code}" if error.code in {403, 404, 429} else "http_error"
            if error.code < 500 and error.code != 429:
                break
        except (TimeoutError, URLError, OSError):
            error_code = "network_unavailable"
    return None, error_code


def _date(value: object, *, optional: bool = False) -> str | None:
    if value == "" and optional:
        return None
    if not isinstance(value, str) or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None:
        raise ValueError("invalid SEC date")
    return date.fromisoformat(value).isoformat()


def _row(values: dict[str, Any], index: int, captured: datetime,
         *, version: str) -> dict[str, Any]:
    output = {**values, "row_index": index, "status": "INVALID_METADATA",
        "acceptance_at": None, "published_at": None,
        "available_at": captured.astimezone(UTC).isoformat(), "amendment_label": False,
        "restatement_verified": False, "numeric_revision": None}
    try:
        document = PurePosixPath(str(values["primaryDocument"]))
        if (not all(isinstance(values[name], str) for name in _COLUMNS)
                or re.fullmatch(r"[0-9]{10}-[0-9]{2}-[0-9]{6}", values["accessionNumber"]) is None
                or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 /.-]{0,31}", values["form"]) is None
                or not 1 <= len(document.parts) <= 8 or len(str(document)) > 512
                or document.as_posix() != values["primaryDocument"]
                or any(part in {".", ".."} or re.fullmatch(
                    r"[A-Za-z0-9][A-Za-z0-9_.-]{0,254}", part) is None
                    for part in document.parts)):
            return output
        filing = _date(values["filingDate"])
        period = _date(values["reportDate"], optional=True)
        output["amendment_label"] = values["form"].endswith("/A")
        today = captured.astimezone(UTC).date().isoformat()
        periodic = values["form"].removesuffix("/A") in _PERIODIC_FORMS
        if version != LEGACY_VERSION:
            output.update(report_date_role=("PERIOD_END_LABEL_UNQUALIFIED" if periodic
                else "FORM_SPECIFIC_DATE_UNQUALIFIED"),
                future_report_date_label=bool(period and period > today),
                future_filing_date_label=bool(filing and filing > today))
        # A prospectively disclosed meeting date is not future availability.
        if (filing is None or filing > today and version == LEGACY_VERSION
                or period is not None and period > today
                and (periodic or version == LEGACY_VERSION)):
            output["status"] = "FUTURE_METADATA"
            return output
        acceptance = datetime.fromisoformat(values["acceptanceDateTime"])
        require_timezone(acceptance, "SEC acceptance timestamp")
        if acceptance.astimezone(UTC) > captured.astimezone(UTC):
            output["status"] = "FUTURE_METADATA"
            return output
        output.update(status="OBSERVED_METADATA_UNQUALIFIED",
                      acceptance_at=acceptance.astimezone(UTC).isoformat())
    except (ValueError, TypeError, ArithmeticError):
        pass
    return output


def normalize_submissions(capture: SECSubmissionsCapture, request: ProviderDatasetRequest,
                          captured: datetime, *, version: str = SEC_SUBMISSIONS_VERSION,
                          ) -> dict[str, Any]:
    validate_request(request)
    capture.__post_init__()
    require_timezone(captured, "SEC capture timestamp")
    if version not in _VERSIONS:
        raise ValueError("unsupported SEC normalization version")
    output: dict[str, Any] = {"status": capture.error_code or "invalid_response",
        "filings": [], "older_pages": [], "recent_row_count": 0,
        "issuer_to_instrument_verified": False, "historical_continuity_verified": False,
        "published_at_known": False, "financial_scoring_authorized": False,
        "historical_replay_eligible": False, "validation_authorized": False,
        "execution_authorized": False}
    if capture.payload is None:
        return output
    try:
        payload = capture.payload
        cik = payload["cik"]
        if (type(cik) not in (str, int) or re.fullmatch(r"[0-9]{1,10}", str(cik)) is None
                or str(cik).zfill(10) != request.subject):
            raise ValueError("wrong SEC issuer")
        recent = payload["filings"]["recent"]
        if not isinstance(recent, dict) or any(
            not isinstance(recent.get(name), list) for name in _COLUMNS
        ):
            raise ValueError("missing SEC columns")
        count = len(recent["accessionNumber"])
        if count > 10000 or any(len(recent[name]) != count for name in _COLUMNS):
            raise ValueError("unaligned or oversized SEC columns")
        rows = [_row({name: recent[name][index] for name in _COLUMNS}, index, captured,
                     version=version)
                for index in range(count)]
        identities = Counter(str(row["accessionNumber"]) for row in rows)
        for row in rows:
            if identities[str(row["accessionNumber"])] > 1:
                row.update(status="DUPLICATE_ACCESSION", acceptance_at=None)
        pages = payload["filings"]["files"]
        if not isinstance(pages, list) or len(pages) > 1000:
            raise ValueError("invalid SEC older-page references")
        references = []
        for page in pages:
            if (not isinstance(page, dict) or re.fullmatch(
                rf"CIK{request.subject}-submissions-[0-9]{{3,6}}\.json", str(page.get("name")))
                    is None or type(page.get("filingCount")) is not int or page["filingCount"] < 0):
                raise ValueError("invalid SEC older-page identity")
            start, end = _date(page["filingFrom"]), _date(page["filingTo"])
            if start is None or end is None or start > end:
                raise ValueError("invalid SEC older-page dates")
            references.append({**page, "capture_status": "NOT_CAPTURED"})
        observed = sum(row["status"] == "OBSERVED_METADATA_UNQUALIFIED" for row in rows)
        output.update(status=("observed_metadata_unqualified" if observed == count and count
            else "partial_metadata" if observed else "insufficient_metadata"),
            filings=rows, older_pages=references, recent_row_count=count,
            observed_metadata_count=observed, cik=request.subject)
    except (KeyError, ValueError, TypeError, ArithmeticError):
        pass
    return output


@dataclass(slots=True)
class SECSubmissionsAdapter:
    download: Callable[[ProviderDatasetRequest], SECSubmissionsCapture] = download_submissions
    clock: Callable[[], datetime] = lambda: datetime.now(UTC)
    provider_id: str = PROVIDER
    model_version: str = SEC_SUBMISSIONS_VERSION

    def __post_init__(self) -> None:
        if self.model_version not in _VERSIONS:
            raise ValueError("unsupported SEC normalization version")

    def capabilities(self) -> tuple[ProviderDatasetCapability, ...]:
        return (ProviderDatasetCapability(PROVIDER, DATASET, (Market.US,),
            ProviderCapabilityStatus.DEGRADED, DataTrustLevel.LOW,
            AvailabilityPrecision.RETRIEVAL_TIME, False, (),
            tuple(EvidenceLimitation(f"sec_submissions_{index}", text, DataTrustLevel.LOW)
                  for index, text in enumerate(LIMITATIONS)), self.model_version),)

    def fetch(self, request: ProviderDatasetRequest) -> ProviderEvidenceBatch:
        self.__post_init__()
        validate_request(request)
        capture = self.download(request)
        capture.__post_init__()
        captured = self.clock()
        require_timezone(captured, "SEC capture timestamp")
        if captured.utcoffset() != timedelta(0):
            raise ValueError("SEC submissions capture clock must use UTC")
        content = json.dumps({"model_version": self.model_version,
            "market": request.market.value, "subject": request.subject,
            "parameters": request.parameters, "retrieved_at": captured.astimezone(UTC).isoformat(),
            "decoded_payload": capture.payload, "error_code": capture.error_code},
            sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        digest = sha256(content).hexdigest()
        reference = submissions_url(request)
        artifact_id = provider_artifact_id(provider=PROVIDER, dataset=DATASET,
            market=request.market, subject=request.subject, source_identity=self.model_version,
            source_reference=reference, content_hash=digest)
        # Legacy artifact publication is capture time with RETRIEVAL_TIME, not issuer publication.
        artifact = ProviderArtifact(artifact_id, PROVIDER, DATASET, request.market, request.subject,
            self.model_version, reference, captured, captured, digest, "application/json",
            AvailabilityPrecision.RETRIEVAL_TIME, DataTrustLevel.LOW, content,
            self.model_version)
        payload = {**normalize_submissions(capture, request, captured, version=self.model_version),
                   "artifact_id": artifact_id}
        record = ProviderEvidenceRecord(provider_evidence_id(provider=PROVIDER, dataset=DATASET,
            market=request.market, subject=request.subject, available_at=captured,
            source_reference=reference, payload=payload), PROVIDER, DATASET, request.market,
            request.subject, captured, captured, reference, payload, digest,
            AvailabilityPrecision.RETRIEVAL_TIME, DataTrustLevel.LOW, LIMITATIONS)
        return ProviderEvidenceBatch(PROVIDER, DATASET, request.market, captured, reference,
            {"subject": request.subject, "normalization_version": self.model_version},
            digest, 1, (record,), self.capabilities()[0].limitations, (artifact,))
