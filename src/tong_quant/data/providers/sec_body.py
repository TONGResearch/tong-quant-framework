"""Original primary-filing bytes inside a reconstructible evidence envelope."""

import base64
import json
import os
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from html import unescape
from pathlib import PurePosixPath

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
from tong_quant.data.providers.sec_submissions import (
    ACCESS_IDENTITY_ENV,
    PROVIDER,
    download_sec_bytes,
)
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market
from tong_quant.domain.models import require_timezone
from tong_quant.version import SEC_BODY_VERSION

DATASET = "sec_primary_filing_body_snapshot"
MAX_BODY_BYTES = 32 * 1024 * 1024
MAX_ENVELOPE_BYTES = 48 * 1024 * 1024
LIMITATIONS = (
    "Primary bytes bind a retained issuer catalog accession and filename, not equity identity",
    "Availability is actual retrieval; filed/report/acceptance labels are not exact publication",
    "Original body bytes are base64-retained in the JSON artifact with a separate body checksum",
    "Inline review is a bounded subset, not full XBRL/schema/accounting or audit validation",
    "Same-origin numeric agreement is not independent provider calibration or truth",
    "No canonical facts, financial score, replay/validation admission or trading authority",
)
PARAMETERS = {"parent_evidence_id", "parent_raw_data_hash", "parent_available_at",
              "primary_document", "form", "filed", "report_date"}


def body_subject(cik: str, accession: str) -> str:
    if (re.fullmatch(r"[0-9]{10}", cik) is None or int(cik) == 0
            or re.fullmatch(r"[0-9]{10}-[0-9]{2}-[0-9]{6}", accession) is None):
        raise ValueError("SEC body requires explicit CIK and accession")
    return f"{cik}:{accession}"


def validate_request(request: ProviderDatasetRequest) -> tuple[str, str]:
    request.__post_init__()
    parts = request.subject.split(":")
    if (request.dataset != DATASET or request.market is not Market.US or len(parts) != 2
            or body_subject(*parts) != request.subject or set(request.parameters) != PARAMETERS):
        raise ValueError("invalid SEC body request scope")
    values = request.parameters
    if not all(isinstance(value, str) for value in values.values()):
        raise ValueError("SEC body request parameters must be strings")
    reject_sensitive_structure(values)
    if values["form"] not in {"10-K", "10-K/A", "10-Q", "10-Q/A", "20-F", "20-F/A",
                               "40-F", "40-F/A"}:
        raise ValueError("SEC body review requires a periodic filing")
    for name in ("filed", "report_date"):
        if (re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", values[name]) is None
                or date.fromisoformat(values[name]) > request.as_of.astimezone(UTC).date()):
            raise ValueError("invalid or future SEC body date label")
    for name in ("parent_evidence_id", "parent_raw_data_hash"):
        if re.fullmatch(r"[0-9a-f]{64}", values[name]) is None:
            raise ValueError("SEC body requires pinned parent hashes")
    parent = datetime.fromisoformat(values["parent_available_at"])
    require_timezone(parent, "SEC body parent availability")
    if parent.astimezone(UTC) > request.as_of.astimezone(UTC):
        raise ValueError("future SEC body parent")
    path = PurePosixPath(values["primary_document"])
    if (path.as_posix() != values["primary_document"] or not 1 <= len(path.parts) <= 8
            or path.suffix not in {".htm", ".html"} or len(str(path)) > 512
            or any(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,254}", part) is None
                   or part in {".", ".."} for part in path.parts)):
        raise ValueError("unsupported SEC primary document path")
    return parts[0], parts[1]


def body_url(request: ProviderDatasetRequest) -> str:
    cik, accession = validate_request(request)
    return (f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/"
            + request.parameters["primary_document"])


@dataclass(frozen=True, slots=True)
class SECBodyCapture:
    content: bytes | None
    error_code: str = ""

    def __post_init__(self) -> None:
        if ((self.content is None) != bool(self.error_code) or self.error_code not in {
            "", "access_identity_missing", "access_identity_invalid", "http_403", "http_404",
            "http_429", "http_error", "network_unavailable", "invalid_decoded_response",
            "response_too_large", "empty_response"}
                or self.content is not None and (not isinstance(self.content, bytes)
                    or not 0 < len(self.content) <= MAX_BODY_BYTES)):
            raise ValueError("invalid bounded SEC body capture")
        if self.content is not None:
            try:
                text = unescape(self.content.decode("utf-8"))
            except UnicodeDecodeError:
                raise ValueError("SEC body capture currently requires UTF-8") from None
            if any(ord(char) < 32 and char not in "\t\n\r" for char in text):
                raise ValueError("SEC body contains unsupported control characters")
            reject_sensitive_structure(text, path="sec_body")
            contact = re.search(r"\S+@[^\s@]+\.[^\s@]+",
                                os.environ.get(ACCESS_IDENTITY_ENV, "").strip())
            if contact is not None and contact.group().casefold() in text.casefold():
                raise ValueError("SEC body reflects access contact")


