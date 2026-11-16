"""Calendar declaration agreement is not exchange/PIT or strategy qualification."""

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from zoneinfo import ZoneInfo

import pytest

from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.domain.enums import Market
from tong_quant.domain.models import Bar, Instrument, TradingSession
from tong_quant.research.technical.calendar_coverage import calendar_coverage_diagnostics
from tong_quant.research.technical.calendar_periods import calendar_period_diagnostics

AT = datetime(2026, 11, 9, 5, tzinfo=UTC)
KNOWN = AT - timedelta(days=14)


def _bars(*, market=Market.US):
    instrument = Instrument("TEST", market, "Synthetic", currency="USD", exchange="fixture")
    hour = 16 if market is Market.US else 8
    return tuple(Bar(instrument, datetime(2026, 11, day, hour, tzinfo=UTC),
        datetime(2026, 11, day, 23, tzinfo=UTC), Decimal(10), Decimal(12), Decimal(9),
        Decimal(11), Decimal(100), source="synthetic-only") for day in range(2, 7))


def _sessions(*, market=Market.US):
    return tuple(TradingSession(market, date(2026, 11, day), day < 7, KNOWN,
                                "synthetic-only-calendar") for day in range(2, 9))


def _read(bars=None, sessions=None, *, market=Market.US, at=AT):
    return calendar_coverage_diagnostics(_bars(market=market) if bars is None else bars,
        _sessions(market=market) if sessions is None else sessions, market=market, as_of=at)


@pytest.mark.parametrize("market", [Market.CHINA_A, Market.US, Market.HONG_KONG, Market.MALAYSIA])
def test_full_declared_calendar_matches_dates_but_never_authorizes_a_score(market):
    bars = _bars(market=market)
    result = _read(market=market)
    week = result["weekly"][0]
    assert week["status"] == "DATES_MATCH_UNVERIFIED"
    assert week["observed_open_date_coverage_percent"] == 100
    assert week["declared_open_date_count"] == week["observed_open_date_count"] == 5
    assert week["unknown_calendar_dates"] == week["missing_open_dates"] == []
    assert week["declared_closed_dates"] == ["2026-11-07", "2026-11-08"]
    assert result["calendar_period_input_hash"] == calendar_period_diagnostics(
        bars, market=market, as_of=AT)["input_hash"]
    assert result["calendar_scope"] == "MARKET_ONLY_EXCHANGE_UNVERIFIED"
    assert result["calendar_trust_level"] == result["calendar_availability_precision"] == "unknown"
    for item in (result, week):
        for key in ("calendar_verified", "session_completeness_verified", "scoring_authorized"):
            assert item[key] is False
    for key in ("source_adjustment_basis_verified", "historical_replay_eligible",
                "validation_authorized", "execution_authorized"):
        assert result[key] is False


def test_absent_weekend_declarations_are_unknown_not_automatically_closed():
    week = _read(sessions=_sessions()[:5])["weekly"][0]
    assert week["status"] == "CALENDAR_DATES_MISSING"
    assert week["unknown_calendar_dates"] == ["2026-11-07", "2026-11-08"]
    assert week["observed_open_date_coverage_percent"] is None
    assert week["declared_closed_dates"] == []


def test_asian_market_local_date_is_not_silently_replaced_with_utc_date():
    bars = tuple(replace(row, timestamp=row.timestamp + timedelta(hours=8))
                 for row in _bars(market=Market.MALAYSIA))
    week = _read(bars=bars, market=Market.MALAYSIA)["weekly"][0]
    assert week["missing_open_dates"] == ["2026-11-02"]
    assert week["observed_on_declared_closed_dates"] == ["2026-11-07"]
    assert week["observed_open_date_coverage_percent"] is None


