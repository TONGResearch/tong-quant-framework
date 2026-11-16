"""Inspect reported valuation denominators; never invent a market numerator or TTM."""

from dataclasses import asdict, dataclass, replace
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256

from tong_quant.data.financial_inputs import (
    CNY_FILING_UNIT_MULTIPLIERS,
    FinancialBindingStatus,
    FinancialFactInspection,
    FinancialInputSnapshot,
    financial_input_json,
)
from tong_quant.domain.enums import Market
from tong_quant.version import VALUATION_BASIS_VERSION


class ValuationBasisStatus(StrEnum):
    NOT_REQUESTED = "not_requested"
    MISSING = "missing"
    INCOMPATIBLE = "incompatible"
    PARTIAL_YEAR = "partial_year_not_annual_or_ttm"
    NONPOSITIVE = "nonpositive_denominator"
    OBSERVED = "observed_unqualified"


@dataclass(frozen=True, slots=True)
class ValuationBasisDiagnostic:
    name: str
    metric: str
    status: ValuationBasisStatus
    as_of: datetime
    snapshot_hash: str
    reasons: tuple[str, ...]
    period_start: date | None = None
    period_end: date | None = None
    reported_value: Decimal | None = None
    evidence_id: str | None = None
    trust_level: str | None = None
    availability_precision: str | None = None
    model_version: str = VALUATION_BASIS_VERSION

    def document(self) -> dict[str, object]:
        body = asdict(self)
        return {
            **body, "diagnostic_hash": sha256(financial_input_json(body).encode()).hexdigest(),
            "unit": "CNY", "valuation_multiple": None,
            "market_value_input_status": "source_bound_dated_equity_market_value_not_implemented",
            "investment_scoring_authorized": False, "validation_authorized": False,
            "historical_replay_eligible": False, "execution_authorized": False,
            "limitations": (
                "Reported denominator diagnostics only; no PE/PB/PS, fair value or price target.",
                "No interim annualization or TTM synthesis. Partial-period losses do not "
                "establish full-year or TTM losses. Prior-year comparatives are not a TTM feed.",
                "Parent equity is not total assets, minority-inclusive equity or market value.",
                "Book equity includes intangible assets; no tangible-book adjustment is inferred.",
                "Binding does not establish independent verification, coverage, freshness, "
                "historical availability or a qualified valuation/scoring policy.",
            ),
        }


def _compatible(entry: FinancialFactInspection, *, balance: bool) -> bool:
    fact = entry.fact
    return (
        entry.status is FinancialBindingStatus.SOURCE_BOUND
        and entry.source_column == "group_current_period"
        and entry.reporting_scope == "group" and entry.sector_profile == "nonfinancial"
        and entry.filing_period_end == fact.period_end
        and entry.comparability is None and entry.issuer_revision_status is None
        and entry.statement == ("balance" if balance else "income")
        and entry.source_unit in CNY_FILING_UNIT_MULTIPLIERS
        and fact.unit == "absolute" and fact.currency == "CNY"
        and entry.measurement_basis is None
        and (fact.period_end.month, fact.period_end.day) in {(3, 31), (6, 30), (9, 30), (12, 31)}
        and fact.period_start == (None if balance else date(fact.period_end.year, 1, 1))
    )


def valuation_basis_diagnostics(
    snapshot: FinancialInputSnapshot,
) -> tuple[ValuationBasisDiagnostic, ...]:
    snapshot.__post_init__()
    cutoff = snapshot.as_of.astimezone(UTC)
    if any(entry.fact.available_at.astimezone(UTC) > cutoff
           or entry.fact.published_at.astimezone(UTC) > cutoff
           for entry in snapshot.inspections):
        raise ValueError("valuation inputs must not follow the actual UTC cutoff")
    if (snapshot.market is not Market.CHINA_A or snapshot.sector_profile != "nonfinancial"
            or snapshot.reporting_scope != "group"):
        raise ValueError("valuation basis diagnostics require China-A group nonfinancial inputs")
    results = []
    for name, metric, balance in (
        ("annual_earnings_basis", "profit_attributable_to_parent", False),
        ("parent_book_basis", "equity_attributable_to_parent", True),
        ("annual_revenue_basis", "revenue", False),
    ):
        diagnostic = ValuationBasisDiagnostic(
            name, metric, ValuationBasisStatus.NOT_REQUESTED, snapshot.as_of,
            snapshot.input_hash, (f"Input not requested: {metric}",),
        )
        entries = [entry for entry in snapshot.inspections if entry.fact.metric == metric]
        if metric not in snapshot.requested_metrics:
            results.append(diagnostic)
            continue
        if not entries:
            results.append(replace(diagnostic, status=ValuationBasisStatus.MISSING,
                                   reasons=(f"Input missing: {metric}",)))
            continue
        # Rejected/unsupported latest rows and ties cannot fall back to favorable old data.
        key = max((e.fact.period_end, e.fact.available_at.astimezone(UTC), e.fact.revision)
                  for e in entries)
        latest = [e for e in entries if (
            e.fact.period_end, e.fact.available_at.astimezone(UTC), e.fact.revision) == key]
        if len(latest) != 1 or not _compatible(latest[0], balance=balance):
            results.append(replace(
                diagnostic, status=ValuationBasisStatus.INCOMPATIBLE,
                reasons=("Ambiguous, rejected, unsupported or incompatible latest input",),
            ))
            continue
        entry = latest[0]
        fact = entry.fact
        if not balance and (fact.period_end.month, fact.period_end.day) != (12, 31):
            status = ValuationBasisStatus.PARTIAL_YEAR
            reason = "Interim calendar-YTD amount retained; no annualization or TTM inference"
        elif fact.value <= 0:
            status = ValuationBasisStatus.NONPOSITIVE
            reason = "Nonpositive reported denominator; no meaningful positive multiple inferred"
        else:
            status = ValuationBasisStatus.OBSERVED
            reason = "Reported denominator only, not valuation-qualified or freshness-qualified"
        results.append(replace(
            diagnostic, status=status, reasons=(reason,), period_start=fact.period_start,
            period_end=fact.period_end, reported_value=fact.value, evidence_id=entry.evidence_id,
            trust_level=fact.trust_level.value,
            availability_precision=fact.availability_precision.value,
        ))
    return tuple(results)
