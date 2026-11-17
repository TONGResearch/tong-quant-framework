"""Explicit older SEC page capture, pinned to a retained parent catalog descriptor."""

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from typing import Any

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
    DATASET as CATALOG_DATASET,
)
from tong_quant.data.providers.sec_submissions import (
    PROVIDER,
    SECSubmissionsCapture,
    download_sec_json,
    normalize_submissions,
)
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market
from tong_quant.domain.models import require_timezone
from tong_quant.version import (
    SEC_FILING_PAGE_LEGACY_VERSION,
    SEC_FILING_PAGE_VERSION,
    SEC_SUBMISSIONS_VERSION,
)

DATASET = "sec_issuer_filings_page_snapshot"
_PARAMETERS = {"parent_evidence_id", "parent_raw_data_hash", "parent_available_at",
               "filing_count", "filing_from", "filing_to"}
LIMITATIONS = (
    "Older page has no independent issuer identity; URL and pinned parent bind the request",
    "Descriptor count/date agreement is not complete history or independent source verification",
    "Acceptance/filed/report labels are not exact public availability; retrieval time is retained",
    "Missing/failed/tied/corrupt or changed-parent pages cannot silently fall back",
    "No filing body, numeric accounting verification, canonical facts, score or replay admission",
    "Decoded envelope, not original HTTP bytes; LOW trust and unverified continuity remain",
)


def page_subject(cik: str, page: str) -> str:
    if (re.fullmatch(r"[0-9]{10}", cik) is None or int(cik) == 0 or re.fullmatch(
        rf"CIK{cik}-submissions-[0-9]{{3,6}}\.json", page) is None):
        raise ValueError("SEC page requires explicit matching CIK and safe referenced filename")
    return f"{cik}:{page}"


def validate_request(request: ProviderDatasetRequest) -> tuple[str, str]:
    request.__post_init__()
    parts = request.subject.split(":")
    if (request.market is not Market.US or request.dataset != DATASET or len(parts) != 2
            or page_subject(*parts) != request.subject or set(request.parameters) != _PARAMETERS):
        raise ValueError("invalid SEC page request scope")
    values = request.parameters
    for name in ("parent_evidence_id", "parent_raw_data_hash"):
        if re.fullmatch(r"[0-9a-f]{64}", values[name]) is None:
            raise ValueError("SEC page requires pinned parent digests")
    parent = datetime.fromisoformat(values["parent_available_at"])
    require_timezone(parent, "SEC parent availability")
    if parent.astimezone(UTC) > request.as_of.astimezone(UTC):
        raise ValueError("SEC page parent is from the future")
    count = values["filing_count"]
    if re.fullmatch(r"0|[1-9][0-9]{0,4}", count) is None or int(count) > 10000:
        raise ValueError("SEC page declared count outside bounds")
    for name in ("filing_from", "filing_to"):
        if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", values[name]) is None:
            raise ValueError("SEC page requires exact descriptor dates")
        date.fromisoformat(values[name])
    if values["filing_from"] > values["filing_to"]:
        raise ValueError("SEC page descriptor dates reversed")
    return parts[0], parts[1]


def page_url(request: ProviderDatasetRequest) -> str:
    _, page = validate_request(request)
    return f"https://data.sec.gov/submissions/{page}"


def download_page(request: ProviderDatasetRequest) -> SECSubmissionsCapture:
    return download_sec_json(page_url(request))


