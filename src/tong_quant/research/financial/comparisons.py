"""Same-filing descriptive changes, never growth scores or trading decisions."""

from dataclasses import asdict, dataclass, replace
from datetime import date, datetime
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from enum import StrEnum
from hashlib import sha256

from tong_quant.data.financial_inputs import (
    CNY_FILING_UNIT_MULTIPLIERS,
    FinancialBindingStatus,
    FinancialFactInspection,
    FinancialInputSnapshot,
    financial_input_json,
)
from tong_quant.version import FINANCIAL_COMPARISON_VERSION


class FinancialComparisonStatus(StrEnum):
    DESCRIPTIVE = "descriptive_only"
    UNAVAILABLE = "unavailable"
    INCOMPATIBLE = "incompatible"
    NONPOSITIVE_BASE = "nonpositive_base"


@dataclass(frozen=True, slots=True)
class FinancialComparison:
    metric: str
    kind: str
    status: FinancialComparisonStatus
    as_of: datetime
    snapshot_hash: str
    reasons: tuple[str, ...]
    current_period_end: date | None = None
    prior_period_end: date | None = None
    current_value: Decimal | None = None
    prior_value: Decimal | None = None
    amount_change: Decimal | None = None
    change_percent: Decimal | None = None
    evidence_ids: tuple[str, ...] = ()
    model_version: str = FINANCIAL_COMPARISON_VERSION

    def document(self) -> dict[str, object]:
        document = asdict(self)
        return {
            **document,
            "comparison_hash": sha256(financial_input_json(document).encode()).hexdigest(),
            "investment_scoring_authorized": False, "historical_replay_eligible": False,
            "validation_authorized": False,
            "limitations": (
                "Descriptive CNY amount change, not an investment score or return.",
                "Same-filing presentation does not independently prove accounting comparability "
                "or original historical numeric revisions; source trust is not upgraded.",
                "Calendar-year YTD and prior-year-end comparisons only; other fiscal calendars "
                "and standalone-quarter growth are unsupported.",
            ),
        }


def _compatible(current: FinancialFactInspection, prior: FinancialFactInspection,
                *, kind: str) -> bool:
    left, right = current.fact, prior.fact
    if (
        current.status is not FinancialBindingStatus.SOURCE_BOUND
        or prior.status is not FinancialBindingStatus.SOURCE_BOUND
        or current.source_column != "group_current_period"
        or current.filing_sha256 != prior.filing_sha256
        or current.filing_artifact_id != prior.filing_artifact_id
        or (current.filing_period_end or left.period_end) != left.period_end
        or prior.filing_period_end != left.period_end
        or prior.comparability != "as_presented_same_filing"
        or prior.issuer_revision_status != "unverified"
        or current.reporting_scope != prior.reporting_scope or current.reporting_scope != "group"
        or current.sector_profile != prior.sector_profile
        or current.source_unit not in CNY_FILING_UNIT_MULTIPLIERS
        or prior.source_unit not in CNY_FILING_UNIT_MULTIPLIERS
        or left.unit != right.unit or left.unit != "absolute"
        or left.currency != right.currency or left.currency != "CNY"
        or left.metric != right.metric
        or (left.instrument.symbol, left.instrument.market, left.instrument.asset_type)
        != (right.instrument.symbol, right.instrument.market, right.instrument.asset_type)
    ):
        return False
    if kind == "yoy_ytd":
        return (
            current.statement == prior.statement and current.statement in {"income", "cash_flow"}
            and prior.source_column == "group_prior_year_period"
            and left.period_start == date(left.period_end.year, 1, 1)
            and right.period_start == date(left.period_end.year - 1, 1, 1)
            and (right.period_end.year, right.period_end.month, right.period_end.day)
            == (left.period_end.year - 1, left.period_end.month, left.period_end.day)
        )
    return (
        kind == "since_prior_year_end" and current.statement == prior.statement == "balance"
        and prior.source_column == "group_prior_year_end"
        and left.period_start is None and right.period_start is None
        and right.period_end == date(left.period_end.year - 1, 12, 31)
    )


