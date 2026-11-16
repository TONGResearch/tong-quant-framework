"""Explicit monetary transcription, not canonical accounting or source approval."""

from dataclasses import asdict, dataclass, fields
from datetime import UTC, date, datetime
from decimal import Decimal, localcontext
from hashlib import sha256
from typing import Any

from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.financial_inputs import financial_input_json
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
from tong_quant.data.providers.global_documents import validate_document_url
from tong_quant.data.providers.yahoo_identity import validate_yahoo_equity_subject
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market
from tong_quant.domain.models import require_timezone
from tong_quant.version import GLOBAL_DOCUMENT_REVIEW_VERSION

PROVIDER, DATASET = "global_document_manual_review", "global_document_monetary_review"
MAX_REVIEW_BYTES = 128 * 1024
UNITS = {"unit": Decimal(1), "thousand": Decimal(1000), "million": Decimal(1000000)}
LIMITATIONS = (
    "Single manual transcription; page, column, period, label, unit and scope are annotations",
    "Arithmetic scale conversion is not machine verification of the PDF or accounting meaning",
    "Current/comparative values are as presented in this filing, not original historical vintages",
    "Source capture and review availability are required; no publication time is inferred",
    "No canonical aliases, ratios, growth, FX, sector scoring, independent review or trading",
)


def _text(value: object, maximum: int = 200) -> bool:
    return (isinstance(value, str) and 1 <= len(value.strip()) <= maximum
            and all(ord(char) >= 32 for char in value))


def _digest(value: object) -> bool:
    return (isinstance(value, str) and len(value) == 64
            and all(char in "0123456789abcdef" for char in value))


@dataclass(frozen=True, slots=True)
class GlobalMonetaryRow:
    row_key: str
    native_label: str
    statement: str
    reporting_scope: str
    period_start: date | None
    period_end: date
    column_kind: str
    column_label: str
    currency: str
    source_unit: str
    source_unit_label: str
    source_value: Decimal | None
    value_status: str
    raw_cell_text: str
    pdf_page: int
    printed_page: str
    restatement_label: str

    def __post_init__(self) -> None:
        if (not _text(self.row_key, 64) or not _text(self.native_label)
                or not _text(self.column_label) or not _text(self.source_unit_label, 80)
                or not _text(self.printed_page, 32)
                or self.statement not in {"income", "balance", "cash_flow"}
                or self.reporting_scope not in {"group", "bank", "parent"}
                or self.column_kind not in {"current", "comparative"}
                or self.currency not in {"CNY", "HKD", "MYR", "USD"}
                or self.source_unit not in UNITS or type(self.pdf_page) is not int
                or not 1 <= self.pdf_page <= 1000
                or self.restatement_label not in {"unknown", "marked_restated", "not_marked"}
                or type(self.period_end) is not date
                or self.period_start is not None and type(self.period_start) is not date
                or self.statement == "balance" and self.period_start is not None
                or self.statement != "balance" and self.period_start is None
                or self.period_start is not None and self.period_start > self.period_end
                or not _text(self.raw_cell_text, 128)
                or self.value_status not in {"transcribed", "missing", "unreadable", "conflicting"}
                or (self.source_value is not None) != (self.value_status == "transcribed")):
            raise ValueError("unsupported overseas monetary review row")
        if self.source_value is not None:
            if (not isinstance(self.source_value, Decimal) or not self.source_value.is_finite()
                    or len(self.source_value.as_tuple().digits) > 64
                    or abs(int(self.source_value.as_tuple().exponent)) > 24):
                raise ValueError("unsupported reviewed decimal")
            with localcontext() as context:
                context.prec = 100
                if abs(self.source_value * UNITS[self.source_unit]) > Decimal("1e24"):
                    raise ValueError("reviewed monetary amount exceeds bounds")
        reject_sensitive_structure(asdict(self), path="global_monetary_row")

    def document(self) -> dict[str, Any]:
        output = asdict(self)
        output["source_value"] = str(self.source_value) if self.source_value is not None else None
        output["period_start"] = self.period_start.isoformat() if self.period_start else None
        output["period_end"] = self.period_end.isoformat()
        return output

    def observation(self) -> dict[str, Any]:
        with localcontext() as context:
            context.prec = 100
            amount = (self.source_value * UNITS[self.source_unit]
                      if self.source_value is not None else None)
        return {**self.document(), "unqualified_scaled_amount": format(amount, "f") if (
                    amount is not None) else None,
                "canonical_metric": None, "accounting_definition_qualified": False}