def test_missing_calendar_is_distinct_from_missing_bar_on_a_declared_open_date():
    absent_calendar = _read(sessions=())["weekly"][0]
    assert len(absent_calendar["unknown_calendar_dates"]) == 7
    assert absent_calendar["declared_open_date_count"] == 0
    assert absent_calendar["missing_open_dates"] == []
    missing = _read(bars=_bars()[:3] + _bars()[4:])["weekly"][0]
    assert missing["status"] == "OPEN_DATE_OBSERVATIONS_MISSING"
    assert missing["missing_open_dates"] == ["2026-11-05"]
    assert missing["observed_open_date_coverage_percent"] == 80


def test_declared_closed_conflict_remains_visible_even_with_other_unknown_dates():
    sessions = (replace(_sessions()[0], is_open=False), *_sessions()[1:5])
    week = _read(sessions=sessions)["weekly"][0]
    assert week["status"] == "OBSERVATION_CALENDAR_CONFLICT"
    assert week["observed_on_declared_closed_dates"] == ["2026-11-02"]
    assert week["unknown_calendar_dates"] and "CALENDAR_DATES_MISSING" in week["flags"]
    assert week["observed_open_date_coverage_percent"] is None


def test_suspended_observation_is_preserved_not_falsely_counted_as_missing():
    bars = _bars()
    halted = replace(bars[2], is_suspended=True, open=Decimal(0), high=Decimal(0),
                     low=Decimal(0), close=Decimal(0), volume=Decimal(0))
    result = _read(bars=(*bars[:2], halted, *bars[3:]))
    week = result["weekly"][0]
    assert week["status"] == "SUSPENSION_OBSERVATIONS_PRESENT"
    assert week["suspended_open_dates"] == ["2026-11-04"]
    assert week["missing_open_dates"] == []
    assert week["observed_open_date_coverage_percent"] == 100
    assert result["suspension_observations"]
    latest = _read(bars=(*bars[:2], halted))
    assert latest["status"] == "SUSPENDED_LATEST"
    assert latest["weekly"] == latest["monthly"] == []
    assert latest["suspension_observations"]


def test_current_period_never_gets_coverage_percent_even_with_known_future_schedule():
    at = datetime(2026, 11, 7, tzinfo=UTC)
    result = _read(at=at)
    week = result["weekly"][0]
    assert "PERIOD_NOT_ENDED" in week["flags"]
    assert week["comparison_through_date"] == "2026-11-06"
    assert week["calendar_date_count"] == 5
    assert week["observed_open_date_coverage_percent"] is None
    assert result["future_schedule_dates"] == ["2026-11-07", "2026-11-08"]


def test_zero_declared_open_dates_does_not_manufacture_one_hundred_percent():
    # Calendar itself can conflict with observed prices; neither side is silently preferred.
    week = _read(sessions=tuple(replace(row, is_open=False) for row in _sessions()))["weekly"][0]
    assert "NO_OPEN_DATES_DECLARED" in week["flags"]
    assert week["observed_open_date_coverage_percent"] is None
    assert len(week["observed_on_declared_closed_dates"]) == 5


def test_missing_price_inputs_stay_missing_even_with_a_calendar():
    result = _read(bars=())
    assert result["status"] == "MISSING_PRICES"
    assert result["weekly"] == result["monthly"] == []
    assert result["supplied_calendar_row_count"] == 7


def test_latest_visible_calendar_revision_is_used_but_all_rows_bind_the_hash():
    sessions = _sessions()
    revision = replace(sessions[0], is_open=False, available_at=KNOWN + timedelta(hours=1))
    result = _read(sessions=(*sessions, revision))
    assert result["supplied_calendar_row_count"] == 8
    assert result["selected_calendar_date_count"] == 7
    assert result["latest_calendar_available_at"] == revision.available_at
    assert result["weekly"][0]["observed_on_declared_closed_dates"] == ["2026-11-02"]
    assert result["input_hash"] != _read(sessions=(revision, *sessions[1:]))["input_hash"]
    assert result == _read(sessions=tuple(reversed((*sessions, revision))))


