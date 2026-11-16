"""Explicit manual issuer-filing extraction, not native-provider mapping approval."""

import json
from dataclasses import asdict, dataclass, fields
from datetime import date, datetime
from decimal import Decimal, localcontext
from hashlib import sha256
from typing import Any
from urllib.parse import urlsplit

from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.financial_inputs import (
    BANK_PERIOD_END_RATIO_METRICS,
    CNY_FILING_UNIT_MULTIPLIERS,
    NONFINANCIAL_BALANCE_METRICS,
    NONFINANCIAL_CASH_COMPONENT_METRICS,
    NONFINANCIAL_YTD_RATIO_METRICS,
)
from tong_quant.data.providers.contracts import (
    CNINFO_DISCLOSURES_DATASET,
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
from tong_quant.version import (
    REVIEWED_BANK_RATIOS_VERSION,
    REVIEWED_COMPARATIVE_FACTS_VERSION,
    REVIEWED_FILING_FACTS_VERSION,
    REVIEWED_MONETARY_FACTS_VERSION,
    REVIEWED_NONFINANCIAL_CASH_BALANCE_VERSION,
    REVIEWED_NONFINANCIAL_PARENT_EQUITY_VERSION,
    REVIEWED_NONFINANCIAL_RATIOS_VERSION,
)

REVIEWED_FILING_DATASET = "reviewed_group_filing_facts"
_METRICS = {
    "equity_attributable_to_parent": "balance",
    "revenue": "income",
    "profit_attributable_to_parent": "income",
    "total_assets": "balance",
    "operating_cash_flow": "cash_flow",
    **dict.fromkeys(BANK_PERIOD_END_RATIO_METRICS, "bank_asset_quality"),
    **dict.fromkeys(NONFINANCIAL_YTD_RATIO_METRICS, "nonfinancial_profitability"),
    **dict.fromkeys(NONFINANCIAL_BALANCE_METRICS, "balance"),
    **dict.fromkeys(NONFINANCIAL_CASH_COMPONENT_METRICS, "cash_flow"),
}
_LIMITATIONS = (
    EvidenceLimitation(
        "manual_filing_extraction",
        "Values, pages and group/current-period column are manual annotations, not "
        "machine-authenticated PDF extraction or an independent second review",
        DataTrustLevel.LOW,
    ),
    EvidenceLimitation(
        "retrieval_time_filing_facts",
        "Facts become visible no earlier than source capture and review; original numeric "
        "revision history and claimed disclosure timestamps remain unverified",
        DataTrustLevel.LOW,
    ),
    EvidenceLimitation(
        "bounded_group_filing_scope",
        "Only explicit group CNY-million observations are supported; no native-provider "
        "mapping, provider independence, dataset readiness or investment scoring is approved",
        DataTrustLevel.LOW,
    ),
)
_COMPARATIVE_LIMITATIONS = (
    EvidenceLimitation(
        "manual_comparative_extraction",
        "Comparative column, filing edition and period labels are manual annotations, "
        "not machine-authenticated extraction or an independent second review",
        DataTrustLevel.LOW,
    ),
    *_LIMITATIONS[1:],
    EvidenceLimitation(
        "same_filing_comparatives_only",
        "Historical amounts are as presented in this later filing; original historical "
        "publication values, restatements and accounting comparability remain unverified",
        DataTrustLevel.LOW,
    ),
)
_BANK_RATIO_LIMITATIONS = (
    _LIMITATIONS[0], _LIMITATIONS[1],
    EvidenceLimitation(
        "bounded_bank_ratio_scope",
        "Only explicit group/current-period-end bank ratios in percent are supported; "
        "1.23 means 1.23 percent, not a fraction or CNY amount. No annualization, "
        "comparative growth, scoring policy or source-trust promotion is approved",
        DataTrustLevel.LOW,
    ),
)
_MONETARY_LIMITATIONS = (
    *_LIMITATIONS[:2],
    EvidenceLimitation(
        "explicit_monetary_units_and_cash_flow",
        "Only explicitly annotated CNY/yuan, CNY-thousand or CNY-million amounts are converted. "
        "Nonfinancial operating cash flow is calendar-YTD net operating cash flow, not free "
        "cash flow, earnings or a financial score. Unit labels are not independently verified",
        DataTrustLevel.LOW,
    ),
)
_NONFINANCIAL_RATIO_LIMITATIONS = (
    *_LIMITATIONS[:2],
    EvidenceLimitation(
        "bounded_nonfinancial_ytd_roe",
        "Only explicit group/nonfinancial current calendar-YTD weighted ROE in percent is "
        "supported, including losses. Preserve the reported percentage value without annualizing, "
        "recomputing from ending equity, aliasing generic ROE/ROIC or inferring comparatives. "
        "Manual basis annotations are not independently verified or admitted for scoring",
        DataTrustLevel.LOW,
    ),
)
_NONFINANCIAL_CASH_BALANCE_LIMITATIONS = (
    *_LIMITATIONS[:2],
    EvidenceLimitation(
        "bounded_nonfinancial_cash_balance",
        "Current explicit group CNY balance and calendar-YTD cash-flow observations only. "
        "Total/current liabilities are not interest-bearing debt; monetary funds are not "
        "proven unrestricted cash or cash equivalents. Blank borrowing lines are not zero. "
        "Cash-flow reconciliation does not establish recurring cash quality or scoring authority",
        DataTrustLevel.LOW,
    ),
)
_PARENT_EQUITY_LIMITATIONS = (
    *_LIMITATIONS[:2],
    EvidenceLimitation(
        "bounded_nonfinancial_parent_equity",
        "Current group equity attributable to parent owners, including negative values. "
        "Not total assets, minority-inclusive equity, market capitalization or fair value. "
        "No valuation multiple, scoring authority or independent verification is implied",
        DataTrustLevel.LOW,
    ),
)


def _digest(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdef" for char in value)


@dataclass(frozen=True, slots=True)
class ReviewedFilingRow:
    metric: str
    statement: str
    source_value: Decimal
    period_start: date | None
    source_pages: tuple[int, ...]
    source_label: str

    def __post_init__(self) -> None:
        if (
            _METRICS.get(self.metric) != self.statement
            or not self.source_label.strip() or type(self.source_pages) is not tuple
            or not self.source_pages
            or len(set(self.source_pages)) != len(self.source_pages)
            or any(type(page) is not int or not 1 <= page <= 1000 for page in self.source_pages)
            or not isinstance(self.source_value, Decimal) or not self.source_value.is_finite()
            or len(self.source_value.as_tuple().digits) > 128
            or abs(int(self.source_value.as_tuple().exponent)) > 100
            or (self.statement in {"income", "cash_flow", "nonfinancial_profitability"}
                and self.period_start is None)
            or (self.statement == "balance" and self.period_start is not None)
            or (self.metric in (
                NONFINANCIAL_BALANCE_METRICS | NONFINANCIAL_CASH_COMPONENT_METRICS
            ) and self.source_value < 0)
            or (self.statement == "bank_asset_quality" and (
                self.period_start is not None or self.source_value < 0
                or (self.metric == "nonperforming_loan_ratio" and self.source_value > 100)))
        ):
            raise ValueError("unsupported reviewed filing row semantics")


@dataclass(frozen=True, slots=True)
class FilingExtractionReview:
    subject: str
    period_end: date
    reviewed_at: datetime
    reviewer: str
    filing_artifact_id: str
    filing_sha256: str
    source_unit: str
    currency: str
    reporting_scope: str
    source_column: str
    audit_status: str
    sector_profile: str
    rows: tuple[ReviewedFilingRow, ...]
    filing_period_end: date | None = None
    comparability: str | None = None
    issuer_revision_status: str | None = None
    measurement_basis: str | None = None

    def __post_init__(self) -> None:
        require_timezone(self.reviewed_at, "filing extraction reviewed_at")
        if (
            len(self.subject) != 6 or not self.subject.isascii() or not self.subject.isdigit()
            or not self.reviewer.strip() or not _digest(self.filing_artifact_id)
            or not _digest(self.filing_sha256) or self.reporting_scope != "group"
            or self.audit_status not in {"audited", "unaudited"}
            or self.sector_profile not in {"bank", "nonfinancial", "unknown"}
            or type(self.rows) is not tuple or not 1 <= len(self.rows) <= len(_METRICS)
            or len({row.metric for row in self.rows}) != len(self.rows)
            or self.period_end > self.reviewed_at.date()
            or any(row.period_start is not None and row.period_start > self.period_end
                   for row in self.rows)
        ):
            raise ValueError("unsupported reviewed filing scope")
        ratio_rows = any(row.metric in BANK_PERIOD_END_RATIO_METRICS for row in self.rows)
        nonfinancial_ratios = any(row.metric in NONFINANCIAL_YTD_RATIO_METRICS
                                 for row in self.rows)
        if nonfinancial_ratios:
            if (
                not all(row.metric in NONFINANCIAL_YTD_RATIO_METRICS for row in self.rows)
                or self.source_unit != "percent" or self.currency != "not_applicable"
                or self.sector_profile != "nonfinancial"
                or self.measurement_basis != "ytd_unannualized_ratio"
                or self.filing_period_end is not None
                or (self.period_end.month, self.period_end.day)
                not in {(3, 31), (6, 30), (9, 30), (12, 31)}
                or any(row.period_start != date(self.period_end.year, 1, 1)
                       for row in self.rows)
            ):
                raise ValueError("nonfinancial ROE requires a separate percent/calendar-YTD review")
        elif ratio_rows:
            if (
                not all(row.metric in BANK_PERIOD_END_RATIO_METRICS for row in self.rows)
                or self.source_unit != "percent" or self.currency != "not_applicable"
                or self.sector_profile != "bank" or self.measurement_basis != "period_end_ratio"
                or self.filing_period_end is not None
            ):
                raise ValueError("bank ratios require a separate percent/period-end review")
        elif (self.source_unit not in CNY_FILING_UNIT_MULTIPLIERS or self.currency != "CNY"
              or self.measurement_basis is not None):
            raise ValueError("monetary observations require explicit supported CNY unit semantics")
        if any(row.statement == "cash_flow" for row in self.rows) and (
            self.sector_profile != "nonfinancial"
            or (self.period_end.month, self.period_end.day)
            not in {(3, 31), (6, 30), (9, 30), (12, 31)}
            or any(row.statement == "cash_flow"
                   and row.period_start != date(self.period_end.year, 1, 1) for row in self.rows)
        ):
            raise ValueError("operating cash flow requires nonfinancial calendar-YTD semantics")
        if any(row.metric in (NONFINANCIAL_BALANCE_METRICS | NONFINANCIAL_CASH_COMPONENT_METRICS
                              | {"equity_attributable_to_parent"})
               for row in self.rows) and (
            self.sector_profile != "nonfinancial" or self.filing_period_end is not None
            or (self.period_end.month, self.period_end.day)
            not in {(3, 31), (6, 30), (9, 30), (12, 31)}
        ):
            raise ValueError(
                "nonfinancial cash/balance inputs require current calendar-quarter scope")
        if self.filing_period_end is None:
            if (self.source_column != "group_current_period" or self.comparability is not None
                    or self.issuer_revision_status is not None):
                raise ValueError("comparative review requires explicit filing-edition semantics")
        else:
            filing_end = self.filing_period_end
            if (
                filing_end > self.reviewed_at.date() or filing_end <= self.period_end
                or (filing_end.month, filing_end.day) not in {(3, 31), (6, 30), (9, 30), (12, 31)}
                or self.comparability != "as_presented_same_filing"
                or self.issuer_revision_status != "unverified"
            ):
                raise ValueError("unsupported comparative filing edition/basis")
            if self.source_column == "group_prior_year_period":
                if (
                    (self.period_end.year, self.period_end.month, self.period_end.day)
                    != (filing_end.year - 1, filing_end.month, filing_end.day)
                    or any(row.statement not in {"income", "cash_flow"}
                           or row.period_start != date(self.period_end.year, 1, 1)
                           for row in self.rows)
                ):
                    raise ValueError("prior-year flow requires matching year-to-date periods")
            elif self.source_column == "group_prior_year_end":
                if (self.period_end != date(filing_end.year - 1, 12, 31)
                        or any(row.statement != "balance" for row in self.rows)):
                    raise ValueError("prior-year-end stock requires explicit balance observations")
            else:
                raise ValueError("unsupported comparative source column")
        reject_sensitive_structure(asdict(self), path="filing_extraction_review")

    @property
    def model_version(self) -> str:
        if any(row.metric == "equity_attributable_to_parent" for row in self.rows):
            return REVIEWED_NONFINANCIAL_PARENT_EQUITY_VERSION
        if any(row.metric in (NONFINANCIAL_BALANCE_METRICS | NONFINANCIAL_CASH_COMPONENT_METRICS)
               for row in self.rows):
            return REVIEWED_NONFINANCIAL_CASH_BALANCE_VERSION
        if self.measurement_basis == "ytd_unannualized_ratio":
            return REVIEWED_NONFINANCIAL_RATIOS_VERSION
        if self.measurement_basis is not None:
            return REVIEWED_BANK_RATIOS_VERSION
        if self.source_unit != "CNY_million" or any(
            row.statement == "cash_flow" for row in self.rows
        ):
            return REVIEWED_MONETARY_FACTS_VERSION
        return (REVIEWED_FILING_FACTS_VERSION if self.filing_period_end is None
                else REVIEWED_COMPARATIVE_FACTS_VERSION)

    def document(self) -> dict[str, Any]:
        document = asdict(self)
        if self.measurement_basis is None:
            document.pop("measurement_basis")
        if self.filing_period_end is None:
            # Preserve the exact v1 packet representation and all prior evidence identities.
            for key in ("filing_period_end", "comparability", "issuer_revision_status"):
                document.pop(key)
        return document


def parse_filing_review(document: dict[str, Any]) -> FilingExtractionReview:
    """Require a dedicated extraction plan; numeric spot reviews are not accepted."""
    reject_sensitive_structure(document, path="filing_extraction_plan")
    if set(document) != {"review", "rows"}:
        raise ValueError("filing extraction plan schema mismatch")
    common = dict(document["review"])
    optional = {"filing_period_end", "comparability", "issuer_revision_status", "measurement_basis"}
    required = {item.name for item in fields(FilingExtractionReview)} - {"rows"} - optional
    if set(common) - optional != required:
        raise ValueError("filing extraction review schema mismatch")
    common["period_end"] = date.fromisoformat(common["period_end"])
    common["reviewed_at"] = datetime.fromisoformat(common["reviewed_at"])
    if common.get("filing_period_end") is not None:
        common["filing_period_end"] = date.fromisoformat(common["filing_period_end"])
    rows = []
    for raw in document["rows"]:
        values = dict(raw)
        if set(values) != {item.name for item in fields(ReviewedFilingRow)}:
            raise ValueError("filing extraction row schema mismatch")
        if not isinstance(values["source_value"], str):
            raise ValueError("filing source values must be quoted decimals")
        values["source_value"] = Decimal(values["source_value"])
        values["period_start"] = (
            date.fromisoformat(values["period_start"]) if values["period_start"] else None
        )
        values["source_pages"] = tuple(values["source_pages"])
        rows.append(ReviewedFilingRow(**values))
    return FilingExtractionReview(**common, rows=tuple(rows))


@dataclass(frozen=True, slots=True)
class ReviewedFilingAdapter:
    review: FilingExtractionReview
    source: ProviderArtifact
    provider_id: str = "cninfo_direct"

    @property
    def limitations(self) -> tuple[EvidenceLimitation, ...]:
        if self.review.model_version == REVIEWED_NONFINANCIAL_PARENT_EQUITY_VERSION:
            return _PARENT_EQUITY_LIMITATIONS
        if self.review.model_version == REVIEWED_NONFINANCIAL_CASH_BALANCE_VERSION:
            return _NONFINANCIAL_CASH_BALANCE_LIMITATIONS
        if self.review.model_version == REVIEWED_NONFINANCIAL_RATIOS_VERSION:
            return _NONFINANCIAL_RATIO_LIMITATIONS
        if self.review.measurement_basis is not None:
            return _BANK_RATIO_LIMITATIONS
        if self.review.model_version == REVIEWED_MONETARY_FACTS_VERSION:
            return (*_MONETARY_LIMITATIONS, *(
                _COMPARATIVE_LIMITATIONS[-1:] if self.review.filing_period_end else ()))
        return _LIMITATIONS if self.review.filing_period_end is None else _COMPARATIVE_LIMITATIONS

    def capabilities(self) -> tuple[ProviderDatasetCapability, ...]:
        return (ProviderDatasetCapability(
            self.provider_id, REVIEWED_FILING_DATASET, (Market.CHINA_A,),
            ProviderCapabilityStatus.DEGRADED, DataTrustLevel.LOW,
            AvailabilityPrecision.RETRIEVAL_TIME, False, (), self.limitations,
            model_version=self.review.model_version,
        ),)

    def fetch(self, request: ProviderDatasetRequest) -> ProviderEvidenceBatch:
        review, source = self.review, self.source
        url = urlsplit(source.source_reference)
        source_id = provider_artifact_id(
            provider=source.provider, dataset=source.dataset, market=source.market,
            subject=source.subject, source_identity=source.source_identity,
            source_reference=source.source_reference, content_hash=source.content_hash,
        )
        available = max(review.reviewed_at, source.retrieved_at, source.published_at)
        if (
            (request.dataset, request.market, request.subject)
            != (REVIEWED_FILING_DATASET, Market.CHINA_A, review.subject)
            or request.parameters or self.provider_id != "cninfo_direct"
            or source.provider != "cninfo_direct" or source.dataset != CNINFO_DISCLOSURES_DATASET
            or source.market is not Market.CHINA_A or source.subject != review.subject
            or source.artifact_id != source_id or source_id != review.filing_artifact_id
            or source.content_hash != review.filing_sha256
            or sha256(source.content).hexdigest() != review.filing_sha256
            or source.media_type != "application/pdf" or not source.content.startswith(b"%PDF")
            or len(source.content) > 50 * 1024 * 1024
            or url.scheme != "https" or url.netloc != "static.cninfo.com.cn"
            or not url.path.startswith("/finalpage/") or not url.path.lower().endswith(".pdf")
            or url.query or url.fragment or available > request.as_of
            or source.published_at.date() < (review.filing_period_end or review.period_end)
        ):
            raise ValueError("reviewed filing source/request binding failed")
        trust = DataTrustLevel.UNKNOWN if source.trust_level is DataTrustLevel.UNKNOWN else (
            DataTrustLevel.LOW
        )
        document = {
            "review": review.document(), "source_artifact_id": source_id,
            "source_reference": source.source_reference, "source_sha256": source.content_hash,
            "source_retrieved_at": source.retrieved_at.isoformat(),
            "source_claimed_published_at": source.published_at.isoformat(),
            "source_trust_level": source.trust_level.value,
            "source_availability_precision": source.availability_precision.value,
            "model_version": review.model_version,
        }
        content = json.dumps(document, sort_keys=True, separators=(",", ":"), default=str).encode()
        digest = sha256(content).hexdigest()
        artifact_id = provider_artifact_id(
            provider=self.provider_id, dataset=request.dataset, market=request.market,
            subject=review.subject, source_identity=source.source_identity,
            source_reference=source.source_reference, content_hash=digest,
        )
        artifact = ProviderArtifact(
            artifact_id, self.provider_id, request.dataset, request.market, review.subject,
            source.source_identity, source.source_reference, available, available, digest,
            "application/json", AvailabilityPrecision.RETRIEVAL_TIME, trust, content,
            model_version=review.model_version,
        )
        records = []
        for row in sorted(review.rows, key=lambda item: item.metric):
            with localcontext() as context:
                context.prec = 150
                value = (row.source_value if review.measurement_basis is not None
                         else row.source_value * CNY_FILING_UNIT_MULTIPLIERS[review.source_unit])
            payload: dict[str, object] = {
                "metric": row.metric, "statement": row.statement, "value": str(value),
                "source_value": str(row.source_value), "source_unit": review.source_unit,
                "currency": review.currency, "unit": "absolute",
                "period_start": row.period_start.isoformat() if row.period_start else None,
                "period_end": review.period_end.isoformat(), "reporting_scope": "group",
                "value_kind": "stock" if row.statement == "balance" else "flow",
                "source_pages": row.source_pages, "source_label": row.source_label,
                "source_column": review.source_column, "sector_profile": review.sector_profile,
                "audit_status": review.audit_status, "reviewer": review.reviewer,
                "reviewed_at": review.reviewed_at.isoformat(), "review_artifact_id": artifact_id,
                "filing_artifact_id": source_id, "filing_sha256": source.content_hash,
                "model_version": review.model_version,
                "historical_replay_eligible": False, "investment_scoring_authorized": False,
                "validation_authorized": False, "native_mapping_authorized": False,
                "independent_provider_validation": False,
            }
            if review.measurement_basis is not None:
                payload.update({
                    "currency": None, "unit": "percent", "value_kind": "ratio",
                    "measurement_basis": review.measurement_basis,
                })
            if review.filing_period_end is not None:
                payload.update({
                    "filing_period_end": review.filing_period_end.isoformat(),
                    "comparability": review.comparability,
                    "issuer_revision_status": review.issuer_revision_status,
                })
            reject_sensitive_structure(payload)
            records.append(ProviderEvidenceRecord(
                provider_evidence_id(
                    provider=self.provider_id, dataset=request.dataset, market=request.market,
                    subject=review.subject, available_at=available,
                    source_reference=source.source_reference, payload=payload,
                ),
                self.provider_id, request.dataset, request.market, review.subject, available,
                available, source.source_reference, payload, digest,
                AvailabilityPrecision.RETRIEVAL_TIME, trust,
                tuple(item.description for item in self.limitations),
                published_at=source.published_at,
            ))
        return ProviderEvidenceBatch(
            self.provider_id, request.dataset, request.market, available, source.source_reference,
            {"subject": review.subject, "normalization_version": review.model_version},
            digest, len(records), tuple(records), self.limitations, artifacts=(artifact,),
        )
