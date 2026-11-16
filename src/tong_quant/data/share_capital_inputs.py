"""Read-only manual share-count review; never current shares or a market valuation."""

from dataclasses import asdict, dataclass, fields
from datetime import UTC, date, datetime
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
from tong_quant.version import SHARE_CAPITAL_REVIEW_VERSION


@dataclass(frozen=True, slots=True)
class ShareCapitalReview:
    subject: str
    period_end: date
    reviewed_at: datetime
    reviewer: str
    filing_artifact_id: str
    filing_sha256: str
    source_pages: tuple[int, ...]
    source_label: str
    total_shares: int | None
    restricted_shares: int | None
    unrestricted_shares: int | None
    reported_unit: str = "shares"
    currency: str | None = None
    source_column: str = "after_change"
    share_class_scope: str = "issuer_total_as_reported"
    period_basis: str = "report_period_end_as_reported"
    model_version: str = SHARE_CAPITAL_REVIEW_VERSION

    def __post_init__(self) -> None:
        require_timezone(self.reviewed_at, "share-capital review time")
        counts = (self.total_shares, self.restricted_shares, self.unrestricted_shares)
        if (len(self.subject) != 6 or not self.subject.isascii() or not self.subject.isdigit()
                or type(self.period_end) is not date
                or self.period_end > self.reviewed_at.astimezone(ZoneInfo("Asia/Shanghai")).date()
                or self.reported_unit != "shares" or self.currency is not None
                or self.source_column != "after_change"
                or self.share_class_scope != "issuer_total_as_reported"
                or self.period_basis != "report_period_end_as_reported"
                or self.model_version != SHARE_CAPITAL_REVIEW_VERSION
                or not self.reviewer.strip() or not self.source_label.strip()
                or any(len(value) != 64 or any(c not in "0123456789abcdef" for c in value)
                       for value in (self.filing_artifact_id, self.filing_sha256))
                or type(self.source_pages) is not tuple or not self.source_pages
                or len(set(self.source_pages)) != len(self.source_pages)
                or any(type(page) is not int or not 1 <= page <= 1000 for page in self.source_pages)
                or all(value is None for value in counts)
                or any(value is not None and (type(value) is not int or not 0 <= value <= 10**15)
                       for value in counts)
                or self.total_shares == 0):
            raise ValueError("unsupported share-count review scope, units or values")
        reject_sensitive_structure(asdict(self), path="share_capital_review")

    @property
    def review_hash(self) -> str:
        self.__post_init__()
        return sha256(financial_input_json(asdict(self)).encode()).hexdigest()


def parse_share_capital_review(document: dict[str, Any]) -> ShareCapitalReview:
    if set(document) != {"review"} or not isinstance(document["review"], dict):
        raise ValueError("share-capital plan requires a single review table")
    values = dict(document["review"])
    if set(values) - {field.name for field in fields(ShareCapitalReview)}:
        raise ValueError("unknown share-capital review fields")
    try:
        values["period_end"] = date.fromisoformat(values["period_end"])
        values["reviewed_at"] = datetime.fromisoformat(values["reviewed_at"])
        values["source_pages"] = tuple(values["source_pages"])
        for name in ("total_shares", "restricted_shares", "unrestricted_shares"):
            values.setdefault(name, None)
        return ShareCapitalReview(**values)
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError("invalid share-capital review contract") from error


def inspect_share_capital_review(
    store: SQLiteStore, artifacts: FileSystemArtifactStore, review: ShareCapitalReview, *,
    as_of: datetime,
) -> dict[str, object]:
    review.__post_init__()
    require_timezone(as_of, "share-capital cutoff")
    cutoff, reviewed = as_of.astimezone(UTC), review.reviewed_at.astimezone(UTC)
    if reviewed > cutoff:
        raise ValueError("share-capital review is not visible at cutoff")
    binding = bind_reviewed_cninfo_filing(
        store, artifacts, subject=review.subject, filing_artifact_id=review.filing_artifact_id,
        filing_sha256=review.filing_sha256, reviewed_at=review.reviewed_at, as_of=cutoff,
        earliest_publication_date=review.period_end)
    source = binding.artifact
    published, captured = source.published_at.astimezone(UTC), source.retrieved_at.astimezone(UTC)
    residual = (review.total_shares - review.restricted_shares - review.unrestricted_shares
                if review.total_shares is not None and review.restricted_shares is not None
                and review.unrestricted_shares is not None else None)
    output = {
        "subject": review.subject, "market": Market.CHINA_A.value, "as_of": cutoff,
        "review": asdict(review), "review_hash": review.review_hash,
        "source_bound": True, "available_at": reviewed,
        "source_reference": source.source_reference,
        "source_registry_model_version": binding.registry_model_version,
        "source_claimed_published_at": published, "source_captured_at": captured,
        "source_batch": binding.batch_receipt,
        "trust_level": (DataTrustLevel.UNKNOWN.value if source.trust_level is DataTrustLevel.UNKNOWN
                        else DataTrustLevel.LOW.value),
        "availability_precision": AvailabilityPrecision.RETRIEVAL_TIME.value,
        "status": "OBSERVED_UNQUALIFIED",
        "reconciliation": ("INCOMPLETE" if residual is None else
                           "EXACT_AGREEMENT" if residual == 0 else "CONFLICT"),
        "total_minus_components": residual,
        "period_end_age_days": (cutoff.astimezone(ZoneInfo("Asia/Shanghai")).date()
                                - review.period_end).days,
        "current_share_count_status": "UNQUALIFIED_CONTINUITY",
        "market_value": None, "valuation_authorized": False,
        "investment_scoring_authorized": False, "validation_authorized": False,
        "historical_replay_eligible": False, "execution_authorized": False,
        "readiness_promoted": False, "canonical_facts_written": False,
        "model_version": SHARE_CAPITAL_REVIEW_VERSION,
        "limitations": (
            "Manual page/period/column/count annotations, not an independent second review.",
            "Stored PDF and batch consistency do not authenticate issuer content or annotations.",
            "Issuer counts as reported, not CNY book share capital, EPS weighted-average shares "
            "or independently qualified outstanding/free-float shares.",
            "Unrestricted shares are not an index free-float measure or market value.",
            "Period-end counts cannot be carried to a later quote without share-class, buyback, "
            "issuance, cancellation and action continuity evidence.",
            "No price multiplication, PE/PB/PS, source promotion, scoring or trading authority.",
            "Review plan remains external to SQLite; no populated canonical fact is claimed.",
        ),
    }
    return {**output, "inspection_hash": sha256(financial_input_json(output).encode()).hexdigest()}
