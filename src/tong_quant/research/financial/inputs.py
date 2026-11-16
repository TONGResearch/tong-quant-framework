"""China-A group-bank input gaps and age diagnostics, never financial scores."""

from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from hashlib import sha256
from zoneinfo import ZoneInfo

from tong_quant.data.financial_inputs import (
    FinancialBindingStatus,
    FinancialFactInspection,
    FinancialInputSnapshot,
    financial_input_json,
)
from tong_quant.domain.enums import Market
from tong_quant.version import BANK_FINANCIAL_INPUT_POLICY_VERSION


@dataclass(frozen=True, slots=True)
class BankInputRequirement:
    dimension: str
    metric: str
    unit: str
    currency: str | None
    statement: str
    measurement_basis: str | None
    period_kind: str


BANK_INPUT_REQUIREMENTS = (
    BankInputRequirement("earnings", "revenue", "absolute", "CNY", "income", None, "ytd"),
    BankInputRequirement("earnings", "profit_attributable_to_parent", "absolute", "CNY",
                         "income", None, "ytd"),
    BankInputRequirement("asset_quality", "nonperforming_loan_ratio", "percent", None,
                         "bank_asset_quality", "period_end_ratio", "point"),
    BankInputRequirement("asset_quality", "provision_coverage_ratio", "percent", None,
                         "bank_asset_quality", "period_end_ratio", "point"),
    BankInputRequirement("profitability", "roe_weighted_ytd_unannualized", "percent", None,
                         "bank_profitability", "ytd_unannualized_ratio", "ytd"),
    BankInputRequirement("profitability", "net_interest_margin_ytd", "percent", None,
                         "bank_profitability", "reported_ytd_margin", "ytd"),
    BankInputRequirement("capital", "core_tier1_capital_ratio", "percent", None,
                         "bank_capital", "period_end_ratio", "point"),
    BankInputRequirement("capital", "capital_adequacy_ratio", "percent", None,
                         "bank_capital", "period_end_ratio", "point"),
    BankInputRequirement("liquidity", "liquidity_coverage_ratio", "percent", None,
                         "bank_liquidity", "period_end_ratio", "point"),
)


class BankInputStatus(StrEnum):
    NOT_REQUESTED = "not_requested"
    MISSING = "missing"
    REJECTED = "rejected"
    UNSUPPORTED = "unsupported"
    AMBIGUOUS = "ambiguous"
    SEMANTIC_MISMATCH = "semantic_mismatch"
    PERIOD_MISMATCH = "period_mismatch"
    OBSERVED_UNQUALIFIED = "observed_unqualified"


class BankInputFreshness(StrEnum):
    UNASSESSED = "unassessed"
    WITHIN_LIMIT = "within_configured_limit"
    STALE = "stale"


