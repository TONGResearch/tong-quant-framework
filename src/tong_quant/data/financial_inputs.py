"""Immutable financial input diagnostics, independent of any provider SDK."""

import json
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from types import MappingProxyType

from tong_quant.domain.enums import AssetType, Market
from tong_quant.domain.models import FundamentalFact, require_timezone
from tong_quant.version import FINANCIAL_INPUTS_VERSION

BANK_PERIOD_END_RATIO_METRICS = frozenset({"nonperforming_loan_ratio", "provision_coverage_ratio"})
NONFINANCIAL_YTD_RATIO_METRICS = frozenset({"roe_weighted_ytd_unannualized"})
NONFINANCIAL_BALANCE_METRICS = frozenset({
    "total_liabilities", "current_liabilities", "monetary_funds",
})
NONFINANCIAL_CASH_COMPONENT_METRICS = frozenset({
    "operating_cash_inflow", "operating_cash_outflow",
})
NONFINANCIAL_CASH_FLOW_METRICS = NONFINANCIAL_CASH_COMPONENT_METRICS | {"operating_cash_flow"}
CNY_FILING_UNIT_MULTIPLIERS = MappingProxyType({
    "CNY": Decimal("1"), "CNY_thousand": Decimal("1000"),
    "CNY_million": Decimal("1000000"),
})


def financial_input_json(value: object) -> str:
    def encode(item: object) -> str:
        return item.astimezone(UTC).isoformat() if isinstance(item, datetime) else str(item)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=encode)


class FinancialBindingStatus(StrEnum):
    SOURCE_BOUND = "source_bound_observation"
    REJECTED = "source_binding_rejected"
    UNSUPPORTED = "unsupported_source"


