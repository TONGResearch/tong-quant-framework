"""Source-bound numeric corroboration, never canonical fact or trade approval."""

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, localcontext
from hashlib import sha256
from typing import cast

from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.calibration.engine import ProviderCalibrationEngine
from tong_quant.data.calibration.models import CalibrationRecord, ProviderCalibrationSnapshot
from tong_quant.data.providers.contracts import (
    CNINFO_DISCLOSURES_DATASET,
    FINANCIAL_SNAPSHOT_DATASET,
    ProviderArtifact,
    ProviderEvidenceRecord,
    provider_artifact_id,
    provider_evidence_id,
)
from tong_quant.domain.enums import DataTrustLevel, Market
from tong_quant.domain.models import require_timezone
from tong_quant.version import FINANCIAL_CORROBORATION_VERSION


def _decimal(value: object) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise ValueError("financial numeric review requires explicit decimal values")
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        raise ValueError("invalid financial decimal") from None
    if (
        not number.is_finite() or len(number.as_tuple().digits) > 128
        or abs(int(number.as_tuple().exponent)) > 1000
    ):
        raise ValueError("financial decimal is nonfinite or exceeds review bounds")
    return number


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    if value == 0:
        return "0"
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


@dataclass(frozen=True, slots=True)
class FilingRowReview:
    subject: str
    canonical_metric: str
    statement: str
    native_metric: str
    native_evidence_id: str
    period_end: date
    period_start: date | None
    value_kind: str
    reporting_scope: str
    currency: str
    filing_value: Decimal
    filing_scale: Decimal
    native_scale_hypothesis: Decimal
    filing_sha256: str
    source_pages: tuple[int, ...]
    value_column: str
    sector_profile: str
    reviewed_at: datetime

    def __post_init__(self) -> None:
        require_timezone(self.reviewed_at, "financial reviewed_at")
        if (
            self.statement not in {"income", "balance", "cash_flow"}
            or self.value_kind not in {"flow", "stock"}
            or self.reporting_scope not in {"group", "company"}
            or self.currency != "CNY" or not self.subject or not self.canonical_metric
            or not self.native_metric or not self.value_column
            or self.sector_profile not in {"bank", "nonfinancial", "unknown"}
            or not self.source_pages or len(set(self.source_pages)) != len(self.source_pages)
            or any(type(page) is not int or not 1 <= page <= 1000 for page in self.source_pages)
        ):
            raise ValueError("financial review requires explicit supported row semantics")
        for digest in (self.native_evidence_id, self.filing_sha256):
            if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
                raise ValueError("financial review requires SHA-256 references")
        if self.value_kind == "flow" and (
            self.period_start is None or self.period_start > self.period_end
        ):
            raise ValueError("flow review requires an explicit period start")
        if self.value_kind == "stock" and self.period_start is not None:
            raise ValueError("stock review must not declare a flow period")
        if _decimal(self.filing_scale) <= 0 or _decimal(self.native_scale_hypothesis) <= 0:
            raise ValueError("review scales must be positive")
        _decimal(self.filing_value)


