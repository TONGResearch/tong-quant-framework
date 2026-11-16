"""Explicit candle/MA event definitions; no look-ahead labels or orders."""

from collections.abc import Sequence
from dataclasses import dataclass

from tong_quant.domain.models import Bar
from tong_quant.research.technical.indicators import TechnicalParameters, atr, sma


def triple_cross_events(bars: Sequence[Bar], parameters: TechnicalParameters) -> tuple[str, ...]:
    closes = [float(bar.close) for bar in bars]
    averages = [sma(closes, period)[-1] if closes else None
                for period in parameters.triple_periods]
    return _triple_event(bars[-1], averages) if bars else ()


def _triple_event(current: Bar, averages: Sequence[float | None]) -> tuple[str, ...]:
    if any(value is None for value in averages):
        return ()
    cluster = [value for value in averages if value is not None]
    if (current.close > current.open
            and float(current.open) <= min(cluster) <= max(cluster) <= float(current.close)):
        return ("bullish_body_crosses_ma_cluster",)
    if (current.close < current.open
            and float(current.close) <= min(cluster) <= max(cluster) <= float(current.open)):
        return ("bearish_body_crosses_ma_cluster",)
    return ()


def granville_events(bars: Sequence[Bar], parameters: TechnicalParameters) -> tuple[str, ...]:
    if len(bars) < parameters.granville_period + parameters.slope_period + 1:
        return ()
    closes = [float(bar.close) for bar in bars]
    averages = sma(closes, parameters.granville_period)
    current_ma = averages[-1]
    previous_ma = averages[-2]
    earlier_ma = averages[-1 - parameters.slope_period]
    assert current_ma is not None and previous_ma is not None and earlier_ma is not None
    close, previous = closes[-1], closes[-2]
    slope = current_ma / earlier_ma - 1
    deviation = close / current_ma - 1
    tolerance = parameters.support_tolerance
    up_cross = previous <= previous_ma and close > current_ma
    down_cross = previous >= previous_ma and close < current_ma
    events: list[str] = []
    if up_cross and slope >= 0:
        events.append("granville_bull_1_stabilized_up_cross")
    if down_cross and slope > 0 and deviation >= -tolerance:
        events.append("granville_bull_2_rising_ma_pullback")
    if (slope > 0 and previous > previous_ma and close > current_ma
            and current_ma <= float(bars[-1].low) <= current_ma * (1 + tolerance)):
        events.append("granville_bull_3_rising_ma_support")
    if deviation <= -parameters.extreme_deviation:
        events.append("granville_bull_4_extreme_downside_deviation")
    if down_cross and slope <= 0:
        events.append("granville_bear_1_stabilized_down_cross")
    if up_cross and slope < 0 and deviation <= tolerance:
        events.append("granville_bear_2_falling_ma_rebound")
    if (slope < 0 and previous < previous_ma and close < current_ma
            and current_ma * (1 - tolerance) <= float(bars[-1].high) <= current_ma):
        events.append("granville_bear_3_falling_ma_resistance")
    if deviation >= parameters.extreme_deviation:
        events.append("granville_bear_4_extreme_upside_deviation")
    return tuple(events)


@dataclass(frozen=True, slots=True)
class SetupObservation:
    state: str
    direction: str | None = None
    observed_index: int | None = None
    confirmed_index: int | None = None
    structural_reference: float | None = None
    trailing_reference: float | None = None


def startup_observation(bars: Sequence[Bar], parameters: TechnicalParameters) -> SetupObservation:
    """Replay prefixes: later confirmation never changes the original ARMED observation."""
    if len(bars) < max(parameters.triple_periods):
        return SetupObservation("INSUFFICIENT_DATA")
    state = SetupObservation("WATCH")
    trigger_high = trigger_low = 0.0
    averages = [sma([float(bar.close) for bar in bars], period)
                for period in parameters.triple_periods]
    for index, current in enumerate(bars):
        if state.state in {"ARMED", "CONFIRMED"}:
            assert state.observed_index is not None and state.structural_reference is not None
            observed_index = state.observed_index
            close = float(current.close)
            reference = state.trailing_reference or state.structural_reference
            invalid = close < reference if state.direction == "bullish" else close > reference
            if invalid:
                state = SetupObservation("INVALIDATED", state.direction, state.observed_index,
                                         state.confirmed_index, state.structural_reference,
                                         reference)
            elif state.state == "ARMED" and index - observed_index > parameters.setup_expiry:
                state = SetupObservation("EXPIRED", state.direction, state.observed_index,
                                         structural_reference=state.structural_reference)
            elif state.state == "CONFIRMED" or (
                close > trigger_high if state.direction == "bullish" else close < trigger_low
            ):
                value = atr(bars[:index + 1], parameters.atr_period)
                trailing = reference
                if value is not None:
                    candidate = close - parameters.atr_multiple * value if (
                        state.direction == "bullish"
                    ) else close + parameters.atr_multiple * value
                    trailing = max(reference, candidate) if state.direction == "bullish" else min(
                        reference, candidate
                    )
                state = SetupObservation("CONFIRMED", state.direction, state.observed_index,
                                         state.confirmed_index if state.confirmed_index is not None
                                         else index, state.structural_reference, trailing)
        events = _triple_event(current, [series[index] for series in averages])
        if events and state.state != "CONFIRMED":
            direction = "bullish" if events[0].startswith("bullish") else "bearish"
            trigger_high, trigger_low = float(current.high), float(current.low)
            structural = trigger_low if direction == "bullish" else trigger_high
            state = SetupObservation("ARMED", direction, index, structural_reference=structural)
    return state
