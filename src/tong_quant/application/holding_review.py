"""Read-only owner annotations and post-observation checks, never position management."""

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation, localcontext
from hashlib import sha256
from typing import Any

from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.global_price_inputs import GlobalPriceInputs
from tong_quant.data.providers.yahoo_identity import validate_yahoo_equity_subject
from tong_quant.domain.enums import AssetType, Market
from tong_quant.domain.models import require_timezone
from tong_quant.research.bar_inputs import checked_daily_bars
from tong_quant.research.technical.diagnostics import technical_diagnostics
from tong_quant.research.technical.indicators import TechnicalParameters
from tong_quant.version import HOLDING_REVIEW_VERSION

_FIELDS = {"symbol", "market", "currency", "quantity", "reported_average_cost",
           "observed_at", "recorded_at", "investment_intent", "loss_review_percent",
           "maximum_context_age_seconds", "maximum_price_age_seconds"}
_CURRENCIES = {Market.US: "USD", Market.HONG_KONG: "HKD", Market.MALAYSIA: "MYR"}


def _number(value: object) -> Decimal:
    if not isinstance(value, str) or not value or len(value) > 40:
        raise ValueError("holding amounts must be bounded decimal strings")
    try:
        number = Decimal(value)
    except InvalidOperation:
        raise ValueError("invalid holding amount") from None
    exponent = number.as_tuple().exponent
    if (not number.is_finite() or not Decimal("0") < number < Decimal("1e12")
            or not isinstance(exponent, int) or abs(exponent) > 12):
        raise ValueError("holding amount outside supported bounds")
    return number


@dataclass(frozen=True, slots=True)
class HoldingReviewContext:
    symbol: str
    market: Market
    currency: str
    quantity: str
    reported_average_cost: str
    observed_at: datetime
    recorded_at: datetime
    investment_intent: str
    loss_review_percent: str
    maximum_context_age_seconds: int
    maximum_price_age_seconds: int

    def __post_init__(self) -> None:
        if self.market not in _CURRENCIES or self.currency != _CURRENCIES[self.market]:
            raise ValueError("holding review requires explicit supported quote currency")
        validate_yahoo_equity_subject(self.market, self.symbol)
        require_timezone(self.observed_at, "holding observation")
        require_timezone(self.recorded_at, "holding recording")
        if self.recorded_at.astimezone(UTC) < self.observed_at.astimezone(UTC):
            raise ValueError("holding recording cannot precede its observation")
        for value in (self.quantity, self.reported_average_cost, self.loss_review_percent):
            _number(value)
        if _number(self.loss_review_percent) > 100:
            raise ValueError("loss review percent cannot exceed 100")
        if self.investment_intent not in {"long_term", "medium_term", "short_term"}:
            raise ValueError("unsupported owner investment intent")
        for age in (self.maximum_context_age_seconds, self.maximum_price_age_seconds):
            if type(age) is not int or not 0 < age <= 366 * 86400:
                raise ValueError("holding review age limits must be explicit positive seconds")

    def document(self) -> dict[str, Any]:
        return {**asdict(self), "market": self.market.value,
                "observed_at": self.observed_at.astimezone(UTC).isoformat(),
                "recorded_at": self.recorded_at.astimezone(UTC).isoformat(),
                "provenance": "OWNER_REPORTED_UNVERIFIED",
                "cost_includes_fees": "UNKNOWN", "borrowed_funds_status": "UNKNOWN"}


def parse_holding_context(document: dict[str, Any]) -> HoldingReviewContext:
    reject_sensitive_structure(document)
    if set(document) != {"holding"} or not isinstance(document["holding"], dict):
        raise ValueError("holding context requires exactly one holding table")
    values = document["holding"]
    if set(values) != _FIELDS:
        raise ValueError("holding context has missing or unsupported fields")
    try:
        return HoldingReviewContext(**{**values, "market": Market(values["market"]),
            "observed_at": datetime.fromisoformat(values["observed_at"]),
            "recorded_at": datetime.fromisoformat(values["recorded_at"])})
    except (ValueError, TypeError, AttributeError, KeyError):
        raise ValueError("invalid holding context; verify identity, amounts, time and limits"
                         ) from None