@dataclass(frozen=True, slots=True)
class FinancialFactInspection:
    fact: FundamentalFact
    status: FinancialBindingStatus
    reasons: tuple[str, ...]
    reporting_scope: str | None = None
    sector_profile: str | None = None
    evidence_id: str | None = None
    review_artifact_id: str | None = None
    filing_artifact_id: str | None = None
    filing_sha256: str | None = None
    source_pages: tuple[int, ...] = ()
    source_unit: str | None = None
    source_column: str | None = None
    audit_status: str | None = None
    statement: str | None = None
    filing_period_end: date | None = None
    comparability: str | None = None
    issuer_revision_status: str | None = None
    measurement_basis: str | None = None

    def __post_init__(self) -> None:
        if (not isinstance(self.status, FinancialBindingStatus) or type(self.reasons) is not tuple
                or not self.reasons or type(self.source_pages) is not tuple):
            raise ValueError("financial inspection requires immutable reasons/pages")
        if self.status is FinancialBindingStatus.SOURCE_BOUND and (
            self.reporting_scope != "group"
            or self.source_column not in {
                "group_current_period", "group_prior_year_period", "group_prior_year_end",
            }
            or self.audit_status not in {"audited", "unaudited"}
            or self.statement not in {
                "income", "balance", "cash_flow", "bank_asset_quality",
                "nonfinancial_profitability",
            }
            or self.sector_profile not in {"bank", "nonfinancial", "unknown"}
            or not self.source_pages or any(type(page) is not int or page < 1
                                           for page in self.source_pages)
            or any(value is None or len(value) != 64
                   or any(char not in "0123456789abcdef" for char in value) for value in (
                self.evidence_id, self.review_artifact_id,
                self.filing_artifact_id, self.filing_sha256,
            ))
        ):
            raise ValueError("source-bound financial observation requires explicit provenance")
        if self.status is FinancialBindingStatus.SOURCE_BOUND:
            if self.fact.metric in BANK_PERIOD_END_RATIO_METRICS:
                if (
                    self.source_unit != "percent" or self.fact.unit != "percent"
                    or self.fact.currency is not None or self.sector_profile != "bank"
                    or self.statement != "bank_asset_quality"
                    or self.measurement_basis != "period_end_ratio"
                    or self.source_column != "group_current_period"
                    or self.fact.period_start is not None or self.fact.value < 0
                    or (self.fact.metric == "nonperforming_loan_ratio" and self.fact.value > 100)
                    or self.filing_period_end != self.fact.period_end
                    or self.comparability is not None or self.issuer_revision_status is not None
                ):
                    raise ValueError("bank ratio requires explicit percent/period-end semantics")
            elif self.fact.metric in NONFINANCIAL_YTD_RATIO_METRICS:
                if (
                    self.source_unit != "percent" or self.fact.unit != "percent"
                    or self.fact.currency is not None or self.sector_profile != "nonfinancial"
                    or self.statement != "nonfinancial_profitability"
                    or self.measurement_basis != "ytd_unannualized_ratio"
                    or self.source_column != "group_current_period"
                    or self.fact.period_start != date(self.fact.period_end.year, 1, 1)
                    or (self.fact.period_end.month, self.fact.period_end.day)
                    not in {(3, 31), (6, 30), (9, 30), (12, 31)}
                    or self.filing_period_end != self.fact.period_end
                    or self.comparability is not None or self.issuer_revision_status is not None
                ):
                    raise ValueError(
                        "nonfinancial ROE requires explicit percent/calendar-YTD basis")
            elif (self.source_unit not in CNY_FILING_UNIT_MULTIPLIERS
                  or self.fact.unit != "absolute"
                  or self.fact.currency != "CNY" or self.measurement_basis is not None
                  or self.statement not in {"income", "balance", "cash_flow"}):
                raise ValueError("monetary observation requires explicit currency/amount semantics")
            if self.fact.metric in (
                NONFINANCIAL_BALANCE_METRICS | NONFINANCIAL_CASH_COMPONENT_METRICS
            ) and (
                self.sector_profile != "nonfinancial" or self.fact.value < 0
                or self.source_column != "group_current_period"
                or self.filing_period_end != self.fact.period_end
                or self.comparability is not None or self.issuer_revision_status is not None
                or (self.fact.period_end.month, self.fact.period_end.day)
                not in {(3, 31), (6, 30), (9, 30), (12, 31)}
                or (self.fact.metric in NONFINANCIAL_BALANCE_METRICS and (
                    self.statement != "balance" or self.fact.period_start is not None))
            ):
                raise ValueError("nonfinancial cash/balance inputs require current explicit scope")
            if self.fact.metric == "equity_attributable_to_parent" and (
                self.sector_profile != "nonfinancial"
                or self.source_column != "group_current_period"
                or self.filing_period_end != self.fact.period_end
                or self.comparability is not None or self.issuer_revision_status is not None
                or self.statement != "balance" or self.fact.period_start is not None
                or (self.fact.period_end.month, self.fact.period_end.day)
                not in {(3, 31), (6, 30), (9, 30), (12, 31)}
            ):
                raise ValueError(
                    "parent equity requires explicit current nonfinancial balance scope")
            if (self.statement == "cash_flow"
                    or self.fact.metric in NONFINANCIAL_CASH_FLOW_METRICS) and (
                self.statement != "cash_flow"
                or self.fact.metric not in NONFINANCIAL_CASH_FLOW_METRICS
                or self.sector_profile != "nonfinancial"
                or self.fact.period_start != date(self.fact.period_end.year, 1, 1)
                or (self.fact.period_end.month, self.fact.period_end.day)
                not in {(3, 31), (6, 30), (9, 30), (12, 31)}
            ):
                raise ValueError("operating cash flow requires nonfinancial calendar-YTD semantics")
        if (self.status is FinancialBindingStatus.SOURCE_BOUND
                and self.source_column != "group_current_period" and (
                    self.filing_period_end is None or self.filing_period_end <= self.fact.period_end
                    or self.comparability != "as_presented_same_filing"
                    or self.issuer_revision_status != "unverified")):
            raise ValueError("comparative observation requires explicit filing-edition semantics")


