"""Source-bound cash/balance diagnostics, not financial scores or debt clearance."""

from dataclasses import asdict, dataclass, replace
from datetime import UTC, date, datetime
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
from tong_quant.domain.enums import Market
from tong_quant.version import NONFINANCIAL_DIAGNOSTICS_VERSION

_BALANCE = frozenset({"total_assets", "total_liabilities", "current_liabilities", "monetary_funds"})
_FLOW = frozenset({
    "revenue", "operating_cash_flow", "operating_cash_inflow", "operating_cash_outflow",
})


class NonfinancialDiagnosticStatus(StrEnum):
    DESCRIPTIVE = "descriptive_only"
    UNAVAILABLE = "unavailable"
    INCOMPATIBLE = "incompatible"
    NONPOSITIVE_BASE = "nonpositive_base"
    INCONSISTENT = "inconsistent"


@dataclass(frozen=True, slots=True)
class NonfinancialDiagnostic:
    name: str
    formula: str
    status: NonfinancialDiagnosticStatus
    as_of: datetime
    snapshot_hash: str
    unit: str
    reasons: tuple[str, ...]
    period_end: date | None = None
    value: Decimal | None = None
    evidence_ids: tuple[str, ...] = ()
    trust_levels: tuple[str, ...] = ()
    availability_precisions: tuple[str, ...] = ()
    model_version: str = NONFINANCIAL_DIAGNOSTICS_VERSION

    def document(self) -> dict[str, object]:
        body = asdict(self)
        return {
            **body, "diagnostic_hash": sha256(financial_input_json(body).encode()).hexdigest(),
            "investment_scoring_authorized": False, "validation_authorized": False,
            "historical_replay_eligible": False,
            "limitations": (
                "Descriptive same-filing diagnostics only, not solvency or investment approval.",
                "Total/current liabilities are not interest-bearing debt. Monetary funds are "
                "not proven unrestricted cash, cash equivalents or full debt-service coverage.",
                "Net operating cash flow/revenue is not a profit margin or earnings-conversion "
                "ratio; positive cash flow does not prove recurring cash quality.",
                "Arithmetic consistency does not verify manual source annotations, provider "
                "independence, historical availability, full coverage or freshness.",
            ),
        }


def _current_inputs(
    snapshot: FinancialInputSnapshot, metrics: tuple[str, ...],
) -> tuple[tuple[FinancialFactInspection, ...], NonfinancialDiagnosticStatus, str]:
    entries = []
    missing = []
    incompatible = []
    for metric in metrics:
        if metric not in snapshot.requested_metrics:
            missing.append(f"Input not requested: {metric}")
            continue
        candidates = [entry for entry in snapshot.inspections if entry.fact.metric == metric]
        if not candidates:
            missing.append(f"Input missing: {metric}")
            continue
        key = max((entry.fact.period_end, entry.fact.available_at.astimezone(UTC),
                   entry.fact.revision)
                  for entry in candidates)
        latest = [entry for entry in candidates if (
            entry.fact.period_end, entry.fact.available_at.astimezone(UTC),
            entry.fact.revision) == key]
        # A rejected or ambiguous latest input must not select an older favorable row.
        if len(latest) != 1:
            incompatible.append(f"Ambiguous latest input: {metric}")
            continue
        entry = latest[0]
        fact = entry.fact
        expected_statement = "balance" if metric in _BALANCE else "income" if (
            metric == "revenue") else "cash_flow"
        if (
            entry.status is not FinancialBindingStatus.SOURCE_BOUND
            or entry.source_column != "group_current_period"
            or entry.reporting_scope != "group" or entry.sector_profile != "nonfinancial"
            or entry.filing_period_end != fact.period_end
            or entry.comparability is not None or entry.issuer_revision_status is not None
            or entry.statement != expected_statement or metric not in (_BALANCE | _FLOW)
            or entry.source_unit not in CNY_FILING_UNIT_MULTIPLIERS
            or fact.unit != "absolute" or fact.currency != "CNY"
            or entry.measurement_basis is not None
            or (fact.period_end.month, fact.period_end.day)
            not in {(3, 31), (6, 30), (9, 30), (12, 31)}
            or fact.period_start != (None if metric in _BALANCE
                                     else date(fact.period_end.year, 1, 1))
            or (metric != "operating_cash_flow" and fact.value < 0)
            or len(fact.value.as_tuple().digits) > 256
            or abs(int(fact.value.as_tuple().exponent)) > 200
        ):
            incompatible.append(
                f"Latest input rejected, unsupported or semantically incompatible: {metric}")
            continue
        entries.append(entry)
    if incompatible:
        return (), NonfinancialDiagnosticStatus.INCOMPATIBLE, "; ".join((*incompatible, *missing))
    if missing:
        return (), NonfinancialDiagnosticStatus.UNAVAILABLE, "; ".join(missing)
    first = entries[0]
    if any((entry.fact.period_end, entry.filing_artifact_id, entry.filing_sha256,
            entry.audit_status) != (
                first.fact.period_end, first.filing_artifact_id, first.filing_sha256,
                first.audit_status) for entry in entries):
        return (), NonfinancialDiagnosticStatus.INCOMPATIBLE, "Different filing editions/periods"
    return tuple(entries), NonfinancialDiagnosticStatus.DESCRIPTIVE, (
        "Same-filing source-bound observations; no independent qualification")