def build_holding_review(
    context: HoldingReviewContext, snapshot: GlobalPriceInputs, parameters: TechnicalParameters,
) -> dict[str, Any]:
    """Only explicit owner-input loss alerts; no inferred horizon, action or allocation."""
    context.__post_init__()
    require_timezone(snapshot.as_of, "holding review cutoff")
    cutoff = snapshot.as_of.astimezone(UTC)
    observed = context.observed_at.astimezone(UTC)
    if observed > cutoff:
        raise ValueError("holding observation is later than the analysis cutoff")
    if context.recorded_at.astimezone(UTC) > cutoff:
        raise ValueError("holding recording is later than the analysis cutoff")
    if context.symbol != snapshot.subject or context.market != snapshot.market:
        raise ValueError("holding context and retained price identity mismatch")
    bars = checked_daily_bars(snapshot.bars, as_of=cutoff, require_latest_active=True)
    if any((bar.instrument.symbol, bar.instrument.market, bar.instrument.currency,
            bar.instrument.asset_type) != (context.symbol, context.market, context.currency,
                                           AssetType.EQUITY) for bar in snapshot.bars):
        raise ValueError("holding context and original bar identity/currency mismatch")
    technical = technical_diagnostics(snapshot.bars, parameters, as_of=cutoff)
    context_age = (cutoff - observed).total_seconds()
    latest = bars[-1] if bars else None
    price_age = (None if latest is None else
                 (cutoff - latest.timestamp.astimezone(UTC)).total_seconds())
    blockers = []
    if context_age > context.maximum_context_age_seconds:
        blockers.append("OWNER_CONTEXT_STALE")
    if snapshot.status != "observed_unqualified":
        blockers.append("PRICE_SOURCE_NOT_OBSERVED")
    if latest is None:
        blockers.append("CURRENT_PRICE_MISSING_OR_SUSPENDED")
    else:
        if latest.timestamp.astimezone(UTC) < observed:
            blockers.append("PRICE_PREDATES_HOLDING_OBSERVATION")
        if price_age is not None and price_age > context.maximum_price_age_seconds:
            blockers.append("PRICE_OBSERVATION_STALE")
    change = value = None
    loss_state = "NOT_EVALUATED"
    if not blockers and latest is not None:
        with localcontext() as decimal_context:
            decimal_context.prec = 50
            decimal_context.rounding = ROUND_HALF_EVEN
            cost = _number(context.reported_average_cost)
            change_number = (latest.close / cost - 1) * 100
            change = str(change_number)
            value = str(latest.close * _number(context.quantity))
            remaining_percent = 100 - _number(context.loss_review_percent)
            loss_state = ("REVIEW_REQUIRED" if latest.close * 100 <= cost * remaining_percent
                          else "NOT_REACHED_ON_THIS_OBSERVATION")
    source = snapshot.document()
    output = {
        "model_version": HOLDING_REVIEW_VERSION, "as_of": cutoff.isoformat(),
        "subject": context.symbol, "market": context.market.value,
        "owner_context": context.document(), "owner_context_age_seconds": context_age,
        "source_input_hash": source["input_hash"],
        "technical_input_hash": technical["technical_input_hash"],
        "price_observed_at": (None if latest is None else
                              latest.timestamp.astimezone(UTC).isoformat()),
        "price_age_seconds": price_age, "blockers": blockers,
        "comparison_status": "BLOCKED" if blockers else "OBSERVED_UNQUALIFIED",
        "price_only_change_percent": change, "observed_position_value": value,
        "loss_review_status": loss_state,
        "trend_structure_family": technical["trend_structure_family"],
        "momentum_family": technical["momentum_family"],
        "technical_confluence": technical["technical_confluence"],
        "holding_horizon": "NOT_ESTIMATED", "thesis_invalidation": "NOT_EVALUATED",
        "add_review": "BLOCKED_PENDING_FINANCIAL_VALIDATION_AND_CASH_REVIEW",
        "exit_review": "RESEARCH_REVIEW_ONLY_NO_SELL_INSTRUCTION",
        "financial_review": "NOT_EVALUATED_BY_THIS_CHECK",
        "trust_ceiling": "LOW", "availability_precision": "retrieval_time",
        "research_only": True, "execution_authorized": False,
        "investment_scoring_authorized": False, "financial_scoring_authorized": False,
        "historical_replay_eligible": False, "validation_authorized": False,
        "holding_management_authorized": False,
        "limitations": [
            "Owner observation is not authenticated position, fill, cash or settlement evidence",
            "Owner recording timestamps are declared, not authenticated historical availability",
            "Daily timestamp is not verified close/session time or current executable price",
            "Price-only comparison excludes fees, FX, dividends and position/action continuity",
            "A loss alert is a review request, not an automatic stop or guaranteed maximum loss",
            "Technical weakness is not a sell instruction; strength does not approve adding",
            "No holding duration, fundamental thesis, allocation or validated strategy is inferred",
        ],
    }
    reject_sensitive_structure(output)
    return {**output, "review_hash": sha256(financial_input_json(output).encode()).hexdigest()}
