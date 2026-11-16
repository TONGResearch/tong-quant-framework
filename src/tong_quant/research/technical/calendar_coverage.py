"""Compare supplied market-calendar declarations with observations, never certify sessions."""

from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from typing import Any
from zoneinfo import ZoneInfo

from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market
from tong_quant.domain.models import Bar, TradingSession, require_timezone
from tong_quant.research.technical.calendar_periods import calendar_period_diagnostics
from tong_quant.version import CALENDAR_COVERAGE_VERSION, CALENDAR_YEAR_COVERAGE_VERSION

_MAX_ROWS = 20000


def _calendar_versions(sessions: tuple[TradingSession, ...], market: Market,
                       as_of: datetime) -> dict[date, TradingSession]:
    if type(sessions) is not tuple or len(sessions) > _MAX_ROWS:
        raise ValueError("calendar coverage requires a bounded tuple of declarations")
    versions: dict[tuple[date, datetime], TradingSession] = {}
    selected: dict[date, TradingSession] = {}
    for row in sessions:
        if (not isinstance(row, TradingSession) or row.market is not market
                or type(row.trade_date) is not date or type(row.is_open) is not bool
                or not isinstance(row.source, str) or not row.source.strip()):
            raise ValueError("calendar declaration identity or field mismatch")
        require_timezone(row.available_at, "calendar declaration availability")
        available = row.available_at.astimezone(UTC)
        if available > as_of.astimezone(UTC):
            raise ValueError("calendar coverage contains future availability")
        key = row.trade_date, available
        previous = versions.get(key)
        if previous is not None and (row.is_open, row.source) != (
                previous.is_open, previous.source):
            raise ValueError("conflicting calendar declaration versions")
        versions[key] = row
        latest = selected.get(row.trade_date)
        if latest is None or latest.available_at.astimezone(UTC) < available:
            selected[row.trade_date] = row
    if len({row.source for row in sessions}) > 1:
        raise ValueError("calendar coverage cannot silently merge different sources")
    reject_sensitive_structure([asdict(row) for row in sessions])
    return selected


def _compare(frame: dict[str, Any], selected: dict[date, TradingSession],
             observed: set[date], suspended: set[date], cutoff_date: date) -> dict[str, Any]:
    start = date.fromisoformat(frame["period_start_date"])
    end = date.fromisoformat(frame["period_end_exclusive_date"])
    # Future schedule declarations may be known now, but cannot complete a current period.
    days = {start + timedelta(days=index) for index in range((end - start).days)
            if start + timedelta(days=index) <= cutoff_date}
    known = days & selected.keys()
    unknown = days - known
    opens = {day for day in known if selected[day].is_open}
    closed = known - opens
    matches = opens & observed
    missing = opens - observed
    halted = opens & suspended
    conflicts = closed & observed
    flags = tuple(name for condition, name in (
        (bool(conflicts), "OBSERVATION_CALENDAR_CONFLICT"),
        (bool(unknown), "CALENDAR_DATES_MISSING"),
        (not frame["calendar_period_ended"], "PERIOD_NOT_ENDED"),
        (bool(missing), "OPEN_DATE_OBSERVATIONS_MISSING"),
        (bool(halted), "SUSPENSION_OBSERVATIONS_PRESENT"),
        (not opens, "NO_OPEN_DATES_DECLARED"),
    ) if condition)
    complete_comparison = frame["calendar_period_ended"] and not unknown and not conflicts
    return {
        "period_start_date": frame["period_start_date"],
        "period_end_exclusive_date": frame["period_end_exclusive_date"],
        "comparison_through_date": max(days).isoformat() if days else None,
        "calendar_period_ended": frame["calendar_period_ended"],
        "status": flags[0] if flags else "DATES_MATCH_UNVERIFIED",
        "flags": flags, "calendar_date_count": len(days),
        "unknown_calendar_dates": sorted(day.isoformat() for day in unknown),
        "declared_open_dates": sorted(day.isoformat() for day in opens),
        "declared_closed_dates": sorted(day.isoformat() for day in closed),
        "declared_open_date_count": len(opens), "observed_open_date_count": len(matches),
        "missing_open_dates": sorted(day.isoformat() for day in missing),
        "suspended_open_dates": sorted(day.isoformat() for day in halted),
        "observed_on_declared_closed_dates": sorted(day.isoformat() for day in conflicts),
        "observed_open_date_coverage_percent": (
            round(100 * len(matches) / len(opens), 4) if complete_comparison and opens else None),
        "calendar_verified": False, "session_completeness_verified": False,
        "scoring_authorized": False,
    }