@dataclass(frozen=True, slots=True)
class GlobalDocumentReview:
    market: Market
    subject: str
    document_url: str
    source_evidence_id: str
    source_envelope_sha256: str
    source_document_sha256: str
    source_available_at: datetime
    reviewed_at: datetime
    reviewer: str
    report_period_end: date
    rows: tuple[GlobalMonetaryRow, ...]

    def __post_init__(self) -> None:
        validate_yahoo_equity_subject(self.market, self.subject)
        validate_document_url(self.market, self.document_url)
        require_timezone(self.source_available_at, "review source availability")
        require_timezone(self.reviewed_at, "manual reviewed_at")
        if (not all(_digest(value) for value in (self.source_evidence_id,
            self.source_envelope_sha256, self.source_document_sha256))
                or not _text(self.reviewer) or type(self.report_period_end) is not date
                or self.report_period_end > self.reviewed_at.astimezone(UTC).date()
                or self.source_available_at.astimezone(UTC) > self.reviewed_at.astimezone(UTC)
                or type(self.rows) is not tuple or not 1 <= len(self.rows) <= 64
                or any(not isinstance(row, GlobalMonetaryRow) for row in self.rows)):
            raise ValueError("unsupported overseas document review scope")
        for row in self.rows:
            row.__post_init__()
            if (row.period_end > self.report_period_end or (row.column_kind == "current"
                and row.period_end != self.report_period_end) or (row.column_kind == "comparative"
                and row.period_end >= self.report_period_end)):
                raise ValueError("review column/period conflicts with filing annotation")
        keys = [(row.statement, row.native_label, row.reporting_scope, row.period_start,
                 row.period_end, row.currency, row.source_unit) for row in self.rows]
        if len({row.row_key for row in self.rows}) != len(self.rows) or len(set(keys)) != len(keys):
            raise ValueError("duplicate overseas review row identity/context")
        reject_sensitive_structure(self.document(), path="global_document_review")
        if len(financial_input_json(self.document()).encode()) > MAX_REVIEW_BYTES:
            raise ValueError("overseas review exceeds size bound")

    def document(self) -> dict[str, Any]:
        return {"market": self.market.value, "subject": self.subject,
            "document_url": self.document_url, "source_evidence_id": self.source_evidence_id,
            "source_envelope_sha256": self.source_envelope_sha256,
            "source_document_sha256": self.source_document_sha256,
            "source_available_at": self.source_available_at.astimezone(UTC).isoformat(),
            "reviewed_at": self.reviewed_at.astimezone(UTC).isoformat(), "reviewer": self.reviewer,
            "report_period_end": self.report_period_end.isoformat(),
            "rows": [row.document() for row in self.rows]}


def parse_global_document_review(document: dict[str, Any]) -> GlobalDocumentReview:
    if set(document) != {"review", "rows"} or not isinstance(document["review"], dict):
        raise ValueError("overseas review plan schema mismatch")
    reject_sensitive_structure(document)
    review = dict(document["review"])
    if set(review) != {field.name for field in fields(GlobalDocumentReview)} - {"rows"}:
        raise ValueError("overseas review metadata schema mismatch")
    review["market"] = Market(review["market"])
    for name in ("reviewed_at", "source_available_at"):
        review[name] = datetime.fromisoformat(review[name])
    review["report_period_end"] = date.fromisoformat(review["report_period_end"])
    if not isinstance(document["rows"], list) or not 1 <= len(document["rows"]) <= 64:
        raise ValueError("overseas review requires bounded rows")
    rows = []
    for raw in document["rows"]:
        if (not isinstance(raw, dict)
                or set(raw) != {field.name for field in fields(GlobalMonetaryRow)}):
            raise ValueError("overseas monetary row schema mismatch")
        values = dict(raw)
        raw_value = values["source_value"]
        if raw_value is not None and type(raw_value) is not str:
            raise ValueError("source monetary values must be quoted decimals")
        values["source_value"] = (Decimal(raw_value)
                                  if isinstance(raw_value, str) and raw_value else None)
        values["period_start"] = date.fromisoformat(values["period_start"]) if (
            values["period_start"] not in {None, ""}) else None
        values["period_end"] = date.fromisoformat(values["period_end"])
        rows.append(GlobalMonetaryRow(**values))
    return GlobalDocumentReview(**review, rows=tuple(rows))


