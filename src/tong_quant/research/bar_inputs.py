"""Select unambiguous visible daily observations without inventing sessions."""

from datetime import UTC, datetime
from decimal import Decimal
from math import isfinite

from tong_quant.domain.enums import Adjustment
from tong_quant.domain.models import Bar
from tong_quant.research.models import ResearchContext


def research_daily_bars(context: ResearchContext) -> tuple[Bar, ...]:
    context.validate()
    versions: dict[tuple[datetime, datetime], Bar] = {}
    latest: dict[datetime, Bar] = {}
    sources = {bar.source for bar in context.bars}
    if len(sources) > 1:
        raise ValueError("daily research bars require one explicit source series")
    for bar in context.bars:
        if bar.adjustment is not Adjustment.NONE:
            raise ValueError("daily research requires unadjusted price evidence")
        numbers: tuple[Decimal, ...] = (bar.open, bar.high, bar.low, bar.close, bar.volume)
        if bar.turnover is not None:
            numbers += (bar.turnover,)
        if any(not number.is_finite() or not isfinite(float(number)) for number in numbers):
            raise ValueError("daily research bar values must be finite")
        if not bar.is_suspended and min(bar.open, bar.high, bar.low, bar.close) <= 0:
            raise ValueError("active daily research prices must be positive")
        key = (bar.timestamp, bar.available_at)
        previous = versions.get(key)
        if previous is not None and _content(previous) != _content(bar):
            raise ValueError("daily research contains conflicting bar versions")
        versions[key] = bar
        selected = latest.get(bar.timestamp)
        if selected is None or selected.available_at < bar.available_at:
            latest[bar.timestamp] = bar
    ordered = tuple(sorted(latest.values(), key=lambda bar: bar.timestamp))
    observed_dates = [bar.timestamp.astimezone(UTC).date() for bar in ordered]
    if len(set(observed_dates)) != len(observed_dates):
        raise ValueError("daily research cannot consume multiple timestamps on one UTC date")
    # Retain originals in ResearchContext; suspension revisions cannot resurrect an older bar.
    return tuple(bar for bar in ordered if not bar.is_suspended)


def _content(bar: Bar) -> tuple[object, ...]:
    return (
        bar.open, bar.high, bar.low, bar.close, bar.volume, bar.turnover,
        bar.adjustment, bar.is_suspended, bar.source,
    )


def require_period(name: str, value: int) -> None:
    if type(value) is not int or value < 1:
        raise ValueError(f"{name} must be a positive integer")
