"""Family-aware descriptive output. No investment score or execution instruction."""

import json
from dataclasses import asdict
from datetime import UTC, datetime
from hashlib import sha256

from tong_quant.data.price_evidence import daily_bar_content
from tong_quant.domain.models import Bar
from tong_quant.research.bar_inputs import checked_daily_bars
from tong_quant.research.models import ResearchValue
from tong_quant.research.technical.events import (
    granville_events,
    startup_observation,
    triple_cross_events,
)
from tong_quant.research.technical.indicators import TechnicalParameters, atr, kdj, macd, sma
from tong_quant.version import TECHNICAL_CALCULATIONS_VERSION


def technical_diagnostics(
    bars: tuple[Bar, ...], parameters: TechnicalParameters, *, as_of: datetime,
) -> dict[str, ResearchValue]:
    supplied = bars
    bars = checked_daily_bars(bars, as_of=as_of, require_latest_active=True)
    latest = max(supplied, key=lambda bar: (
        bar.timestamp.astimezone(UTC), bar.available_at.astimezone(UTC)), default=None)
    suspended = latest is not None and latest.is_suspended
    input_status = ("SUSPENDED_LATEST" if suspended else
                    "OBSERVED_UNQUALIFIED" if latest else "MISSING")
    closes = [float(bar.close) for bar in bars]
    momentum = macd(closes, parameters)
    stochastic = kdj(bars, parameters)
    triple = triple_cross_events(bars, parameters)
    granville = granville_events(bars, parameters)
    setup = startup_observation(bars, parameters)
    average = sma(closes, parameters.granville_period)
    trend_directions = []
    if average and average[-1] is not None:
        trend_directions.append(_direction(closes[-1] - average[-1]))
    trend_directions.extend("BULLISH" if event.startswith("bullish") else "BEARISH"
                            for event in triple)
    # Extreme-deviation mean reversion is separate from continuation, never another vote.
    continuation = tuple(event for event in granville if "_4_" not in event)
    trend_directions.extend("BULLISH" if "_bull_" in event else "BEARISH"
                            for event in continuation)
    trend_family = _family(trend_directions)
    momentum_family = "INSUFFICIENT_DATA"
    if momentum is not None and stochastic is not None:
        momentum_family = _family([_direction(momentum.histogram),
                                   _direction(stochastic.k - stochastic.d)])
    families = (trend_family, momentum_family)
    if "INSUFFICIENT_DATA" in families:
        confluence = "INSUFFICIENT_DATA"
    elif "CONFLICTED" in families or {"BULLISH", "BEARISH"}.issubset(families):
        confluence = "CONFLICTED"
    elif all(family == "BULLISH" for family in families):
        confluence = "BULLISH_TECHNICAL_ALIGNMENT"
    elif all(family == "BEARISH" for family in families):
        confluence = "BEARISH_TECHNICAL_ALIGNMENT"
    else:
        confluence = "NEUTRAL"
    missing = []
    if suspended:
        missing.append("latest_suspended_observation")
    if momentum is None:
        missing.append("macd_warmup")
    if stochastic is None:
        missing.append("kdj_warmup")
    if len(bars) < max(parameters.triple_periods):
        missing.append("triple_average_warmup")
    if len(bars) < parameters.granville_period + parameters.slope_period + 1:
        missing.append("granville_warmup")
    value = atr(bars, parameters.atr_period)
    payload = {
        "version": TECHNICAL_CALCULATIONS_VERSION,
        "as_of": as_of.astimezone(UTC).isoformat(),
        "parameters": asdict(parameters),
        "input_status": input_status,
        "blocking_observation": daily_bar_content(latest) if latest and suspended else None,
        "bars": [
            {"symbol": bar.instrument.symbol, "market": bar.instrument.market.value,
             "timestamp": bar.timestamp.astimezone(UTC).isoformat(),
             "available_at": bar.available_at.astimezone(UTC).isoformat(),
             "source": bar.source, "adjustment": bar.adjustment.value,
             "open": str(bar.open), "high": str(bar.high), "low": str(bar.low),
             "close": str(bar.close), "volume": str(bar.volume),
             "turnover": None if bar.turnover is None else str(bar.turnover)}
            for bar in bars
        ],
    }
    return {
        "technical_calculations_version": TECHNICAL_CALCULATIONS_VERSION,
        "technical_input_status": input_status,
        "technical_latest_supplied_observed_at": (
            latest.timestamp.astimezone(UTC).isoformat() if latest else None),
        "technical_latest_supplied_available_at": (
            latest.available_at.astimezone(UTC).isoformat() if latest else None),
        "technical_usable_observations": len(bars),
        "technical_latest_close": closes[-1] if closes else None,
        "technical_last_observed_at": (
            bars[-1].timestamp.astimezone(UTC).isoformat() if bars else None),
        "technical_latest_input_available_at": max(
            (bar.available_at for bar in bars), default=as_of,
            key=lambda value: value.astimezone(UTC),
        ).astimezone(UTC).isoformat() if bars else None,
        "technical_input_hash": sha256(json.dumps(
            payload, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()).hexdigest(),
        "technical_parameters": json.dumps(asdict(parameters), sort_keys=True),
        "macd_dif": None if momentum is None else momentum.dif,
        "macd_dea": None if momentum is None else momentum.dea,
        "macd_histogram": None if momentum is None else momentum.histogram,
        "macd_cross": "unavailable" if momentum is None else momentum.cross,
        "kdj_k": None if stochastic is None else stochastic.k,
        "kdj_d": None if stochastic is None else stochastic.d,
        "kdj_j": None if stochastic is None else stochastic.j,
        "kdj_cross": "unavailable" if stochastic is None else stochastic.cross,
        "kdj_extended": None if stochastic is None else stochastic.j > 100 or stochastic.j < 0,
        "triple_average_events": ",".join(triple),
        "granville_events": ",".join(granville),
        "granville_available": "granville_warmup" not in missing,
        "mean_reversion_events": ",".join(event for event in granville if "_4_" in event),
        "trend_structure_family": trend_family,
        "momentum_family": momentum_family,
        "technical_confluence": confluence,
        "technical_family_count": sum(family != "INSUFFICIENT_DATA" for family in families),
        "technical_defined_family_count": 2,
        "participation_family": "NOT_ASSESSED",
        "fundamental_family": "NOT_ASSESSED",
        "size_style_status": "INSUFFICIENT_DATA",
        "seven_plus_one_status": "DEFERRED_BY_OWNER",
        "setup_state": setup.state,
        "setup_direction": setup.direction,
        "setup_observed_index": setup.observed_index,
        "setup_confirmed_index": setup.confirmed_index,
        "structural_invalidation_reference": setup.structural_reference,
        "dynamic_invalidation_reference": setup.trailing_reference,
        "technical_atr": value,
        "technical_missing_inputs": ",".join(missing),
        "technical_research_only": True,
        "technical_scoring_admitted": False,
    }


def _direction(value: float) -> str:
    return "BULLISH" if value > 0 else "BEARISH" if value < 0 else "NEUTRAL"


def _family(directions: list[str]) -> str:
    observed = set(directions) - {"NEUTRAL"}
    if not directions:
        return "INSUFFICIENT_DATA"
    if len(observed) > 1:
        return "CONFLICTED"
    return next(iter(observed), "NEUTRAL")
