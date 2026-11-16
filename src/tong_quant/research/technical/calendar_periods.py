"""Calendar-bucket OHLC observations; neither verified session candles nor scored research."""

from dataclasses import asdict
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, localcontext
from hashlib import sha256
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.domain.enums import AssetType, InstrumentCategory, Market
from tong_quant.domain.models import Bar, require_timezone
from tong_quant.research.bar_inputs import checked_daily_bars
from tong_quant.version import (
    CALENDAR_PERIOD_DIAGNOSTICS_VERSION,
    CALENDAR_YEAR_DIAGNOSTICS_VERSION,
)

_ZONES = {Market.CHINA_A: "Asia/Shanghai", Market.US: "America/New_York",
          Market.HONG_KONG: "Asia/Hong_Kong", Market.MALAYSIA: "Asia/Kuala_Lumpur"}
_MAX_ITEMS = 20000


def _start(day: date, frequency: str) -> date:
    if frequency == "yearly":
        return date(day.year, 1, 1)
    return day - timedelta(days=day.weekday()) if frequency == "weekly" else day.replace(day=1)


def _end(start: date, frequency: str) -> date:
    try:
        if frequency == "yearly":
            return date(start.year + 1, 1, 1)
        return (start + timedelta(days=7) if frequency == "weekly" else
                date(start.year + (start.month == 12), start.month % 12 + 1, 1))
    except (OverflowError, ValueError):
        raise ValueError("calendar period outside supported date bounds") from None


def _frames(selected: tuple[Bar, ...], *, frequency: str, zone: ZoneInfo,
            as_of: datetime) -> list[dict[str, Any]]:
    if not selected:
        return []
    data = pd.DataFrame([{
        "start": _start(bar.timestamp.astimezone(zone).date(), frequency),
        "bar": bar, "open": bar.open, "high": bar.high, "low": bar.low,
        "close": bar.close, "volume": bar.volume,
    } for bar in selected])
    groups = {start: group for start, group in data.groupby("start", sort=True)}
    start = _start(selected[0].timestamp.astimezone(zone).date(), frequency)
    last = _start(as_of.astimezone(zone).date(), frequency)
    result: list[dict[str, Any]] = []
    with localcontext() as context:
        context.prec = 100
        while start <= last:
            if len(result) >= _MAX_ITEMS:
                raise ValueError("calendar period inventory exceeds supported bounds")
            end = _end(start, frequency)
            end_at = datetime.combine(end, time.min, tzinfo=zone).astimezone(UTC)
            ended = end_at <= as_of.astimezone(UTC)
            group = groups.get(start)
            members = tuple(group["bar"]) if group is not None else ()
            suspended = tuple(bar for bar in members if bar.is_suspended)
            status = ("MISSING_PERIOD_OBSERVATIONS" if not members else
                      "SUSPENSION_OBSERVED_IN_PERIOD" if suspended else
                      "CALENDAR_PERIOD_NOT_ENDED" if not ended else
                      "CALENDAR_PERIOD_ENDED_COVERAGE_UNVERIFIED")
            values: dict[str, str | None] = dict.fromkeys(
                ("open", "high", "low", "close", "volume", "turnover"))
            if members and ended and not suspended:
                assert group is not None
                # Object/Decimal operations retain exact observations, not floating-point prices.
                values.update(open=str(group["open"].iloc[0]), high=str(group["high"].max()),
                    low=str(group["low"].min()), close=str(group["close"].iloc[-1]),
                    volume=str(group["volume"].sum()),
                    turnover=(str(sum((bar.turnover for bar in members
                                      if bar.turnover is not None), Decimal(0)))
                              if all(bar.turnover is not None for bar in members) else None))
            result.append({
                "period_start_date": start.isoformat(),
                "period_end_exclusive_date": end.isoformat(),
                "calendar_end_at": end_at, "calendar_period_ended": ended,
                "status": status, "observed_date_count": len(members),
                "suspended_observation_count": len(suspended),
                "first_observed_at": members[0].timestamp if members else None,
                "last_observed_at": members[-1].timestamp if members else None,
                "latest_available_at": max((bar.available_at for bar in members),
                    key=lambda item: item.astimezone(UTC)) if members else None,
                "ohlcv": values, "session_coverage": "UNVERIFIED",
                "expected_session_count": None, "session_coverage_percent": None,
                "scoring_authorized": False,
            })
            start = end
    return result