def nonfinancial_diagnostics(
    snapshot: FinancialInputSnapshot,
) -> tuple[NonfinancialDiagnostic, ...]:
    snapshot.__post_init__()
    if (snapshot.market is not Market.CHINA_A or snapshot.sector_profile != "nonfinancial"
            or snapshot.reporting_scope != "group"):
        raise ValueError("cash/balance diagnostics require China-A group nonfinancial inputs")
    definitions = (
        ("liabilities_to_assets_percent", ("total_liabilities", "total_assets"),
         "total_liabilities / total_assets * 100", "percent"),
        ("monetary_funds_to_current_liabilities_percent",
         ("monetary_funds", "current_liabilities"),
         "monetary_funds / current_liabilities * 100", "percent"),
        ("operating_cash_flow_to_revenue_percent", ("operating_cash_flow", "revenue"),
         "operating_cash_flow / revenue * 100", "percent"),
        ("operating_cash_reconciliation_residual",
         ("operating_cash_inflow", "operating_cash_outflow", "operating_cash_flow"),
         "operating_cash_inflow - operating_cash_outflow - operating_cash_flow", "CNY"),
    )
    results = []
    for name, metrics, formula, unit in definitions:
        entries, status, reason = _current_inputs(snapshot, metrics)
        result = NonfinancialDiagnostic(name, formula, status, snapshot.as_of,
                                        snapshot.input_hash, unit, (reason,))
        if not entries:
            results.append(result)
            continue
        result = replace(
            result, period_end=entries[0].fact.period_end,
            evidence_ids=tuple(entry.evidence_id for entry in entries if entry.evidence_id),
            trust_levels=tuple(sorted({entry.fact.trust_level.value for entry in entries})),
            availability_precisions=tuple(sorted({entry.fact.availability_precision.value
                                                  for entry in entries})),
        )
        values = tuple(entry.fact.value for entry in entries)
        try:
            with localcontext() as context:
                context.prec = 400
                if unit == "CNY":
                    residual = values[0] - values[1] - values[2]
                    result = replace(
                        result, value=residual,
                        status=(NonfinancialDiagnosticStatus.DESCRIPTIVE if residual == 0
                                else NonfinancialDiagnosticStatus.INCONSISTENT),
                        reasons=(*result.reasons, "Exact residual; zero is arithmetic agreement "
                                 "only, not independently verified cash-flow quality"),
                    )
                elif values[1] <= 0:
                    result = replace(
                        result, status=NonfinancialDiagnosticStatus.NONPOSITIVE_BASE,
                        reasons=(*result.reasons, "Nonpositive denominator; ratio withheld"),
                    )
                else:
                    result = replace(result, value=(values[0] / values[1] * 100).quantize(
                        Decimal("0.0001"), rounding=ROUND_HALF_EVEN))
        except ArithmeticError:
            result = replace(
                result, status=NonfinancialDiagnosticStatus.INCOMPATIBLE, value=None,
                reasons=(*result.reasons, "Numeric calculation exceeds supported bounds"),
            )
        results.append(result)
    reconciliation = results[-1]
    cash_ratio = results[2]
    if reconciliation.status in {
        NonfinancialDiagnosticStatus.INCONSISTENT, NonfinancialDiagnosticStatus.INCOMPATIBLE,
    }:
        results[2] = replace(
            cash_ratio, status=reconciliation.status, value=None,
            reasons=(*cash_ratio.reasons,
                     "Cash-flow component check is not reliable; ratio withheld"),
        )
    else:
        results[2] = replace(cash_ratio, reasons=(
            *cash_ratio.reasons, f"Cash-flow component check: {reconciliation.status.value}; "
            "this descriptive ratio is not cash-quality approval",
        ))
    return tuple(results)