def download_body(request: ProviderDatasetRequest) -> SECBodyCapture:
    content, error = download_sec_bytes(body_url(request), max_bytes=MAX_BODY_BYTES)
    try:
        return SECBodyCapture(content, error)
    except ValueError:
        return SECBodyCapture(None, "invalid_decoded_response")


@dataclass(slots=True)
class SECBodyAdapter:
    download: Callable[[ProviderDatasetRequest], SECBodyCapture] = download_body
    clock: Callable[[], datetime] = lambda: datetime.now(UTC)
    provider_id: str = PROVIDER

    def capabilities(self) -> tuple[ProviderDatasetCapability, ...]:
        return (ProviderDatasetCapability(PROVIDER, DATASET, (Market.US,),
            ProviderCapabilityStatus.DEGRADED, DataTrustLevel.LOW,
            AvailabilityPrecision.RETRIEVAL_TIME, False, tuple(sorted(PARAMETERS)),
            tuple(EvidenceLimitation(f"sec_body_{index}", text, DataTrustLevel.LOW)
                  for index, text in enumerate(LIMITATIONS)), SEC_BODY_VERSION),)

    def fetch(self, request: ProviderDatasetRequest) -> ProviderEvidenceBatch:
        validate_request(request)
        capture = self.download(request)
        capture.__post_init__()
        captured = self.clock()
        require_timezone(captured, "SEC body capture")
        if captured.utcoffset() != timedelta(0):
            raise ValueError("SEC body capture clock must use UTC")
        if captured.astimezone(UTC) < datetime.fromisoformat(
            request.parameters["parent_available_at"]).astimezone(UTC):
            raise ValueError("SEC body capture precedes parent")
        body_hash = sha256(capture.content).hexdigest() if capture.content else None
        content = json.dumps({"model_version": SEC_BODY_VERSION, "market": request.market.value,
            "subject": request.subject, "parameters": request.parameters,
            "retrieved_at": captured.astimezone(UTC).isoformat(), "error_code": capture.error_code,
            "body_base64": base64.b64encode(capture.content).decode() if capture.content else None},
            sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        if len(content) > MAX_ENVELOPE_BYTES:
            raise ValueError("SEC body envelope exceeds bounds")
        digest, reference = sha256(content).hexdigest(), body_url(request)
        artifact_id = provider_artifact_id(provider=PROVIDER, dataset=DATASET,
            market=request.market, subject=request.subject, source_identity=SEC_BODY_VERSION,
            source_reference=reference, content_hash=digest)
        artifact = ProviderArtifact(artifact_id, PROVIDER, DATASET, request.market, request.subject,
            SEC_BODY_VERSION, reference, captured, captured, digest, "application/json",
            AvailabilityPrecision.RETRIEVAL_TIME, DataTrustLevel.LOW, content, SEC_BODY_VERSION)
        payload: dict[str, object] = {"status": capture.error_code or "captured_body_unqualified",
            "body_sha256": body_hash, "body_byte_size": len(capture.content or b""),
            "parent_binding": request.parameters, "artifact_id": artifact_id,
            "financial_scoring_authorized": False, "historical_replay_eligible": False,
            "validation_authorized": False, "execution_authorized": False}
        record = ProviderEvidenceRecord(provider_evidence_id(provider=PROVIDER, dataset=DATASET,
            market=request.market, subject=request.subject, available_at=captured,
            source_reference=reference, payload=payload), PROVIDER, DATASET, request.market,
            request.subject, captured, captured, reference, payload, digest,
            AvailabilityPrecision.RETRIEVAL_TIME, DataTrustLevel.LOW, LIMITATIONS)
        return ProviderEvidenceBatch(PROVIDER, DATASET, request.market, captured, reference,
            {"subject": request.subject, **request.parameters,
             "normalization_version": SEC_BODY_VERSION},
            digest, 1, (record,), self.capabilities()[0].limitations, (artifact,))
