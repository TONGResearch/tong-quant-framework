"""Source-native XBRL concept observations, without canonical accounting aliases."""

import json
import re
from collections import Counter
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
    MAX_BYTES,
    PROVIDER,
    SECSubmissionsCapture,
    download_sec_json,
)
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market
from tong_quant.domain.models import require_timezone
from tong_quant.version import SEC_CONCEPT_VERSION

DATASET = "sec_company_concept_snapshot"
LIMITATIONS = (
    "Source-native standard-taxonomy observations, not admitted company financial definitions",
    "Actual retrieval is availability; filed date and fiscal labels never establish published_at",
    "All accessions/periods/units are retained; no latest-restatement replacement is inferred",
    "Only exact integer source values have normalized amounts; noninteger rows remain visible",
    "SEC metadata reference matching is not independent source or filing-body corroboration",
    "No issuer/ticker admission, canonical facts, financial scoring, replay or trading authority",
    "Decoded response envelope, not original HTTP bytes; custom taxonomy/body coverage is absent",
)


def concept_subject(cik: str, taxonomy: str, tag: str) -> str:
    subject = f"{cik}:{taxonomy}:{tag}"
    if re.fullmatch(r"[0-9]{10}:(us-gaap|ifrs-full):[A-Za-z_][A-Za-z0-9_.-]{0,127}",
                    subject) is None or int(cik) == 0:
        raise ValueError("concept requires explicit CIK, standard taxonomy and native tag")
    return subject


def validate_request(request: ProviderDatasetRequest) -> tuple[str, str, str]:
    request.__post_init__()
    if request.dataset != DATASET or request.market is not Market.US or request.parameters:
        raise ValueError("unsupported SEC concept request")
    parts = request.subject.split(":")
    if len(parts) != 3 or concept_subject(*parts) != request.subject:
        raise ValueError("invalid SEC concept identity")
    return parts[0], parts[1], parts[2]


def concept_url(request: ProviderDatasetRequest) -> str:
    cik, taxonomy, tag = validate_request(request)
    return f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/{taxonomy}/{tag}.json"


def download_concept(request: ProviderDatasetRequest) -> SECSubmissionsCapture:
    return download_sec_json(concept_url(request))


def _day(value: object) -> date:
    if not isinstance(value, str) or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None:
        raise ValueError("invalid SEC concept date")
    return date.fromisoformat(value)