def financial_comparisons(snapshot: FinancialInputSnapshot) -> tuple[FinancialComparison, ...]:
    snapshot.__post_init__()
    results = []
    for metric in snapshot.requested_metrics:
        kind = {"revenue": "yoy_ytd", "profit_attributable_to_parent": "yoy_ytd",
                "operating_cash_flow": "yoy_ytd",
                "total_assets": "since_prior_year_end"}.get(metric, "unsupported_metric")
        common = FinancialComparison(metric, kind, FinancialComparisonStatus.UNAVAILABLE,
                                     snapshot.as_of, snapshot.input_hash, ())
        entries = [entry for entry in snapshot.inspections if entry.fact.metric == metric]
        if not entries or kind == "unsupported_metric":
            results.append(replace(
                common, status=FinancialComparisonStatus.UNAVAILABLE,
                reasons=("Current input missing or this descriptive metric is unsupported",),
            ))
            continue
        latest_period = max(entry.fact.period_end for entry in entries)
        # Do not fall back to an older valid observation when the latest is rejected.
        current_rows = [entry for entry in entries if entry.fact.period_end == latest_period]
        if len(current_rows) != 1:
            results.append(replace(
                common, status=FinancialComparisonStatus.INCOMPATIBLE,
                reasons=("Ambiguous current observation",),
            ))
            continue
        current = current_rows[0]
        if (current.source_column != "group_current_period"
                or current.status is not FinancialBindingStatus.SOURCE_BOUND
                or latest_period.year < 2
                or (latest_period.month, latest_period.day) not in {
                    (3, 31), (6, 30), (9, 30), (12, 31),
                }):
            results.append(replace(
                common, status=FinancialComparisonStatus.INCOMPATIBLE,
                reasons=("Latest observation is not a source-bound current column",),
            ))
            continue
        prior_date = (date(latest_period.year - 1, 12, 31) if kind == "since_prior_year_end"
                      else date(latest_period.year - 1, latest_period.month, latest_period.day))
        prior_rows = [entry for entry in entries if entry.fact.period_end == prior_date]
        if len(prior_rows) != 1 or not _compatible(current, prior_rows[0], kind=kind):
            results.append(replace(
                common, status=(FinancialComparisonStatus.UNAVAILABLE if not prior_rows
                                  else FinancialComparisonStatus.INCOMPATIBLE),
                reasons=("Exact source-bound same-filing comparative missing or incompatible",),
                current_period_end=latest_period, prior_period_end=prior_date,
            ))
            continue
        prior = prior_rows[0]
        try:
            with localcontext() as context:
                context.prec = 400
                change = current.fact.value - prior.fact.value
                percentage = ((change / prior.fact.value * 100).quantize(
                    Decimal("0.0001"), rounding=ROUND_HALF_EVEN,
                ) if prior.fact.value > 0 else None)
        except ArithmeticError:
            results.append(replace(
                common, status=FinancialComparisonStatus.INCOMPATIBLE,
                reasons=("Numeric change exceeds supported calculation bounds",),
            ))
            continue
        results.append(replace(
            common, status=(FinancialComparisonStatus.DESCRIPTIVE if percentage is not None
                              else FinancialComparisonStatus.NONPOSITIVE_BASE),
            reasons=("Same-filing comparative, as presented; no original-revision claim",
                     "Audit labels may differ; neither label upgrades input trust",
                     *(() if percentage is not None else (
                         "Nonpositive baseline: percentage withheld; signed amount change only",))),
            current_period_end=latest_period, prior_period_end=prior_date,
            current_value=current.fact.value, prior_value=prior.fact.value,
            amount_change=change, change_percent=percentage,
            evidence_ids=tuple(value for value in (current.evidence_id, prior.evidence_id)
                               if value),
        ))
    return tuple(results)