def calendar_period_diagnostics(bars: tuple[Bar, ...], *, market: Market,
                                as_of: datetime, include_yearly: bool = False) -> dict[str, Any]:
    require_timezone(as_of, "calendar period cutoff")
    if type(include_yearly) is not bool:
        raise ValueError("yearly calendar opt-in must be boolean")
    if market not in _ZONES or type(bars) is not tuple or len(bars) > _MAX_ITEMS:
        raise ValueError("calendar diagnostics require supported market and bounded daily tuple")
    for bar in bars:
        require_timezone(bar.timestamp, "calendar input observation")
        require_timezone(bar.available_at, "calendar input availability")
        if bar.instrument.available_at is not None:
            require_timezone(bar.instrument.available_at, "calendar instrument availability")
        if bar.ingested_at is not None:
            require_timezone(bar.ingested_at, "calendar ingestion timestamp")
            if bar.ingested_at.astimezone(UTC) > as_of.astimezone(UTC):
                raise ValueError("calendar input contains future ingestion metadata")
        if (bar.instrument.market is not market or bar.instrument.asset_type is not AssetType.EQUITY
                or bar.instrument.category is not InstrumentCategory.EQUITY
                or type(bar.is_suspended) is not bool):
            raise ValueError("calendar diagnostic instrument scope mismatch")
    checked_daily_bars(bars, as_of=as_of, require_latest_active=True)
    latest: dict[datetime, Bar] = {}
    for bar in bars:
        bar.__post_init__()
        bar.instrument.__post_init__()
        numbers = (bar.open, bar.high, bar.low, bar.close, bar.volume,
                   *((bar.turnover,) if bar.turnover is not None else ()))
        if any(abs(value) > Decimal("1e24") or abs(int(value.as_tuple().exponent)) > 36
               for value in numbers):
            raise ValueError("calendar decimal input exceeds supported exact-arithmetic bounds")
        observed = bar.timestamp.astimezone(UTC)
        previous = latest.get(observed)
        if (previous is None
                or previous.available_at.astimezone(UTC) < bar.available_at.astimezone(UTC)):
            latest[observed] = bar
    selected = tuple(latest[key] for key in sorted(latest))
    if len({(bar.instrument.currency, bar.instrument.exchange) for bar in bars}) > 1:
        raise ValueError("calendar inputs cannot mix currencies or exchange labels")
    zone = ZoneInfo(_ZONES[market])
    local_dates = [bar.timestamp.astimezone(zone).date() for bar in selected]
    if len(set(local_dates)) != len(local_dates):
        raise ValueError("calendar inputs contain multiple observations on one market-local date")
    content = [asdict(bar) for bar in bars]
    reject_sensitive_structure(content)
    content.sort(key=financial_input_json)
    blocked = bool(selected and selected[-1].is_suspended)
    document: dict[str, Any] = {
        "model_version": CALENDAR_PERIOD_DIAGNOSTICS_VERSION, "market": market.value,
        "subject": selected[0].instrument.symbol if selected else None,
        "as_of": as_of.astimezone(UTC), "market_timezone": _ZONES[market],
        "week_convention": "MONDAY_TO_NEXT_MONDAY_LOCAL_MIDNIGHT",
        "month_convention": "FIRST_TO_NEXT_FIRST_LOCAL_MIDNIGHT",
        "source_observations_hash": sha256(financial_input_json(content).encode()).hexdigest(),
        "supplied_row_count": len(bars), "selected_observation_count": len(selected),
        "status": ("SUSPENDED_LATEST" if blocked else
                   "OBSERVED_UNQUALIFIED" if selected else "MISSING"),
        "weekly": _frames(selected, frequency="weekly", zone=zone, as_of=as_of)
                  if not blocked else [],
        "monthly": _frames(selected, frequency="monthly", zone=zone, as_of=as_of)
                   if not blocked else [],
        "suspension_observations": [{"observed_at": bar.timestamp, "available_at": bar.available_at}
                                    for bar in selected if bar.is_suspended],
        "calendar_verified": False, "source_adjustment_basis_verified": False,
        "source_freshness": "UNASSESSED", "source_trust": "NOT_ASSESSED",
        "lifecycle_resumption_verified": False, "scoring_authorized": False,
        "historical_replay_eligible": False, "validation_authorized": False,
        "execution_authorized": False,
        "limitations": (
            "Calendar buckets aggregate observations, not verified complete exchange sessions",
            "Calendar ended does not mean complete data, fresh source or qualified price basis",
            "Current calendar periods withhold numeric candles; closed sessions are not inferred",
            "Missing periods stay missing, never forward-filled or assigned zero volume",
            "Suspensions block affected periods; latest suspension blocks the entire diagnostic",
            "Unknown turnover remains null; no currency, split or dividend adjustment is inferred",
            "No legacy score replacement, strategy validation, holding period or trade decision",
        ),
    }
    if include_yearly:
        document.update(model_version=CALENDAR_YEAR_DIAGNOSTICS_VERSION,
            year_convention="JANUARY_FIRST_TO_NEXT_JANUARY_FIRST_LOCAL_MIDNIGHT",
            yearly=_frames(selected, frequency="yearly", zone=zone, as_of=as_of)
                   if not blocked else [])
    reject_sensitive_structure(document)
    return {**document, "input_hash": sha256(financial_input_json(document).encode()).hexdigest()}
