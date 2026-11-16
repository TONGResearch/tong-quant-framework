"""Explicit HK/MY original PDF evidence, never automatic financial extraction."""

import base64
import json
import re
import ssl
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from hashlib import sha256
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
from tong_quant.data.providers.yahoo_identity import validate_yahoo_equity_subject
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market
from tong_quant.domain.models import require_timezone
from tong_quant.version import GLOBAL_DOCUMENT_VERSION

DATASET = "global_primary_document_snapshot"
MAX_BYTES, MAX_ENVELOPE_BYTES = 32 * 1024 * 1024, 48 * 1024 * 1024
PARAMETERS = {"document_url", "landing_url", "issuer_label", "period_end", "document_kind"}
PROVIDERS = {Market.HONG_KONG: "hkex_document", Market.MALAYSIA: "maybank_document"}
LIMITATIONS = (
    "Explicit original PDF capture only; no text, table or numeric extraction is authorized",
    "Issuer, instrument, report kind and period are caller annotations, not verified identity",
    "Landing URL is a research reference; its bytes/link relationship are not retained or verified",
    "Availability is actual capture; URL/report dates are not first-publication timestamps",
    "Official-domain transport and PDF magic do not prove authenticity, truth or complete history",
    "No independent calibration, canonical facts, financial scoring, replay or execution authority",
)
_ERRORS = {"", "http_403", "http_404", "http_429", "http_error", "network_unavailable",
           "response_too_large", "empty_response", "invalid_pdf_payload"}


def validate_document_url(market: Market, url: str) -> None:
    patterns = {
        Market.HONG_KONG: r"https://www1\.hkexnews\.hk/listedco/listconews/sehk/"
                         r"[0-9]{4}/[0-9]{4}/[0-9]{10,20}(?:_c)?\.pdf",
        Market.MALAYSIA: r"https://www\.maybank\.com/iwov-resources/documents/pdf/"
                        r"annual-report/[0-9]{4}/[A-Za-z0-9][A-Za-z0-9_-]{0,180}\.pdf",
    }
    if market not in patterns or re.fullmatch(patterns[market], url) is None:
        raise ValueError("document URL is outside explicit HKEX/Maybank scope")


def validate_request(request: ProviderDatasetRequest) -> str:
    request.__post_init__()
    validate_yahoo_equity_subject(request.market, request.subject)
    if (request.market not in PROVIDERS or request.dataset != DATASET
            or set(request.parameters) != PARAMETERS
            or any(not isinstance(value, str) for value in request.parameters.values())):
        raise ValueError("invalid primary-document request scope")
    values = request.parameters
    reject_sensitive_structure(values)
    validate_document_url(request.market, values["document_url"])
    landing_patterns = {
        Market.HONG_KONG: r"https://www1\.hkexnews\.hk/listedco/listconews/sehk/"
                         r"[0-9]{4}/[0-9]{4}/[0-9]{10,20}(?:_c)?\.pdf",
        Market.MALAYSIA: r"https://www\.maybank\.com/en/investor-relations/"
                        r"financial-overview/annual-reports\.page",
    }
    # A direct HKEX document may serve as its own reference, not a captured catalog.
    if (re.fullmatch(landing_patterns[request.market], values["landing_url"]) is None
            or request.market is Market.HONG_KONG
            and values["landing_url"] != values["document_url"]
            or not 1 <= len(values["issuer_label"].strip()) <= 200
            or any(ord(char) < 32 for char in values["issuer_label"])
            or values["document_kind"] not in {"annual_report", "annual_financial_statements"}
            or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", values["period_end"]) is None
            or date.fromisoformat(values["period_end"]) > request.as_of.astimezone(UTC).date()):
        raise ValueError("invalid primary-document annotations")
    return PROVIDERS[request.market]


@dataclass(frozen=True, slots=True)
class DocumentCapture:
    content: bytes | None
    error_code: str = ""

    def __post_init__(self) -> None:
        if ((self.content is None) != bool(self.error_code) or self.error_code not in _ERRORS
                or self.content is not None and (not isinstance(self.content, bytes)
                    or not 0 < len(self.content) <= MAX_BYTES
                    or not self.content.startswith(b"%PDF-"))):
            raise ValueError("invalid bounded primary PDF capture")
        if self.content is not None:
            reject_sensitive_structure(self.content.decode("latin-1"), path="document_bytes")


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: Any, msg: Any,
                         headers: Any, newurl: Any) -> None:
        return None