@dataclass(frozen=True, slots=True)
class FinancialInputSnapshot:
    symbol: str
    market: Market
    as_of: datetime
    requested_metrics: tuple[str, ...]
    sector_profile: str
    reporting_scope: str
    inspections: tuple[FinancialFactInspection, ...]
    model_version: str = FINANCIAL_INPUTS_VERSION

    def __post_init__(self) -> None:
        require_timezone(self.as_of, "financial snapshot as_of")
        cutoff = self.as_of.astimezone(UTC)
        if (
            not self.symbol or type(self.requested_metrics) is not tuple
            or not 1 <= len(self.requested_metrics) <= 20
            or tuple(sorted(set(self.requested_metrics))) != self.requested_metrics
            or any(not item.strip() for item in self.requested_metrics)
            or type(self.inspections) is not tuple
            or self.sector_profile not in {"bank", "nonfinancial", "unknown"}
            or self.reporting_scope != "group" or self.model_version != FINANCIAL_INPUTS_VERSION
        ):
            raise ValueError("unsupported financial snapshot contract")
        for entry in self.inspections:
            entry.__post_init__()
            fact = entry.fact
            fact.__post_init__()
            fact.instrument.__post_init__()
            if (
                (fact.instrument.symbol, fact.instrument.market, fact.instrument.asset_type)
                != (self.symbol, self.market, AssetType.EQUITY)
                or fact.metric not in self.requested_metrics or not fact.value.is_finite()
                or fact.available_at.astimezone(UTC) > cutoff
                or fact.published_at.astimezone(UTC) > cutoff
                or fact.available_at.astimezone(UTC) < fact.published_at.astimezone(UTC)
                or fact.period_end > cutoff.date()
                or (entry.filing_period_end is not None
                    and entry.filing_period_end > cutoff.date())
                or (fact.instrument.available_at is not None
                    and fact.instrument.available_at.astimezone(UTC) > cutoff)
                or (entry.status is FinancialBindingStatus.SOURCE_BOUND
                    and (entry.reporting_scope != self.reporting_scope
                         or entry.sector_profile != self.sector_profile))
            ):
                raise ValueError("financial snapshot subject/time/semantics mismatch")

    @property
    def missing_metrics(self) -> tuple[str, ...]:
        present = {entry.fact.metric for entry in self.inspections}
        return tuple(metric for metric in self.requested_metrics if metric not in present)

    @property
    def source_binding_complete(self) -> bool:
        return bool(self.inspections) and not self.missing_metrics and all(
            entry.status is FinancialBindingStatus.SOURCE_BOUND for entry in self.inspections
        )

    @property
    def input_hash(self) -> str:
        self.__post_init__()
        return sha256(financial_input_json(asdict(self)).encode()).hexdigest()

    def validate_context(self, facts: tuple[FundamentalFact, ...], *, symbol: str,
                         market: Market, as_of: datetime) -> None:
        self.__post_init__()
        require_timezone(as_of, "financial context as_of")
        if ((symbol, market) != (self.symbol, self.market)
                or as_of.astimezone(UTC) != self.as_of.astimezone(UTC)) or sorted(
            financial_input_json(asdict(fact)) for fact in facts
        ) != sorted(financial_input_json(asdict(entry.fact)) for entry in self.inspections):
            raise ValueError("research financial snapshot does not match its consumed facts/cutoff")

    def document(self) -> dict[str, object]:
        return {
            **asdict(self), "input_hash": self.input_hash,
            "missing_metrics": self.missing_metrics,
            "source_binding_complete": self.source_binding_complete,
            "investment_scoring_authorized": False, "historical_replay_eligible": False,
            "validation_authorized": False,
            "limitations": (
                "Source binding checks stored consistency, not independent PDF annotation truth.",
                "Manual LOW/UNKNOWN retrieval-time facts have no approved scoring policy.",
                "Requested-metric coverage is not full financial or historical completeness.",
                "A bank profile does not inherit a generic-company ROIC/cash-flow/debt score; "
                "the requested gap list is not an approved sector research checklist.",
            ),
        }