def test_actual_utc_fold_selects_the_later_calendar_version_not_equal_wall_clock():
    zone = ZoneInfo("America/New_York")
    earlier = datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=0)
    later = earlier.replace(fold=1)
    sessions = _sessions()
    first = replace(sessions[0], available_at=earlier)
    revision = replace(first, is_open=False, available_at=later)
    result = _read(sessions=(revision, *sessions[1:], first))
    assert result["weekly"][0]["observed_on_declared_closed_dates"] == ["2026-11-02"]
    assert result["latest_calendar_available_at"].astimezone(UTC) == later.astimezone(UTC)


YEAR_AT = datetime(2025, 1, 2, 12, tzinfo=UTC)


def _year_bars(market=Market.US):
    instrument = Instrument("TEST", market, "Synthetic", currency="USD", exchange="fixture")
    return tuple(Bar(instrument, datetime(2024, month, day, 16 if market is Market.US else 8,
        tzinfo=UTC), datetime(2024, month, day, 23, tzinfo=UTC), Decimal(10), Decimal(12),
        Decimal(9), Decimal(11), Decimal(100), source="synthetic")
        for month, day in ((2, 29), (12, 31)))


def _year_sessions(market=Market.US):
    # All dates are explicit synthetic declarations, not a production weekday calendar.
    start = date(2024, 1, 1)
    return tuple(TradingSession(market, start + timedelta(days=i),
        start + timedelta(days=i) in {date(2024, 2, 29), date(2024, 12, 31)},
        datetime(2023, 1, 1, tzinfo=UTC), "synthetic-year-calendar") for i in range(366))


def test_yearly_coverage_counts_leap_year_dates_and_never_promotes_full_agreement():
    result = calendar_coverage_diagnostics(_year_bars(), _year_sessions(), market=Market.US,
                                          as_of=YEAR_AT, include_yearly=True)
    year = result["yearly"][0]
    assert year["calendar_date_count"] == 366
    assert year["status"] == "DATES_MATCH_UNVERIFIED"
    assert year["observed_open_date_coverage_percent"] == 100
    assert year["declared_open_date_count"] == year["observed_open_date_count"] == 2
    assert result["calendar_period_input_hash"] == calendar_period_diagnostics(
        _year_bars(), market=Market.US, as_of=YEAR_AT, include_yearly=True)["input_hash"]
    assert result["calendar_trust_level"] == "unknown"
    assert result["investment_scoring_authorized"] is result["calendar_verified"] is False
    assert result["yearly"][-1]["observed_open_date_coverage_percent"] is None


def test_default_coverage_is_unchanged_without_yearly_opt_in():
    default = calendar_coverage_diagnostics(_year_bars(), (), market=Market.US, as_of=YEAR_AT)
    explicit = calendar_coverage_diagnostics(_year_bars(), (), market=Market.US,
                                            as_of=YEAR_AT, include_yearly=False)
    assert default == explicit and "yearly" not in default
    assert "source_bars_content_hash" not in default


@pytest.mark.parametrize("kind", ["no_calendar", "missing_declaration", "missing_observation",
                                  "closed_conflict", "suspension"])