def corroborate_financial_row(
    review: FilingRowReview,
    native: ProviderEvidenceRecord,
    native_snapshot_bytes: bytes,
    filing: ProviderArtifact,
    *,
    as_of: datetime,
) -> dict[str, object]:
    require_timezone(as_of, "financial review as_of")
    available_at = max(review.reviewed_at, native.available_at, native.retrieved_at,
                       native.published_at or native.available_at,
                       filing.published_at, filing.retrieved_at)
    if available_at > as_of or review.period_end > as_of.date():
        raise ValueError("financial corroboration contains future inputs")
    if (
        native.provider != "akshare" or native.dataset != FINANCIAL_SNAPSHOT_DATASET
        or filing.provider != "cninfo_direct" or filing.dataset != CNINFO_DISCLOSURES_DATASET
        or native.subject != review.subject or filing.subject != review.subject
        or native.market is not Market.CHINA_A
        or native.market is not filing.market or native.evidence_id != review.native_evidence_id
        or filing.content_hash != review.filing_sha256
        or sha256(filing.content).hexdigest() != review.filing_sha256
        or not filing.content.startswith(b"%PDF")
        or filing.media_type != "application/pdf"
        or native.source_reference != f"akshare:financial:{review.statement}"
        or len(native_snapshot_bytes) > 16 * 1024 * 1024
        or sha256(native_snapshot_bytes).hexdigest() != native.raw_data_hash
    ):
        raise ValueError("financial corroboration source binding mismatch")
    recomputed = provider_evidence_id(
        provider=native.provider, dataset=native.dataset, market=native.market,
        subject=native.subject, available_at=native.available_at,
        source_reference=native.source_reference, payload=native.payload,
    )
    if recomputed != native.evidence_id:
        raise ValueError("financial native evidence identity mismatch")
    if filing.artifact_id != provider_artifact_id(
        provider=filing.provider, dataset=filing.dataset, market=filing.market,
        subject=filing.subject, source_identity=filing.source_identity,
        source_reference=filing.source_reference, content_hash=filing.content_hash,
    ):
        raise ValueError("financial filing artifact identity mismatch")
    reject_sensitive_structure(native.payload, path="financial_native")
    snapshot = json.loads(native_snapshot_bytes)
    frame = json.loads(snapshot["frame"])
    position = native.payload.get("row_number")
    row = native.payload.get("native_row")
    if (
        snapshot["parameters"] != {"symbol": review.subject, "statement": review.statement}
        or type(position) is not int or not 0 <= position < len(frame["data"])
        or not isinstance(row, dict)
        or json.dumps(frame["data"][position], sort_keys=True) != json.dumps(row, sort_keys=True)
        or native.payload.get("statement") != review.statement
        or row.get("metric_name") != review.native_metric
        or row.get("report_date") != review.period_end.isoformat()
    ):
        raise ValueError("financial native row or period mismatch")
    raw_value = row.get("value")
    missing = raw_value is None or (isinstance(raw_value, str) and not raw_value.strip())
    with localcontext() as context:
        context.prec = 300
        issuer_value = _decimal(review.filing_value) * _decimal(review.filing_scale)
        native_value = None if missing else _decimal(raw_value) * _decimal(
            review.native_scale_hypothesis
        )
    # Decimal strings avoid float rounding and the generic calibration float formatter.
    left = ProviderCalibrationSnapshot(
        "cninfo_direct", "financial_numeric_corroboration", as_of,
        (CalibrationRecord(review.canonical_metric, {"value": _decimal_text(issuer_value)}),),
    )
    right = ProviderCalibrationSnapshot(
        "akshare", "financial_numeric_corroboration", as_of,
        (CalibrationRecord(review.canonical_metric, {"value": _decimal_text(native_value)}),),
    )
    levels = (DataTrustLevel.UNKNOWN, DataTrustLevel.LOW, DataTrustLevel.MEDIUM,
              DataTrustLevel.HIGH, DataTrustLevel.VERIFIED)
    ceiling = min((native.trust_level, filing.trust_level, DataTrustLevel.LOW), key=levels.index)
    comparison = ProviderCalibrationEngine().compare(
        left, right, fields=("value",), compared_at=as_of, trust_ceiling=ceiling,
    )
    numeric_match = None if missing else native_value == issuer_value
    status = "MISSING_NATIVE_VALUE" if missing else (
        "NUMERIC_MATCH_REVIEW_REQUIRED" if numeric_match else "VALUE_CONFLICT"
    )
    report: dict[str, object] = {
        "model_version": FINANCIAL_CORROBORATION_VERSION,
        "as_of": as_of.isoformat(), "available_at": available_at.isoformat(),
        "review": asdict(review), "status": status, "numeric_match": numeric_match,
        "issuer_value_cny": _decimal_text(issuer_value),
        "native_value_under_hypothesis": _decimal_text(native_value),
        "native_snapshot_sha256": native.raw_data_hash,
        "filing_artifact_id": filing.artifact_id,
        "filing_retrieved_at": filing.retrieved_at.isoformat(),
        "native_retrieved_at": native.retrieved_at.isoformat(),
        "native_limitations": native.limitations,
        "native_trust_level": native.trust_level.value,
        "filing_trust_level": filing.trust_level.value,
        "native_availability_precision": native.availability_precision.value,
        "filing_availability_precision": filing.availability_precision.value,
        "trust_level": ceiling.value, "availability_precision": "retrieval_time",
        "numeric_comparison": asdict(comparison),
        "canonical_population_authorized": False, "historical_replay_eligible": False,
        "investment_scoring_authorized": False, "validation_authorized": False,
        "independent_provider_validation": False,
        "limitations": [
            "PDF values/pages/column semantics are manual review annotations, "
            "not machine-authenticated extraction.",
            "Native unit/currency/scope is an explicit hypothesis; "
            "numeric agreement cannot approve it globally.",
            "Flow period start and group/company scope are not independently "
            "proved by native field labels.",
            "This spot check does not prove historical revisions, disclosure timing "
            "or provider independence.",
            "A numeric agreement score is not Research/Investment confidence or PIT readiness.",
        ],
    }
    # Return only plain JSON scalars and reject credential-like annotations before export.
    document = cast(dict[str, object], json.loads(json.dumps(report, default=str, sort_keys=True)))
    reject_sensitive_structure(document, path="financial_corroboration")
    document["report_hash"] = sha256(json.dumps(
        document, sort_keys=True, separators=(",", ":")
    ).encode()).hexdigest()
    return document
