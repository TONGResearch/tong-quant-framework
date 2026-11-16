"""China-A group nonfinancial input checklist, never a scoring or source admission."""

from dataclasses import asdict, dataclass
from datetime import UTC, date
from hashlib import sha256
from typing import Any
from zoneinfo import ZoneInfo

from tong_quant.data.financial_inputs import (
    FinancialBindingStatus,
    FinancialInputSnapshot,
    financial_input_json,
)
from tong_quant.domain.enums import Market
from tong_quant.version import NONFINANCIAL_INPUT_POLICY_VERSION


@dataclass(frozen=True, slots=True)
class _Requirement:
    metric: str
    dimension: str
    statement: str
    period_kind: str
    unit: str = "absolute"
    currency: str | None = "CNY"
    measurement_basis: str | None = None


_REQUIREMENTS = (
    _Requirement("revenue", "growth", "income", "ytd"),
    _Requirement("profit_attributable_to_parent", "growth", "income", "ytd"),
    _Requirement("roe_weighted_ytd_unannualized", "profitability",
                 "nonfinancial_profitability", "ytd", "percent", None, "ytd_unannualized_ratio"),
    _Requirement("total_assets", "survival", "balance", "point"),
    _Requirement("total_liabilities", "survival", "balance", "point"),
    _Requirement("current_liabilities", "survival", "balance", "point"),
    _Requirement("monetary_funds", "survival", "balance", "point"),
    _Requirement("operating_cash_flow", "cash_quality", "cash_flow", "ytd"),
    _Requirement("operating_cash_inflow", "cash_quality", "cash_flow", "ytd"),
    _Requirement("operating_cash_outflow", "cash_quality", "cash_flow", "ytd"),
    _Requirement("equity_attributable_to_parent", "valuation_basis", "balance", "point"),
)
_UNDEFINED_METRICS = ("roic", "interest_bearing_debt")


@dataclass(frozen=True, slots=True)
class NonfinancialInputPolicy:
    maximum_report_age_days: int = 0
    model_version: str = NONFINANCIAL_INPUT_POLICY_VERSION

    def __post_init__(self) -> None:
        if (type(self.maximum_report_age_days) is not int or self.maximum_report_age_days < 0
                or self.model_version != NONFINANCIAL_INPUT_POLICY_VERSION):
            raise ValueError("nonfinancial input policy requires age >= 0 and pinned version")

    @property
    def policy_hash(self) -> str:
        self.__post_init__()
        return sha256(financial_input_json({
            **asdict(self), "requirements": tuple(asdict(item) for item in _REQUIREMENTS),
            "undefined_metrics": _UNDEFINED_METRICS, "calendar_timezone": "Asia/Shanghai",
        }).encode()).hexdigest()