def _row(unit: str, index: int, native: object, captured: datetime) -> dict[str, Any]:
    output: dict[str, Any] = {"unit": unit, "row_index": index, "native": native,
        "value": None, "period_start": None, "period_end": None,
        "period_shape": "UNKNOWN", "status": "INVALID_NATIVE_ROW",
        "available_at": captured.astimezone(UTC).isoformat(), "published_at": None,
        "numeric_revision": None, "accounting_definition_qualified": False}
    output["row_id"] = sha256(json.dumps({"unit": unit, "native": native},
        sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    try:
        if not isinstance(native, dict):
            return output
        end = _day(native["end"])
        start = _day(native["start"]) if "start" in native else None
        _day(native["filed"])  # Official date label, not a public dissemination timestamp.
        output.update(period_end=end.isoformat(), period_start=start.isoformat() if start else None,
                      period_shape="duration_label" if start else "instant_label")
        if end > captured.astimezone(UTC).date() or start is not None and start > end:
            output["status"] = "INVALID_OR_FUTURE_PERIOD"
            return output
        if (not isinstance(native.get("accn"), str) or re.fullmatch(
            r"[0-9]{10}-[0-9]{2}-[0-9]{6}", native["accn"]) is None
                or not isinstance(native.get("form"), str) or re.fullmatch(
                    r"[A-Za-z0-9][A-Za-z0-9 /.-]{0,31}", native["form"]) is None):
            return output
        value = native.get("val")
        if type(value) is not int or abs(value) > 10**24:
            output["status"] = "UNSUPPORTED_NATIVE_AMOUNT"
            return output
        output.update(value=str(value), status="OBSERVED_NATIVE_UNQUALIFIED")
    except (ValueError, TypeError, KeyError, ArithmeticError):
        pass
    return output


def normalize_concept(capture: SECSubmissionsCapture, request: ProviderDatasetRequest,
                       captured: datetime) -> dict[str, Any]:
    cik, taxonomy, tag = validate_request(request)
    capture.__post_init__()
    require_timezone(captured, "SEC concept capture")
    output: dict[str, Any] = {"status": capture.error_code or "invalid_response", "cik": cik,
        "taxonomy": taxonomy, "tag": tag, "observations": [], "units": [],
        "financial_scoring_authorized": False, "historical_replay_eligible": False,
        "validation_authorized": False, "execution_authorized": False,
        "issuer_to_instrument_verified": False, "accounting_definition_qualified": False,
        "historical_continuity_verified": False}
    if capture.payload is None:
        return output
    try:
        payload = capture.payload
        returned_cik = payload["cik"]
        if (type(returned_cik) not in (str, int) or re.fullmatch(
            r"[0-9]{1,10}", str(returned_cik)) is None or str(returned_cik).zfill(10) != cik
                or payload["taxonomy"] != taxonomy or payload["tag"] != tag):
            raise ValueError("wrong SEC concept identity")
        units = payload["units"]
        if (not isinstance(units, dict) or not len(units) <= 32 or any(
            not isinstance(unit, str) or re.fullmatch(r"[A-Za-z][A-Za-z0-9_./-]{0,63}", unit)
            is None or not isinstance(rows, list) for unit, rows in units.items()
        ) or sum(len(rows) for rows in units.values()) > 10000):
            raise ValueError("invalid SEC concept units or row count")
        rows = [_row(unit, index, row, captured)
                for unit in sorted(units) for index, row in enumerate(units[unit])]
        # Do not choose between conflicting or duplicate contexts within one accession.
        def identity(row: dict[str, Any]) -> str:
            native = row["native"] if isinstance(row["native"], dict) else {}
            fields = [row["unit"], *(native.get(name) for name in ("accn", "start", "end"))]
            return json.dumps(fields, sort_keys=True, separators=(",", ":"), allow_nan=False)
        counts = Counter(identity(row) for row in rows)
        for row in rows:
            if counts[identity(row)] > 1:
                row.update(status="DUPLICATE_FACT_CONTEXT", value=None)
        usable = sum(row["status"] == "OBSERVED_NATIVE_UNQUALIFIED" for row in rows)
        output.update(status=("observed_native_unqualified" if usable == len(rows) and rows
            else "partial_native" if usable else "insufficient_native"),
            observations=rows, units=sorted(units), observed_native_count=usable)
    except (ValueError, KeyError, TypeError, ArithmeticError):
        pass
    return output


@dataclass(slots=True)
class SECConceptAdapter:
    download: Callable[[ProviderDatasetRequest], SECSubmissionsCapture] = download_concept
    clock: Callable[[], datetime] = lambda: datetime.now(UTC)
    provider_id: str = PROVIDER

    def capabilities(self) -> tuple[ProviderDatasetCapability, ...]:
        return (ProviderDatasetCapability(PROVIDER, DATASET, (Market.US,),
            ProviderCapabilityStatus.DEGRADED, DataTrustLevel.LOW,
            AvailabilityPrecision.RETRIEVAL_TIME, False, (),
            tuple(EvidenceLimitation(f"sec_concept_{index}", text, DataTrustLevel.LOW)
                  for index, text in enumerate(LIMITATIONS)), SEC_CONCEPT_VERSION),)

    def fetch(self, request: ProviderDatasetRequest) -> ProviderEvidenceBatch:
        validate_request(request)
        capture = self.download(request)
        capture.__post_init__()
        captured = self.clock()
        require_timezone(captured, "SEC concept capture")
        if captured.utcoffset() != timedelta(0):
            raise ValueError("SEC concept capture clock must use UTC")
        content = json.dumps({"model_version": SEC_CONCEPT_VERSION,
            "market": request.market.value, "subject": request.subject, "parameters": {},
            "retrieved_at": captured.astimezone(UTC).isoformat(),
            "decoded_payload": capture.payload, "error_code": capture.error_code},
            sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        if len(content) > MAX_BYTES + 4096:
            raise ValueError("SEC concept envelope exceeds bounds")
        digest, reference = sha256(content).hexdigest(), concept_url(request)
        artifact_id = provider_artifact_id(provider=PROVIDER, dataset=DATASET,
            market=request.market, subject=request.subject, source_identity=SEC_CONCEPT_VERSION,
            source_reference=reference, content_hash=digest)
        artifact = ProviderArtifact(artifact_id, PROVIDER, DATASET, request.market, request.subject,
            SEC_CONCEPT_VERSION, reference, captured, captured, digest, "application/json",
            AvailabilityPrecision.RETRIEVAL_TIME, DataTrustLevel.LOW, content, SEC_CONCEPT_VERSION)
        payload = {**normalize_concept(capture, request, captured), "artifact_id": artifact_id}
        record = ProviderEvidenceRecord(provider_evidence_id(provider=PROVIDER, dataset=DATASET,
            market=request.market, subject=request.subject, available_at=captured,
            source_reference=reference, payload=payload), PROVIDER, DATASET, request.market,
            request.subject, captured, captured, reference, payload, digest,
            AvailabilityPrecision.RETRIEVAL_TIME, DataTrustLevel.LOW, LIMITATIONS)
        return ProviderEvidenceBatch(PROVIDER, DATASET, request.market, captured, reference,
            {"subject": request.subject, "normalization_version": SEC_CONCEPT_VERSION}, digest, 1,
            (record,), self.capabilities()[0].limitations, (artifact,))
