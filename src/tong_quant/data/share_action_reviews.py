"""Manual document observations, not a canonical or complete corporate-action ledger."""

from dataclasses import asdict, dataclass, fields
from datetime import UTC, date, datetime
from enum import StrEnum
from hashlib import sha256
from typing import Any
from zoneinfo import ZoneInfo

from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.reviewed_filing_source import bind_reviewed_cninfo_filing
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market
from tong_quant.domain.models import require_timezone
from tong_quant.version import SHARE_ACTION_REVIEW_VERSION


class ShareActionScope(StrEnum):
    ISSUER_CAPITAL = "issuer_capital"
    HOLDER_OR_PLAN = "holder_or_plan"
    UNDETERMINED = "undetermined"


class ShareActionStage(StrEnum):
    PROPOSED = "proposed"
    PENDING = "pending"
    REPORTED_COMPLETED = "reported_completed"
    UNDETERMINED = "undetermined"


class ShareActionKind(StrEnum):
    TRANSFER = "transfer"
    DISPOSAL = "disposal"
    PLAN_TERMINATION = "plan_termination"
    CANCELLATION = "cancellation"
    ISSUANCE = "issuance"
    SPLIT_OR_BONUS = "split_or_bonus"
    UNDETERMINED = "undetermined"


@dataclass(frozen=True, slots=True)
class ShareActionObservation:
    reference: str
    scope: ShareActionScope
    kind: ShareActionKind
    stage: ShareActionStage
    source_pages: tuple[int, ...]
    quantity_shares: int | None = None
    effective_date: date | None = None

    def __post_init__(self) -> None:
        if (not isinstance(self.reference, str) or not self.reference.strip()
                or not isinstance(self.scope, ShareActionScope)
                or not isinstance(self.kind, ShareActionKind)
                or not isinstance(self.stage, ShareActionStage)
                or type(self.source_pages) is not tuple or not self.source_pages
                or len(set(self.source_pages)) != len(self.source_pages)
                or any(type(page) is not int or not 1 <= page <= 1000 for page in self.source_pages)
                or (self.quantity_shares is not None and (type(self.quantity_shares) is not int
                    or not 0 < self.quantity_shares <= 10**15))
                or (self.effective_date is not None and (type(self.effective_date) is not date
                    or self.stage is not ShareActionStage.REPORTED_COMPLETED))):
            raise ValueError("invalid share-action observation, quantity or effective date")
        holder_kinds = {ShareActionKind.TRANSFER, ShareActionKind.DISPOSAL,
                        ShareActionKind.PLAN_TERMINATION}
        issuer_kinds = {ShareActionKind.CANCELLATION, ShareActionKind.ISSUANCE,
                        ShareActionKind.SPLIT_OR_BONUS}
        if ((self.kind in holder_kinds and self.scope is not ShareActionScope.HOLDER_OR_PLAN)
                or (self.kind in issuer_kinds and self.scope is not ShareActionScope.ISSUER_CAPITAL)
                or (self.kind is ShareActionKind.UNDETERMINED
                    and self.scope is not ShareActionScope.UNDETERMINED)
                or (self.kind in {ShareActionKind.UNDETERMINED, ShareActionKind.PLAN_TERMINATION}
                    and self.quantity_shares is not None)):
            raise ValueError("share-action scope/kind/quantity semantics rejected")
        reject_sensitive_structure(asdict(self), path="share_action_observation")


@dataclass(frozen=True, slots=True)
class ShareActionDocumentReview:
    subject: str
    reviewed_at: datetime
    reviewer: str
    filing_artifact_id: str
    filing_sha256: str
    observations: tuple[ShareActionObservation, ...]
    model_version: str = SHARE_ACTION_REVIEW_VERSION

    def __post_init__(self) -> None:
        require_timezone(self.reviewed_at, "share-action review time")
        if (not isinstance(self.subject, str) or len(self.subject) != 6
                or not self.subject.isascii() or not self.subject.isdigit()
                or not isinstance(self.reviewer, str) or not self.reviewer.strip()
                or any(not isinstance(value, str) or len(value) != 64
                       or any(c not in "0123456789abcdef" for c in value)
                       for value in (self.filing_artifact_id, self.filing_sha256))
                or type(self.observations) is not tuple or not 1 <= len(self.observations) <= 128
                or any(not isinstance(item, ShareActionObservation) for item in self.observations)
                or self.model_version != SHARE_ACTION_REVIEW_VERSION):
            raise ValueError("invalid share-action document review")
        references = []
        for item in self.observations:
            item.__post_init__()
            references.append(item.reference)
        if len(set(references)) != len(references):
            raise ValueError("duplicate share-action observation reference")
        reject_sensitive_structure(asdict(self), path="share_action_document_review")

    @property
    def review_hash(self) -> str:
        self.__post_init__()
        return sha256(financial_input_json(asdict(self)).encode()).hexdigest()