@dataclass(frozen=True, slots=True)
class BankInputPolicy:
    maximum_report_age_days: int = 0
    model_version: str = BANK_FINANCIAL_INPUT_POLICY_VERSION

    def __post_init__(self) -> None:
        if (type(self.maximum_report_age_days) is not int or self.maximum_report_age_days < 0
                or self.model_version != BANK_FINANCIAL_INPUT_POLICY_VERSION):
            raise ValueError("bank input policy requires integer age >= 0 and pinned version")

    @property
    def policy_hash(self) -> str:
        self.__post_init__()
        return sha256(financial_input_json({
            **asdict(self), "requirements": tuple(asdict(item) for item in BANK_INPUT_REQUIREMENTS),
            "calendar_timezone": "Asia/Shanghai",
        }).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class BankInputCheck:
    dimension: str
    metric: str
    status: BankInputStatus
    reasons: tuple[str, ...]
    freshness: BankInputFreshness = BankInputFreshness.UNASSESSED
    period_end: date | None = None
    report_age_days: int | None = None
    trust_level: str | None = None
    availability_precision: str | None = None
    observation_hashes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class BankInputAssessment:
    symbol: str
    market: Market
    as_of: datetime
    input_hash: str
    policy_hash: str
    target_period_end: date | None
    target_period_basis: str
    checks: tuple[BankInputCheck, ...]
    model_version: str = BANK_FINANCIAL_INPUT_POLICY_VERSION

    def document(self) -> dict[str, object]:
        body = asdict(self)
        return {
            **body, "assessment_hash": sha256(financial_input_json(body).encode()).hexdigest(),
            "investment_scoring_authorized": False, "validation_authorized": False,
            "historical_replay_eligible": False,
            "limitations": (
                "Input definitions are diagnostic requirements, not an admitted scoring policy.",
                "Source binding and age limits do not authenticate source truth or trust.",
                "Missing canonical metrics do not prove missing issuer disclosure; some source "
                "definitions are intentionally unsupported until separately reviewed.",
                "No complete bank quality, valuation or investment conclusion is produced.",
                "Valuation needs dated price/book/share/action inputs; none are inferred.",
                "Latest-visible period does not prove the latest issuer filing or revisions.",
            ),
        }


def _semantics_match(entry: FinancialFactInspection, requirement: BankInputRequirement) -> bool:
    fact = entry.fact
    return (
        fact.unit == requirement.unit and fact.currency == requirement.currency
        and entry.statement == requirement.statement
        and entry.measurement_basis == requirement.measurement_basis
        and entry.reporting_scope == "group" and entry.sector_profile == "bank"
        and entry.source_column == "group_current_period"
        and entry.filing_period_end == fact.period_end
        and (fact.period_end.month, fact.period_end.day)
        in {(3, 31), (6, 30), (9, 30), (12, 31)}
        and fact.period_start == (
            date(fact.period_end.year, 1, 1) if requirement.period_kind == "ytd" else None)
    )


def assess_bank_inputs(snapshot: FinancialInputSnapshot, policy: BankInputPolicy, *,
                       target_period_end: date | None = None) -> BankInputAssessment:
    snapshot.__post_init__()
    policy.__post_init__()
    if (snapshot.market is not Market.CHINA_A or snapshot.sector_profile != "bank"
            or snapshot.reporting_scope != "group"):
        raise ValueError("bank input policy supports China-A group-bank diagnostics only")
    decision_date = snapshot.as_of.astimezone(ZoneInfo("Asia/Shanghai")).date()
    if target_period_end is not None and (
        type(target_period_end) is not date or target_period_end > decision_date
        or (target_period_end.month, target_period_end.day)
        not in {(3, 31), (6, 30), (9, 30), (12, 31)}
    ):
        raise ValueError("bank target period requires a visible calendar-quarter end")
    basis = "explicit" if target_period_end is not None else "latest_visible_required_metric"
    if target_period_end is None:
        required = {item.metric for item in BANK_INPUT_REQUIREMENTS}
        target_period_end = max((entry.fact.period_end for entry in snapshot.inspections
                                 if entry.fact.metric in required), default=None)
    checks = []
    for requirement in BANK_INPUT_REQUIREMENTS:
        if requirement.metric not in snapshot.requested_metrics:
            checks.append(BankInputCheck(
                requirement.dimension, requirement.metric, BankInputStatus.NOT_REQUESTED,
                ("Policy input was not requested",)))
            continue
        entries = [entry for entry in snapshot.inspections
                   if entry.fact.metric == requirement.metric]
        if not entries:
            checks.append(BankInputCheck(
                requirement.dimension, requirement.metric, BankInputStatus.MISSING,
                ("No canonical observation in the query",)))
            continue
        latest_key = max((entry.fact.period_end, entry.fact.available_at.astimezone(UTC),
                          entry.fact.revision)
                         for entry in entries)
        latest = [entry for entry in entries if (
            entry.fact.period_end, entry.fact.available_at.astimezone(UTC),
            entry.fact.revision) == latest_key]
        hashes = tuple(sorted(sha256(financial_input_json(asdict(entry)).encode()).hexdigest()
                              for entry in latest))
        age = (decision_date - latest_key[0]).days
        freshness = (BankInputFreshness.UNASSESSED if policy.maximum_report_age_days == 0
                     else BankInputFreshness.STALE if age > policy.maximum_report_age_days
                     else BankInputFreshness.WITHIN_LIMIT)
        status, reason = BankInputStatus.AMBIGUOUS, "Latest observation is ambiguous; no fallback"
        trust = precision = None
        if len(latest) == 1:
            entry = latest[0]
            trust, precision = entry.fact.trust_level.value, entry.fact.availability_precision.value
            if entry.status is FinancialBindingStatus.REJECTED:
                status, reason = BankInputStatus.REJECTED, "Latest source binding was rejected"
            elif entry.status is FinancialBindingStatus.UNSUPPORTED:
                status, reason = BankInputStatus.UNSUPPORTED, "Latest source is unsupported"
            elif not _semantics_match(entry, requirement):
                status, reason = BankInputStatus.SEMANTIC_MISMATCH, "Definition/unit mismatch"
            elif entry.fact.period_end != target_period_end:
                status, reason = BankInputStatus.PERIOD_MISMATCH, "Latest input differs from target"
            else:
                status, reason = (BankInputStatus.OBSERVED_UNQUALIFIED,
                                  "Source-bound observation only; scoring is not admitted")
        checks.append(BankInputCheck(
            requirement.dimension, requirement.metric, status, (reason,), freshness=freshness,
            period_end=latest_key[0], report_age_days=age, trust_level=trust,
            availability_precision=precision, observation_hashes=hashes,
        ))
    return BankInputAssessment(snapshot.symbol, snapshot.market, snapshot.as_of,
                               snapshot.input_hash, policy.policy_hash, target_period_end,
                               basis, tuple(checks))
