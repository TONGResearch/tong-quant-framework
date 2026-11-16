"""Select unambiguous visible daily observations without inventing sessions."""

from datetime import UTC, datetime
from decimal import Decimal
from math import isfinite

from tong_quant.domain.enums import Adjustment
from tong_quant.domain.models import Bar, require_timezone
from tong_quant.research.models import ResearchContext


def research_daily_bars(
    context: ResearchContext, *, require_latest_active: bool = False,
) -> tuple[Bar, ...]:
    context.validate()
    return checked_daily_bars(context.bars, as_of=context.as_of,
                              require_latest_active=require_latest_active)


def checked_daily_bars(
    bars: tuple[Bar, ...], *, as_of: datetime, require_latest_active: bool = False,
) -> tuple[Bar, ...]:
    require_timezone(as_of, "as_of")
    if type(require_latest_active) is not bool:
        raise ValueError("latest-active requirement must be boolean")
    cutoff = as_of.astimezone(UTC)
    identities = {(bar.instrument.symbol, bar.instrument.market, bar.instrument.asset_type)
                  for bar in bars}
    if len(identities) > 1:
        raise ValueError("daily research bar instrument mismatch")
    if any(bar.timestamp.astimezone(UTC) > cutoff or bar.available_at.astimezone(UTC) > cutoff
           or (bar.instrument.available_at is not None
               and bar.instrument.available_at.astimezone(UTC) > cutoff)
           for bar in bars):
        raise ValueError("daily research contains future data")
    if any(bar.available_at.astimezone(UTC) < bar.timestamp.astimezone(UTC) for bar in bars):
        raise ValueError("daily research availability cannot precede observation")
    versions: dict[tuple[datetime, datetime], Bar] = {}
    latest: dict[datetime, Bar] = {}
    sources = {bar.source for bar in bars}
    if len(sources) > 1:
        raise ValueError("daily research bars require one explicit source series")
    for bar in bars:
        if bar.adjustment is not Adjustment.NONE:
            raise ValueError("daily research requires unadjusted price evidence")
        numbers: tuple[Decimal, ...] = (bar.open, bar.high, bar.low, bar.close, bar.volume)
        if bar.turnover is not None:
            numbers += (bar.turnover,)
        if any(not number.is_finite() or not isfinite(float(number)) for number in numbers):
            raise ValueError("daily research bar values must be finite")
        if not bar.is_suspended and min(bar.open, bar.high, bar.low, bar.close) <= 0:
            raise ValueError("active daily research prices must be positive")
        observed = bar.timestamp.astimezone(UTC)
        available = bar.available_at.astimezone(UTC)
        key = (observed, available)
        previous = versions.get(key)
        if previous is not None and _content(previous) != _content(bar):
            raise ValueError("daily research contains conflicting bar versions")
        versions[key] = bar
        selected = latest.get(observed)
        if selected is None or selected.available_at.astimezone(UTC) < available:
            latest[observed] = bar
    ordered = tuple(sorted(latest.values(), key=lambda bar: bar.timestamp.astimezone(UTC)))
    observed_dates = [bar.timestamp.astimezone(UTC).date() for bar in ordered]
    if len(set(observed_dates)) != len(observed_dates):
        raise ValueError("daily research cannot consume multiple timestamps on one UTC date")
    if require_latest_active and ordered and ordered[-1].is_suspended:
        return ()
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