def normalize_page(capture: SECSubmissionsCapture, request: ProviderDatasetRequest,
                    captured: datetime, *, version: str = SEC_FILING_PAGE_VERSION,
                    ) -> dict[str, Any]:
    cik, page = validate_request(request)
    capture.__post_init__()
    require_timezone(captured, "SEC page capture")
    if datetime.fromisoformat(request.parameters["parent_available_at"]).astimezone(UTC) > (
        captured.astimezone(UTC)
    ):
        raise ValueError("SEC page capture cannot precede its parent availability")
    if version not in {SEC_FILING_PAGE_VERSION, SEC_FILING_PAGE_LEGACY_VERSION}:
        raise ValueError("unsupported SEC page version")
    output: dict[str, Any] = {"page": page, "cik": cik, "parent_binding": request.parameters,
        "filings": [], "status": capture.error_code or "invalid_response",
        "descriptor_consistent": False, "financial_scoring_authorized": False,
        "historical_replay_eligible": False, "validation_authorized": False,
        "execution_authorized": False, "historical_continuity_verified": False,
        "issuer_to_instrument_verified": False}
    if capture.payload is None:
        return output
    # Reuse the unchanged form-aware normalizer, not another metadata domain model.
    normalized = normalize_submissions(SECSubmissionsCapture({"cik": cik, "filings": {
        "recent": capture.payload, "files": []}}),
        ProviderDatasetRequest(CATALOG_DATASET, Market.US, cik, request.as_of), captured,
        version=SEC_SUBMISSIONS_VERSION)
    rows = normalized["filings"]
    output.update(filings=rows, status=normalized["status"])
    dates = [row["filingDate"] for row in rows]
    try:
        dates_valid = all(isinstance(value, str) and date.fromisoformat(value).isoformat() == value
                          for value in dates)
    except ValueError:
        dates_valid = False
    within = bool(dates) and dates_valid and (
        request.parameters["filing_from"] <= min(dates)
        and max(dates) <= request.parameters["filing_to"])
    exact = within and min(dates) == request.parameters["filing_from"] and (
        max(dates) == request.parameters["filing_to"])
    count_matches = len(rows) == int(request.parameters["filing_count"])
    consistent = count_matches and (exact if version == SEC_FILING_PAGE_LEGACY_VERSION else within)
    if version != SEC_FILING_PAGE_LEGACY_VERSION:
        output.update(descriptor_count_consistent=count_matches,
            descriptor_range_relation=("WITHIN_DECLARED_INTERVAL" if within else
                                       "OUTSIDE_OR_UNKNOWN_INTERVAL"),
            observed_filing_from=min(dates) if dates_valid and dates else None,
            observed_filing_to=max(dates) if dates_valid and dates else None)
    output["descriptor_consistent"] = consistent
    if rows and not consistent:
        output["status"] = "descriptor_mismatch"
    return output


@dataclass(slots=True)
class SECFilingPageAdapter:
    download: Callable[[ProviderDatasetRequest], SECSubmissionsCapture] = download_page
    clock: Callable[[], datetime] = lambda: datetime.now(UTC)
    provider_id: str = PROVIDER
    model_version: str = SEC_FILING_PAGE_VERSION

    def __post_init__(self) -> None:
        if self.model_version not in {SEC_FILING_PAGE_VERSION, SEC_FILING_PAGE_LEGACY_VERSION}:
            raise ValueError("unsupported SEC page version")

    def capabilities(self) -> tuple[ProviderDatasetCapability, ...]:
        return (ProviderDatasetCapability(PROVIDER, DATASET, (Market.US,),
            ProviderCapabilityStatus.DEGRADED, DataTrustLevel.LOW,
            AvailabilityPrecision.RETRIEVAL_TIME, False, tuple(sorted(_PARAMETERS)),
            tuple(EvidenceLimitation(f"sec_page_{index}", text, DataTrustLevel.LOW)
                  for index, text in enumerate(LIMITATIONS)), self.model_version),)

    def fetch(self, request: ProviderDatasetRequest) -> ProviderEvidenceBatch:
        self.__post_init__()
        validate_request(request)
        capture = self.download(request)
        capture.__post_init__()
        captured = self.clock()
        require_timezone(captured, "SEC page capture")
        if captured.utcoffset() != timedelta(0):
            raise ValueError("SEC page capture clock must use UTC")
        content = json.dumps({"model_version": self.model_version,
            "metadata_version": SEC_SUBMISSIONS_VERSION, "market": request.market.value,
            "subject": request.subject, "parameters": request.parameters,
            "retrieved_at": captured.astimezone(UTC).isoformat(),
            "decoded_payload": capture.payload, "error_code": capture.error_code},
            sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        digest, reference = sha256(content).hexdigest(), page_url(request)
        artifact_id = provider_artifact_id(provider=PROVIDER, dataset=DATASET,
            market=request.market, subject=request.subject, source_identity=self.model_version,
            source_reference=reference, content_hash=digest)
        artifact = ProviderArtifact(artifact_id, PROVIDER, DATASET, request.market, request.subject,
            self.model_version, reference, captured, captured, digest, "application/json",
            AvailabilityPrecision.RETRIEVAL_TIME, DataTrustLevel.LOW, content,
            self.model_version)
        payload = {**normalize_page(capture, request, captured, version=self.model_version),
                   "artifact_id": artifact_id}
        record = ProviderEvidenceRecord(provider_evidence_id(provider=PROVIDER, dataset=DATASET,
            market=request.market, subject=request.subject, available_at=captured,
            source_reference=reference, payload=payload), PROVIDER, DATASET, request.market,
            request.subject, captured, captured, reference, payload, digest,
            AvailabilityPrecision.RETRIEVAL_TIME, DataTrustLevel.LOW, LIMITATIONS)
        return ProviderEvidenceBatch(PROVIDER, DATASET, request.market, captured, reference,
            {"subject": request.subject, **request.parameters,
             "normalization_version": self.model_version}, digest, 1, (record,),
            self.capabilities()[0].limitations, (artifact,))
