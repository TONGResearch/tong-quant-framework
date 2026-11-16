"""Market-value input matching only; no multiple until source/sector admission exists."""

from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, localcontext
from hashlib import sha256
from zoneinfo import ZoneInfo

from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.market_value_inputs import MarketValueInputSnapshot
from tong_quant.data.price_evidence import daily_bar_content
from tong_quant.domain.enums import AssetType, Market
from tong_quant.domain.models import Bar
from tong_quant.research.bar_inputs import checked_daily_bars
from tong_quant.version import MARKET_VALUE_DIAGNOSTICS_VERSION, MARKET_VALUE_POLICY_VERSION


@dataclass(frozen=True, slots=True)
class MarketValueMatchingPolicy:
    max_quote_age_seconds: int | None = None
    max_capture_age_seconds: int | None = None
    max_bar_age_seconds: int | None = None
    model_version: str = MARKET_VALUE_POLICY_VERSION

    def __post_init__(self) -> None:
        if self.model_version != MARKET_VALUE_POLICY_VERSION or any(
            value is not None and (type(value) is not int or value <= 0)
            for value in (self.max_quote_age_seconds, self.max_capture_age_seconds,
                          self.max_bar_age_seconds)
        ):
            raise ValueError(
                "matching age limits require explicit positive integer seconds or None")

    @property
    def policy_hash(self) -> str:
        self.__post_init__()
        return sha256(financial_input_json(asdict(self)).encode()).hexdigest()


def _microseconds(delta: timedelta) -> int:
    return (delta.days * 86400 + delta.seconds) * 1000000 + delta.microseconds


def _freshness(age: int | None, limit: int | None) -> str:
    if age is None:
        return "UNAVAILABLE"
    if age < 0:
        return "FUTURE"
    if limit is None:
        return "UNASSESSED"
    return "WITHIN_CONFIGURED_LIMIT" if age <= limit * 1000000 else "STALE"


def _checked_bars(snapshot: MarketValueInputSnapshot, bars: tuple[Bar, ...]) -> tuple[Bar, ...]:
    cutoff = snapshot.as_of.astimezone(UTC)
    if any((bar.instrument.symbol, bar.instrument.market, bar.instrument.asset_type) != (
        snapshot.symbol, snapshot.market, AssetType.EQUITY)
           or bar.available_at.astimezone(UTC) > cutoff or bar.timestamp.astimezone(UTC) > cutoff
           or (bar.instrument.available_at is not None
               and bar.instrument.available_at.astimezone(UTC) > cutoff) for bar in bars):
        raise ValueError("market-value bar identity or cutoff mismatch")
    return checked_daily_bars(bars, as_of=snapshot.as_of)