def calendar_coverage_diagnostics(bars: tuple[Bar, ...], sessions: tuple[TradingSession, ...],
                                 *, market: Market, as_of: datetime,
                                 include_yearly: bool = False) -> dict[str, Any]:
    """All percentages are conditional on supplied declarations, not independent quality."""
    if not isinstance(market, Market):
        raise ValueError("calendar coverage requires an explicit market")
    parent = calendar_period_diagnostics(bars, market=market, as_of=as_of,
                                         include_yearly=include_yearly)
    selected = _calendar_versions(sessions, market, as_of)
    zone = ZoneInfo(parent["market_timezone"])
    observed = {row.timestamp.astimezone(zone).date() for row in bars}
    suspended = {row["observed_at"].astimezone(zone).date()
                 for row in parent["suspension_observations"]}
    content = [asdict(row) for row in sessions]
    content.sort(key=financial_input_json)
    document: dict[str, Any] = {
        "model_version": CALENDAR_COVERAGE_VERSION, "subject": parent["subject"],
        "market": market.value, "as_of": as_of.astimezone(UTC),
        "market_timezone": parent["market_timezone"],
        "calendar_period_input_hash": parent["input_hash"],
        "calendar_rows_hash": sha256(financial_input_json(content).encode()).hexdigest(),
        "supplied_calendar_row_count": len(sessions),
        "selected_calendar_date_count": len(selected),
        "calendar_sources": sorted({row.source for row in sessions}),
        "latest_calendar_available_at": max((row.available_at for row in sessions),
            key=lambda item: item.astimezone(UTC)) if sessions else None,
        "future_schedule_dates": sorted(day.isoformat() for day in selected
                                        if day > as_of.astimezone(zone).date()),
        "calendar_trust_level": DataTrustLevel.UNKNOWN.value,
        "calendar_availability_precision": AvailabilityPrecision.UNKNOWN.value,
        "calendar_scope": "MARKET_ONLY_EXCHANGE_UNVERIFIED",
        "status": ("SUSPENDED_LATEST" if parent["status"] == "SUSPENDED_LATEST" else
                   "MISSING_PRICES" if not bars else "OBSERVED_UNQUALIFIED"),
        "weekly": [_compare(frame, selected, observed, suspended, as_of.astimezone(zone).date())
                   for frame in parent["weekly"]],
        "monthly": [_compare(frame, selected, observed, suspended, as_of.astimezone(zone).date())
                    for frame in parent["monthly"]],
        "suspension_observations": parent["suspension_observations"],
        "calendar_verified": False, "session_completeness_verified": False,
        "source_adjustment_basis_verified": False, "scoring_authorized": False,
        "historical_replay_eligible": False, "validation_authorized": False,
        "execution_authorized": False,
        "limitations": (
            "TradingSession lacks exchange binding, trust and original publication precision",
            "Declared availability is checked, not independently authenticated",
            "Unknown dates include weekends and holidays; never infer them closed",
            "Percentages require an ended period and every date explicitly declared",
            "A date match or 100 percent is not verified sessions, fresh prices or PIT admission",
            "Suspension observations are present adverse evidence, not silently missing rows",
            "Pre-listing and other missing open dates need separate lifecycle interpretation",
            "Known future schedule declarations cannot complete current periods",
            "No intraday close, emergency opening, split or dividend qualification",
        ),
    }
    if include_yearly:
        document.update(model_version=CALENDAR_YEAR_COVERAGE_VERSION,
            source_bars_content_hash=sha256(financial_input_json(
                [asdict(bar) for bar in bars]).encode()).hexdigest(),
            supplied_daily_row_count=len(bars), investment_scoring_authorized=False,
            yearly=[_compare(frame, selected, observed, suspended, as_of.astimezone(zone).date())
                    for frame in parent["yearly"]])
    reject_sensitive_structure(document)
    return {**document, "input_hash": sha256(financial_input_json(document).encode()).hexdigest()}