def assess_nonfinancial_inputs(
    snapshot: FinancialInputSnapshot, policy: NonfinancialInputPolicy, *,
    target_period_end: date | None = None,
) -> dict[str, Any]:
    snapshot.__post_init__()
    policy.__post_init__()
    if (snapshot.market is not Market.CHINA_A or snapshot.sector_profile != "nonfinancial"
            or snapshot.reporting_scope != "group"):
        raise ValueError("nonfinancial input policy requires China-A group nonfinancial inputs")
    cutoff = snapshot.as_of.astimezone(UTC)
    decision_date = cutoff.astimezone(ZoneInfo("Asia/Shanghai")).date()
    if target_period_end is not None and (
        type(target_period_end) is not date or target_period_end > decision_date
        or (target_period_end.month, target_period_end.day)
        not in {(3, 31), (6, 30), (9, 30), (12, 31)}
    ):
        raise ValueError("nonfinancial target period requires a visible calendar-quarter end")
    basis = "explicit" if target_period_end is not None else "latest_visible_required_metric"
    if target_period_end is None:
        names = {item.metric for item in _REQUIREMENTS}
        target_period_end = max((entry.fact.period_end for entry in snapshot.inspections
                                 if entry.fact.metric in names), default=None)
    checks: list[dict[str, Any]] = []
    for requirement in _REQUIREMENTS:
        entries = [entry for entry in snapshot.inspections
                   if entry.fact.metric == requirement.metric]
        check: dict[str, Any] = {
            "metric": requirement.metric, "dimension": requirement.dimension,
            "requested": requirement.metric in snapshot.requested_metrics,
            "status": "missing" if requirement.metric in snapshot.requested_metrics
            else "not_requested", "reason": "No queried observation; absence is not approval",
            "freshness": "unassessed", "period_end": None, "report_age_days": None,
            "latest_available_age_seconds": None, "trust_level": None,
            "availability_precision": None, "observation_hashes": (),
        }
        if entries:
            key = max((e.fact.period_end, e.fact.available_at.astimezone(UTC), e.fact.revision)
                      for e in entries)
            latest = [e for e in entries if (
                e.fact.period_end, e.fact.available_at.astimezone(UTC), e.fact.revision) == key]
            age = (decision_date - key[0]).days
            check.update(
                status="ambiguous", reason="Latest observation is ambiguous; no fallback",
                period_end=key[0], report_age_days=age,
                latest_available_age_seconds=(cutoff - key[1]).total_seconds(),
                freshness=("unassessed" if policy.maximum_report_age_days == 0 else
                           "stale" if age > policy.maximum_report_age_days
                           else "within_configured_limit"),
                observation_hashes=tuple(sorted(
                    sha256(financial_input_json(asdict(e)).encode()).hexdigest() for e in latest)))
            if len(latest) == 1:
                entry, fact = latest[0], latest[0].fact
                status, reason = ("observed_unqualified",
                                  "Source-bound input only; scoring not admitted")
                if entry.status is not FinancialBindingStatus.SOURCE_BOUND:
                    status = ("rejected" if entry.status is FinancialBindingStatus.REJECTED
                              else "unsupported")
                    reason = "Latest source binding rejected/unsupported; no favorable fallback"
                elif (fact.unit != requirement.unit or fact.currency != requirement.currency
                      or entry.statement != requirement.statement
                      or entry.measurement_basis != requirement.measurement_basis
                      or entry.source_column != "group_current_period"
                      or entry.filing_period_end != fact.period_end
                      or entry.comparability is not None or entry.issuer_revision_status is not None
                      or (fact.period_end.month, fact.period_end.day)
                      not in {(3, 31), (6, 30), (9, 30), (12, 31)}
                      or fact.period_start != (date(fact.period_end.year, 1, 1)
                          if requirement.period_kind == "ytd" else None)):
                    status, reason = ("semantic_mismatch",
                                      "Unit/scope/column/period definition mismatch")
                elif fact.period_end != target_period_end:
                    status, reason = "period_mismatch", "Observation differs from target period"
                check.update(status=status, reason=reason, trust_level=fact.trust_level.value,
                             availability_precision=fact.availability_precision.value)
        checks.append(check)
    document = {
        "symbol": snapshot.symbol, "market": snapshot.market.value, "as_of": cutoff,
        "input_hash": snapshot.input_hash, "policy_hash": policy.policy_hash,
        "model_version": NONFINANCIAL_INPUT_POLICY_VERSION,
        "target_period_end": target_period_end, "target_period_basis": basis,
        "checks": checks,
        "unimplemented_definitions": [{
            "metric": name, "requested": name in snapshot.requested_metrics,
            "status": "definition_not_implemented",
            "reason": "No admitted source/measurement definition; do not substitute other metrics",
        } for name in _UNDEFINED_METRICS],
        "source_qualification": "NOT_ESTABLISHED", "financial_scoring_policy": "NOT_ADMITTED",
        "investment_scoring_authorized": False, "validation_authorized": False,
        "historical_replay_eligible": False, "execution_authorized": False,
        "limitations": (
            "Selected input checklist, not complete nonfinancial company/industry research.",
            "Observed counts, period alignment and freshness are not source or scoring approval.",
            "Available age is time since this observation became available, not source capture "
            "age, accounting-period freshness or original issuer publication precision.",
            "Latest visible period does not establish the latest issuer filing/revision history.",
            "Total liabilities are not interest-bearing debt; ROE is not ROIC or annualized here.",
            "Cycle, recurring cash quality, dated valuation/actions and independent source/sector "
            "qualification require separate research; no derived solvency or investment score.",
            "An explicit nonfinancial profile cannot qualify bank/broker/insurer sector semantics.",
        ),
    }
    identity = sha256(financial_input_json(document).encode()).hexdigest()
    return {**document, "assessment_hash": identity}