def download_document(request: ProviderDatasetRequest) -> DocumentCapture:
    validate_request(request)
    opener = build_opener(_NoRedirect(), HTTPSHandler(
        context=ssl.create_default_context(cafile=certifi.where())))
    error_code = "network_unavailable"
    for attempt in range(2):
        sleep(1 if attempt == 0 else 3)
        try:
            with opener.open(Request(request.parameters["document_url"], headers={
                "User-Agent": "TongQuant/0.8 research-document", "Accept": "application/pdf",
                "Accept-Encoding": "identity"}), timeout=15) as reply:
                raw = reply.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                return DocumentCapture(None, "response_too_large")
            if not raw:
                return DocumentCapture(None, "empty_response")
            try:
                return DocumentCapture(raw)
            except ValueError:
                return DocumentCapture(None, "invalid_pdf_payload")
        except HTTPError as error:
            error_code = f"http_{error.code}" if error.code in {403, 404, 429} else "http_error"
            if error.code < 500 and error.code != 429:
                break
        except (TimeoutError, URLError, OSError):
            error_code = "network_unavailable"
    return DocumentCapture(None, error_code)


@dataclass(slots=True)
class GlobalDocumentAdapter:
    market: Market
    download: Callable[[ProviderDatasetRequest], DocumentCapture] = download_document
    clock: Callable[[], datetime] = lambda: datetime.now(UTC)

    @property
    def provider_id(self) -> str:
        if self.market not in PROVIDERS:
            raise ValueError("unsupported primary-document provider market")
        return PROVIDERS[self.market]

    def capabilities(self) -> tuple[ProviderDatasetCapability, ...]:
        return (ProviderDatasetCapability(self.provider_id, DATASET, (self.market,),
            ProviderCapabilityStatus.DEGRADED, DataTrustLevel.LOW,
            AvailabilityPrecision.RETRIEVAL_TIME, False, tuple(sorted(PARAMETERS)),
            tuple(EvidenceLimitation(f"global_document_{index}", text, DataTrustLevel.LOW)
                  for index, text in enumerate(LIMITATIONS)), GLOBAL_DOCUMENT_VERSION),)

    def fetch(self, request: ProviderDatasetRequest) -> ProviderEvidenceBatch:
        provider = validate_request(request)
        if provider != self.provider_id or request.market is not self.market:
            raise ValueError("document provider/request market mismatch")
        capture = self.download(request)
        capture.__post_init__()
        captured = self.clock()
        require_timezone(captured, "primary document capture")
        if date.fromisoformat(request.parameters["period_end"]) > captured.astimezone(UTC).date():
            raise ValueError("future primary document period annotation")
        content = json.dumps({"model_version": GLOBAL_DOCUMENT_VERSION,
            "market": request.market.value, "subject": request.subject,
            "parameters": request.parameters, "retrieved_at": captured.astimezone(UTC).isoformat(),
            "error_code": capture.error_code,
            "document_base64": (base64.b64encode(capture.content).decode()
                                if capture.content else None)},
            sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        if len(content) > MAX_ENVELOPE_BYTES:
            raise ValueError("primary document envelope exceeds bounds")
        digest, url = sha256(content).hexdigest(), request.parameters["document_url"]
        artifact_id = provider_artifact_id(provider=provider, dataset=DATASET,
            market=request.market, subject=request.subject, source_identity=GLOBAL_DOCUMENT_VERSION,
            source_reference=url, content_hash=digest)
        artifact = ProviderArtifact(artifact_id, provider, DATASET, request.market, request.subject,
            GLOBAL_DOCUMENT_VERSION, url, captured, captured, digest, "application/json",
            AvailabilityPrecision.RETRIEVAL_TIME, DataTrustLevel.LOW, content,
            GLOBAL_DOCUMENT_VERSION)
        payload: dict[str, object] = {"status": capture.error_code or "captured_pdf_unqualified",
            "annotations": request.parameters, "artifact_id": artifact_id,
            "document_sha256": sha256(capture.content).hexdigest() if capture.content else None,
            "document_byte_size": len(capture.content or b""), "published_at_known": False,
            "issuer_to_instrument_verified": False, "landing_link_verified": False,
            "numeric_extraction_authorized": False, "financial_scoring_authorized": False,
            "historical_replay_eligible": False, "validation_authorized": False,
            "execution_authorized": False}
        record = ProviderEvidenceRecord(provider_evidence_id(provider=provider, dataset=DATASET,
            market=request.market, subject=request.subject, available_at=captured,
            source_reference=url, payload=payload), provider, DATASET, request.market,
            request.subject, captured, captured, url, payload, digest,
            AvailabilityPrecision.RETRIEVAL_TIME, DataTrustLevel.LOW, LIMITATIONS)
        return ProviderEvidenceBatch(provider, DATASET, request.market, captured, url,
            {"subject": request.subject, **request.parameters,
             "normalization_version": GLOBAL_DOCUMENT_VERSION}, digest, 1, (record,),
            self.capabilities()[0].limitations, (artifact,))
