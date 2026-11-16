"""Versioned, causal calculations over checked daily observations, not trade rules."""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from math import isfinite
from typing import Protocol

import pandas as pd

from tong_quant.domain.models import Bar
from tong_quant.research.bar_inputs import require_period


@dataclass(frozen=True, slots=True)
class TechnicalParameters:
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    kdj_period: int = 9
    kdj_k: int = 3
    kdj_d: int = 3
    triple_periods: tuple[int, ...] = (5, 10, 20)
    granville_period: int = 200
    slope_period: int = 3
    support_tolerance: float = 0.01
    extreme_deviation: float = 0.10
    setup_expiry: int = 5
    atr_period: int = 14
    atr_multiple: float = 2.0

    def __post_init__(self) -> None:
        for name in ("macd_fast", "macd_slow", "macd_signal", "kdj_period", "kdj_k",
                     "kdj_d", "granville_period", "slope_period", "setup_expiry", "atr_period"):
            require_period(name, getattr(self, name))
        if self.macd_fast >= self.macd_slow:
            raise ValueError("MACD fast period must be smaller than slow period")
        if (not isinstance(self.triple_periods, tuple) or len(self.triple_periods) != 3
                or len(set(self.triple_periods)) != 3):
            raise ValueError("triple periods must contain three distinct periods")
        for period in self.triple_periods:
            require_period("triple period", period)
        for name in ("support_tolerance", "extreme_deviation", "atr_multiple"):
            value = getattr(self, name)
            if type(value) not in {float, int} or not isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be positive and finite")
        if not self.support_tolerance < self.extreme_deviation < 1:
            raise ValueError("require support tolerance < extreme deviation < 1")


@dataclass(frozen=True, slots=True)
class MACDPoint:
    dif: float
    dea: float
    histogram: float
    cross: str


@dataclass(frozen=True, slots=True)
class KDJPoint:
    k: float
    d: float
    j: float
    rsv: float
    cross: str


def crossover(previous: float, current: float) -> str:
    if previous <= 0 < current:
        return "bullish"
    if previous >= 0 > current:
        return "bearish"
    return "none"


def macd(closes: Sequence[float], parameters: TechnicalParameters) -> MACDPoint | None:
    values = _prices(closes)
    # First-close recursive EMA; withhold output until slow + signal observations.
    if len(values) < parameters.macd_slow + parameters.macd_signal:
        return None
    series = pd.Series(values, dtype="float64")
    dif = (series.ewm(span=parameters.macd_fast, adjust=False).mean()
           - series.ewm(span=parameters.macd_slow, adjust=False).mean())
    dea = dif.ewm(span=parameters.macd_signal, adjust=False).mean()
    histogram = dif - dea
    return MACDPoint(float(dif.iloc[-1]), float(dea.iloc[-1]), float(histogram.iloc[-1]),
                     crossover(float(histogram.iloc[-2]), float(histogram.iloc[-1])))


class OHLCPrices(Protocol):
    @property
    def high(self) -> Decimal: ...

    @property
    def low(self) -> Decimal: ...

    @property
    def close(self) -> Decimal: ...


def kdj(bars: Sequence[OHLCPrices], parameters: TechnicalParameters) -> KDJPoint | None:
    if len(bars) < parameters.kdj_period + 1:
        return None
    for values in ([float(bar.close) for bar in bars], [float(bar.high) for bar in bars],
                   [float(bar.low) for bar in bars]):
        _prices(values)
    k = d = 50.0
    previous_difference = 0.0
    rsv = 50.0
    for index in range(parameters.kdj_period - 1, len(bars)):
        window = bars[index - parameters.kdj_period + 1:index + 1]
        low = min(float(bar.low) for bar in window)
        high = max(float(bar.high) for bar in window)
        rsv = 50.0 if high == low else 100 * (float(bars[index].close) - low) / (high - low)
        previous_difference = k - d
        k += (rsv - k) / parameters.kdj_k
        d += (k - d) / parameters.kdj_d
    return KDJPoint(k, d, 3 * k - 2 * d, rsv, crossover(previous_difference, k - d))


def sma(closes: Sequence[float], period: int) -> tuple[float | None, ...]:
    require_period("SMA period", period)
    values = _prices(closes)
    result = pd.Series(values, dtype="float64").rolling(period, min_periods=period).mean()
    return tuple(None if pd.isna(value) else float(value) for value in result)


def atr(bars: Sequence[Bar], period: int) -> float | None:
    """Arithmetic true-range mean, explicitly not Wilder smoothing."""
    require_period("ATR period", period)
    if len(bars) <= period:
        return None
    ranges = [max(float(current.high - current.low),
                  abs(float(current.high - previous.close)),
                  abs(float(current.low - previous.close)))
              for previous, current in zip(bars[-period - 1:-1], bars[-period:], strict=True)]
    return sum(ranges) / period


def _prices(values: Sequence[float]) -> tuple[float, ...]:
    if any(type(value) not in {float, int} or not isfinite(value) or value <= 0
           for value in values):
        raise ValueError("indicator prices must be finite positive numbers")
    return tuple(float(value) for value in values)