def market_value_diagnostics(
    snapshot: MarketValueInputSnapshot, bars: tuple[Bar, ...] = (),
    policy: MarketValueMatchingPolicy | None = None,
) -> dict[str, object]:
    snapshot.__post_init__()
    if snapshot.inspections and snapshot.market is not Market.CHINA_A:
        raise ValueError("current market-value matching supports China-A observations only")
    policy = policy or MarketValueMatchingPolicy()
    policy.__post_init__()
    checked = _checked_bars(snapshot, bars)
    cutoff = snapshot.as_of.astimezone(UTC)
    latest_raw = max(bars, key=lambda bar: (
        bar.timestamp.astimezone(UTC), bar.available_at.astimezone(UTC)), default=None)
    latest_bar = checked[-1] if checked and latest_raw and not latest_raw.is_suspended else None
    ages: dict[str, int | None] = {
        "quote": None, "capture": None,
        "bar": _microseconds(cutoff - latest_bar.timestamp.astimezone(UTC)) if latest_bar else None,
    }
    result: dict[str, object] = {
        "symbol": snapshot.symbol, "market": snapshot.market.value, "as_of": snapshot.as_of,
        "market_value_input_hash": snapshot.input_hash, "status": "missing",
        "reasons": ["No market-value capture at cutoff"], "quote_bar_date_match": None,
        "quote_bar_price_match": None, "total_value_residual": None, "float_value_residual": None,
        "freshness": "UNASSESSED", "valuation_multiple": None, "valuation_authorized": False,
        "arithmetic_consistency": "UNASSESSED",
        "investment_scoring_authorized": False, "execution_authorized": False,
        "historical_replay_eligible": False,
        "validation_authorized": False,
        "model_version": MARKET_VALUE_DIAGNOSTICS_VERSION,
        "matching_policy": asdict(policy), "matching_policy_hash": policy.policy_hash,
        "bar_input_hash": sha256(financial_input_json(sorted(
            financial_input_json(daily_bar_content(bar)) for bar in bars)).encode()).hexdigest(),
        "bar_status": ("SUSPENDED_LATEST" if latest_raw and latest_raw.is_suspended
                       else "OBSERVED_UNQUALIFIED" if latest_bar else "UNAVAILABLE"),
    }
    if snapshot.inspections:
        key = max(e.record.available_at.astimezone(UTC) for e in snapshot.inspections)
        latest = [e for e in snapshot.inspections if e.record.available_at.astimezone(UTC) == key]
        if len(latest) != 1 or not latest[0].source_bound:
            result.update(status="rejected_or_ambiguous", reasons=["Latest capture binding failed"])
        else:
            record = latest[0].record
            ages["capture"] = _microseconds(cutoff - record.retrieved_at.astimezone(UTC))
            payload = record.payload
            raw_reasons = payload.get("reasons")
            reasons = list(raw_reasons) if isinstance(raw_reasons, list) else []
            result.update(status=payload["status"], reasons=reasons,
                          evidence_id=record.evidence_id,
                          claimed_quote_at=payload["claimed_quote_at"],
                          trust_level=record.trust_level.value,
                          availability_precision=record.availability_precision.value)
            if payload["status"] == "observed_unqualified":
                quote_at = datetime.fromisoformat(str(payload["claimed_quote_at"]))
                ages["quote"] = _microseconds(cutoff - quote_at.astimezone(UTC))
                with localcontext() as context:
                    context.prec = 150
                    context.Emax, context.Emin = 999999, -999999
                    for prefix in ("total", "float"):
                        result[f"{prefix}_value_residual"] = str(
                            Decimal(str(payload[f"{prefix}_market_value"]))
                            - Decimal(str(payload["price"]))
                            * Decimal(str(payload[f"{prefix}_shares"]))
                        )
                result["arithmetic_consistency"] = "EXACT_AGREEMENT"
                if any(Decimal(str(result[f"{p}_value_residual"])) != 0
                       for p in ("total", "float")):
                    result["arithmetic_consistency"] = "CONFLICT"
                    reasons.append("Value differs from price times shares; not rounded away")
                reasons.append("Native units/share class/quote clock and source policy unqualified")
                if latest_bar is not None:
                    zone = ZoneInfo("Asia/Shanghai")
                    result["quote_bar_date_match"] = (
                        quote_at.astimezone(zone).date()
                        == latest_bar.timestamp.astimezone(zone).date())
                    result["quote_bar_price_match"] = (
                        Decimal(str(payload["price"])) == latest_bar.close)
                    if not result["quote_bar_date_match"] or not result["quote_bar_price_match"]:
                        reasons.append("Quote date/price does not match latest supplied daily bar")
                else:
                    reasons.append("No current active unambiguous daily bar; no older fallback")
    statuses = {name: _freshness(ages[name], limit) for name, limit in (
        ("quote", policy.max_quote_age_seconds), ("capture", policy.max_capture_age_seconds),
        ("bar", policy.max_bar_age_seconds),
    )}
    for name, status in statuses.items():
        result[f"{name}_age_microseconds"] = ages[name]
        result[f"{name}_freshness"] = status
    result["freshness"] = (
        "FUTURE" if "FUTURE" in statuses.values() else
        "STALE" if "STALE" in statuses.values() else
        "UNAVAILABLE" if "UNAVAILABLE" in statuses.values() else
        "UNASSESSED" if "UNASSESSED" in statuses.values() else "WITHIN_CONFIGURED_LIMIT"
    )
    return {**result, "diagnostic_hash": sha256(financial_input_json(result).encode()).hexdigest()}
