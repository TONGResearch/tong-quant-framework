from collections.abc import Sequence
from datetime import datetime
from math import sqrt
from statistics import fmean, pstdev

from tong_quant.domain.models import Bar
from tong_quant.market_regime.models import RegimeMetric


def trend_metric(
    bars: Sequence[Bar],
    *,
    name: str,
    as_of: datetime,
    short_window: int = 20,
    long_window: int = 60,
) -> RegimeMetric:
    _validate_bars(bars, as_of, minimum=long_window)
    closes = [float(bar.close) for bar in bars]
    latest = closes[-1]
    short_average = fmean(closes[-short_window:])
    long_average = fmean(closes[-long_window:])
    price_distance = (latest / long_average) - 1
    average_spread = (short_average / long_average) - 1
    value = _clamp(0.6 * price_distance / 0.10 + 0.4 * average_spread / 0.06)
    return RegimeMetric(
        name=name,
        value=value,
        available_at=max(bar.available_at for bar in bars),
        source="market_data",
        description=(
            f"latest={latest:.4f}, short_ma={short_average:.4f}, "
            f"long_ma={long_average:.4f}"
        ),
    )


def relative_strength_metric(
    market_bars: Sequence[Bar],
    benchmark_bars: Sequence[Bar],
    *,
    name: str,
    as_of: datetime,
    window: int = 60,
) -> RegimeMetric:
    _validate_bars(market_bars, as_of, minimum=window + 1)
    _validate_bars(benchmark_bars, as_of, minimum=window + 1)
    market_return = float(market_bars[-1].close / market_bars[-window - 1].close) - 1
    benchmark_return = float(
        benchmark_bars[-1].close / benchmark_bars[-window - 1].close
    ) - 1
    relative_return = market_return - benchmark_return
    return RegimeMetric(
        name=name,
        value=_clamp(relative_return / 0.15),
        available_at=max(market_bars[-1].available_at, benchmark_bars[-1].available_at),
        source="market_data",
        description=(
            f"market_return={market_return:.4f}, "
            f"benchmark_return={benchmark_return:.4f}"
        ),
    )


def volatility_metric(
    bars: Sequence[Bar],
    *,
    name: str,
    as_of: datetime,
    window: int = 20,
    neutral_annualized_volatility: float = 0.20,
) -> RegimeMetric:
    _validate_bars(bars, as_of, minimum=window + 1)
    closes = [float(bar.close) for bar in bars[-window - 1 :]]
    returns = [
        (current / previous) - 1
        for previous, current in zip(closes[:-1], closes[1:], strict=True)
    ]
    annualized = pstdev(returns) * sqrt(252)
    value = _clamp((neutral_annualized_volatility - annualized) / 0.20)
    return RegimeMetric(
        name=name,
        value=value,
        available_at=bars[-1].available_at,
        source="market_data",
        description=f"annualized_volatility={annualized:.4f}",
    )


def breadth_metric(
    *,
    name: str,
    advancing: int,
    declining: int,
    available_at: datetime,
    source: str,
) -> RegimeMetric:
    total = advancing + declining
    if total <= 0:
        raise ValueError("breadth requires a positive advancing plus declining count")
    ratio = (advancing - declining) / total
    return RegimeMetric(
        name=name,
        value=_clamp(ratio),
        available_at=available_at,
        source=source,
        description=f"advancing={advancing}, declining={declining}",
    )


def level_change_metric(
    *,
    name: str,
    current: float,
    baseline: float,
    available_at: datetime,
    source: str,
    full_scale_change: float = 0.30,
) -> RegimeMetric:
    if baseline <= 0:
        raise ValueError("metric baseline must be positive")
    change = (current / baseline) - 1
    return RegimeMetric(
        name=name,
        value=_clamp(change / full_scale_change),
        available_at=available_at,
        source=source,
        description=f"current={current:.4f}, baseline={baseline:.4f}, change={change:.4f}",
    )


def count_level_metric(
    *,
    name: str,
    count: int,
    universe_size: int,
    available_at: datetime,
    source: str,
) -> RegimeMetric:
    if universe_size <= 0:
        raise ValueError("universe size must be positive")
    ratio = count / universe_size
    return RegimeMetric(
        name=name,
        value=_clamp((ratio - 0.5) / 0.5),
        available_at=available_at,
        source=source,
        description=f"count={count}, universe_size={universe_size}, ratio={ratio:.4f}",
    )


def _validate_bars(bars: Sequence[Bar], as_of: datetime, *, minimum: int) -> None:
    if len(bars) < minimum:
        raise ValueError(f"at least {minimum} bars are required")
    if any(bar.available_at > as_of for bar in bars):
        raise ValueError("future bars are not allowed in market regime metrics")
    dates = [bar.timestamp for bar in bars]
    if dates != sorted(dates):
        raise ValueError("bars must be sorted by timestamp")


def _clamp(value: float) -> float:
    return max(-1.0, min(1.0, value))