def test_annual_coverage_preserves_distinct_gaps_and_adverse_observations(kind):
    bars, sessions = _year_bars(), _year_sessions()
    if kind == "no_calendar":
        sessions = ()
    elif kind == "missing_declaration":
        sessions = tuple(row for row in sessions if row.trade_date != date(2024, 2, 29))
    elif kind == "missing_observation":
        bars = bars[1:]
    elif kind == "closed_conflict":
        sessions = tuple(replace(row, is_open=False) if row.trade_date == date(2024, 2, 29)
                         else row for row in sessions)
    else:
        bars = (replace(bars[0], is_suspended=True, open=Decimal(0), close=Decimal(0),
                        high=Decimal(0), low=Decimal(0), volume=Decimal(0)), bars[1])
    year = calendar_coverage_diagnostics(bars, sessions, market=Market.US,
                                        as_of=YEAR_AT, include_yearly=True)["yearly"][0]
    if kind == "no_calendar":
        assert len(year["unknown_calendar_dates"]) == 366
        assert year["observed_open_date_coverage_percent"] is None
    elif kind == "missing_declaration":
        assert year["unknown_calendar_dates"] == ["2024-02-29"]
        assert year["observed_open_date_coverage_percent"] is None
    elif kind == "missing_observation":
        assert year["missing_open_dates"] == ["2024-02-29"]
        assert year["observed_open_date_coverage_percent"] == 50
    elif kind == "closed_conflict":
        assert year["observed_on_declared_closed_dates"] == ["2024-02-29"]
        assert year["observed_open_date_coverage_percent"] is None
    else:
        assert year["suspended_open_dates"] == ["2024-02-29"]
        assert year["missing_open_dates"] == []
        assert year["observed_open_date_coverage_percent"] == 100
    assert year["calendar_verified"] is year["session_completeness_verified"] is False


@pytest.mark.parametrize("market,ended", [(Market.US, False), (Market.CHINA_A, True),
    (Market.HONG_KONG, True), (Market.MALAYSIA, True)])
def test_year_coverage_uses_local_boundary_not_utc_or_last_observation(market, ended):
    result = calendar_coverage_diagnostics(_year_bars(market), _year_sessions(market),
        market=market, as_of=datetime(2025, 1, 1, 1, tzinfo=UTC), include_yearly=True)
    year = result["yearly"][0]
    assert year["calendar_period_ended"] is ended
    assert year["observed_open_date_coverage_percent"] == (100 if ended else None)


def test_future_calendar_versions_are_rejected_even_for_a_past_year():
    sessions = _year_sessions()
    future = replace(sessions[0], available_at=YEAR_AT + timedelta(microseconds=1))
    with pytest.raises(ValueError, match="future"):
        calendar_coverage_diagnostics(_year_bars(), (future, *sessions[1:]), market=Market.US,
                                      as_of=YEAR_AT, include_yearly=True)


def test_equivalent_timezone_and_order_produce_the_same_full_receipt():
    result = _read()
    assert result == _read(bars=tuple(reversed(_bars())), sessions=tuple(reversed(_sessions())),
                           at=AT.astimezone(ZoneInfo("Asia/Kuala_Lumpur")))
    digest = result.pop("input_hash")
    assert digest == sha256(financial_input_json(result).encode()).hexdigest()


@pytest.mark.parametrize("defect", ["market", "datetime_date", "bool", "empty_source",
                                    "future", "naive", "secret", "mixed_source", "conflict"])
def test_invalid_calendar_inputs_fail_closed_without_favorable_fallback(defect):
    sessions = _sessions()
    first = sessions[0]
    if defect == "market":
        first = replace(first, market=Market.CHINA_A)
    elif defect == "datetime_date":
        first = replace(first, trade_date=AT)
    elif defect == "bool":
        first = replace(first, is_open=1)
    elif defect == "empty_source":
        first = replace(first, source=" ")
    elif defect == "future":
        first = replace(first, available_at=AT + timedelta(microseconds=1))
    elif defect == "naive":
        # Mutable-boundary corruption must be revalidated, not just dataclass construction.
        object.__setattr__(first, "available_at", KNOWN.replace(tzinfo=None))
    elif defect == "secret":
        sessions = tuple(replace(row, source="token=synthetic-forbidden") for row in sessions)
        first = sessions[0]
    elif defect == "mixed_source":
        first = replace(first, source="different")
    else:
        sessions = (*sessions, replace(first, is_open=False))
    with pytest.raises(ValueError):
        _read(sessions=(first, *sessions[1:]))


@pytest.mark.parametrize("bad", [[], (None,), _sessions() * 3000])
def test_invalid_or_oversized_calendar_container_is_rejected(bad):
    with pytest.raises(ValueError):
        _read(sessions=bad)