def parse_share_action_review(document: dict[str, Any]) -> ShareActionDocumentReview:
    if set(document) != {"review"} or not isinstance(document["review"], dict):
        raise ValueError("share-action plan requires a single review table")
    values = dict(document["review"])
    if set(values) - {field.name for field in fields(ShareActionDocumentReview)}:
        raise ValueError("unknown share-action review fields")
    try:
        values["reviewed_at"] = datetime.fromisoformat(values["reviewed_at"])
        raw = values["observations"]
        if not isinstance(raw, list) or not 1 <= len(raw) <= 128:
            raise ValueError("share-action observations must be a bounded list")
        observations = []
        for row in raw:
            if not isinstance(row, dict) or set(row) - {
                field.name for field in fields(ShareActionObservation)
            }:
                raise ValueError("unknown share-action observation fields")
            item = dict(row)
            item["scope"] = ShareActionScope(item["scope"])
            item["kind"] = ShareActionKind(item["kind"])
            item["stage"] = ShareActionStage(item["stage"])
            item["source_pages"] = tuple(item["source_pages"])
            if "effective_date" in item:
                item["effective_date"] = date.fromisoformat(item["effective_date"])
            observations.append(ShareActionObservation(**item))
        values["observations"] = tuple(observations)
        return ShareActionDocumentReview(**values)
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError("invalid share-action review contract") from error


def inspect_share_action_review(
    store: SQLiteStore, artifacts: FileSystemArtifactStore, review: ShareActionDocumentReview, *,
    as_of: datetime,
) -> dict[str, Any]:
    review.__post_init__()
    binding = bind_reviewed_cninfo_filing(
        store, artifacts, subject=review.subject, filing_artifact_id=review.filing_artifact_id,
        filing_sha256=review.filing_sha256, reviewed_at=review.reviewed_at, as_of=as_of)
    source = binding.artifact
    publication_date = source.published_at.astimezone(ZoneInfo("Asia/Shanghai")).date()
    if any(item.effective_date is not None and item.effective_date > publication_date
           for item in review.observations):
        raise ValueError("completed share-action date follows claimed document publication")
    observations = [{**asdict(item),
                     "quantity_role": (item.scope.value
                                       if item.quantity_shares is not None else None),
                     "effective_date_precision": "DATE" if item.effective_date else "NOT_REPORTED",
                     "issuer_share_delta": None}
                    for item in review.observations]
    output = {
        "subject": review.subject, "market": Market.CHINA_A.value,
        "as_of": as_of.astimezone(UTC), "review": asdict(review),
        "review_hash": review.review_hash, "source_bound": True,
        "announcement_id": source.source_identity,
        "source_reference": source.source_reference, "filing_sha256": source.content_hash,
        "source_registry_model_version": binding.registry_model_version,
        "source_claimed_published_at": source.published_at.astimezone(UTC),
        "source_captured_at": source.retrieved_at.astimezone(UTC),
        "source_batch": binding.batch_receipt, "available_at": review.reviewed_at.astimezone(UTC),
        "status": "MANUALLY_REVIEWED_UNQUALIFIED", "observations": observations,
        "trust_level": (DataTrustLevel.UNKNOWN.value if source.trust_level is DataTrustLevel.UNKNOWN
                        else DataTrustLevel.LOW.value),
        "availability_precision": AvailabilityPrecision.RETRIEVAL_TIME.value,
        "model_version": SHARE_ACTION_REVIEW_VERSION,
        "effective_action_timeline": "NOT_ESTABLISHED", "issuer_share_delta": None,
        "current_shares": None, "market_value": None, "canonical_facts_written": False,
        "valuation_authorized": False, "investment_scoring_authorized": False,
        "validation_authorized": False, "historical_replay_eligible": False,
        "execution_authorized": False, "readiness_promoted": False,
        "limitations": (
            "Manual page/semantic annotations require independent second review.",
            "Quantity belongs to its declared scope; no issuer delta or aggregation is inferred.",
            "Holder transfers/disposals and plan termination are not issuer cancellation.",
            "Proposals/pending events are not implemented changes; unreported dates stay null.",
            "Do not invert rounded percentages into total shares or infer zero issuer change.",
            "PDF byte/batch binding does not authenticate source truth, page labels or coverage.",
            "Review availability is actual review time, not historical publication availability.",
            "External annotation only; no action ledger, current shares, valuation or admission.",
        ),
    }
    return {**output, "inspection_hash": sha256(financial_input_json(output).encode()).hexdigest()}