@dataclass(frozen=True, slots=True)
class GlobalDocumentReviewAdapter:
    review: GlobalDocumentReview
    recorded_at: datetime
    provider_id: str = PROVIDER

    def capabilities(self) -> tuple[ProviderDatasetCapability, ...]:
        return (ProviderDatasetCapability(PROVIDER, DATASET, (Market.HONG_KONG, Market.MALAYSIA),
            ProviderCapabilityStatus.DEGRADED, DataTrustLevel.LOW,
            AvailabilityPrecision.RETRIEVAL_TIME, False, (), tuple(EvidenceLimitation(
                f"global_review_{index}", text, DataTrustLevel.LOW)
                for index, text in enumerate(LIMITATIONS)), GLOBAL_DOCUMENT_REVIEW_VERSION),)

    def fetch(self, request: ProviderDatasetRequest) -> ProviderEvidenceBatch:
        request.__post_init__()
        review = self.review
        review.__post_init__()
        require_timezone(self.recorded_at, "manual review actual recording time")
        if ((request.dataset, request.market, request.subject) != (DATASET, review.market,
            review.subject) or request.parameters or self.provider_id != PROVIDER
                or not review.reviewed_at.astimezone(UTC) <= self.recorded_at.astimezone(UTC)
                <= request.as_of.astimezone(UTC)):
            raise ValueError("manual review request binding failed")
        content = financial_input_json({"model_version": GLOBAL_DOCUMENT_REVIEW_VERSION,
                                       "recorded_at": self.recorded_at,
                                       "review": review.document()}).encode()
        digest = sha256(content).hexdigest()
        artifact_id = provider_artifact_id(provider=PROVIDER, dataset=DATASET, market=review.market,
            subject=review.subject, source_identity=GLOBAL_DOCUMENT_REVIEW_VERSION,
            source_reference=review.document_url, content_hash=digest)
        artifact = ProviderArtifact(artifact_id, PROVIDER, DATASET, review.market, review.subject,
            GLOBAL_DOCUMENT_REVIEW_VERSION, review.document_url, self.recorded_at, self.recorded_at,
            digest, "application/json", AvailabilityPrecision.RETRIEVAL_TIME, DataTrustLevel.LOW,
            content, GLOBAL_DOCUMENT_REVIEW_VERSION)
        payload: dict[str, object] = {"status": "MANUAL_TRANSCRIPTION_UNQUALIFIED",
            "recorded_at": self.recorded_at.astimezone(UTC).isoformat(),
            "review": review.document(), "observations": [row.observation() for row in review.rows],
            "review_artifact_id": artifact_id, "canonical_population_authorized": False,
            "source_location_verified": False, "accounting_definition_qualified": False,
            "financial_scoring_authorized": False, "investment_scoring_authorized": False,
            "historical_replay_eligible": False, "validation_authorized": False,
            "independent_review": False, "issuer_to_instrument_verified": False,
            "execution_authorized": False}
        record = ProviderEvidenceRecord(provider_evidence_id(provider=PROVIDER, dataset=DATASET,
            market=review.market, subject=review.subject, available_at=self.recorded_at,
            source_reference=review.document_url, payload=payload), PROVIDER, DATASET,
            review.market, review.subject, self.recorded_at, self.recorded_at, review.document_url,
            payload, digest, AvailabilityPrecision.RETRIEVAL_TIME, DataTrustLevel.LOW, LIMITATIONS)
        return ProviderEvidenceBatch(PROVIDER, DATASET, review.market, self.recorded_at,
            review.document_url, {"subject": review.subject,
            "normalization_version": GLOBAL_DOCUMENT_REVIEW_VERSION}, digest, 1, (record,),
            self.capabilities()[0].limitations, (artifact,))
