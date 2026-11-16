"""Observed calendar buckets never become complete exchange candles or trading approval."""

import subprocess
import sys
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from zoneinfo import ZoneInfo

import pytest

from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.domain.enums import Adjustment, AssetType, Market
from tong_quant.domain.models import Bar, Instrument
from tong_quant.research.technical.calendar_periods import calendar_period_diagnostics

AT = datetime(2026, 11, 9, 5, tzinfo=UTC)


def _bar(day, amount=10, *, market=Market.US, turnover=None):
    at = datetime.combine(date.fromisoformat(day), datetime.min.time(), tzinfo=UTC)
    value = Decimal(amount)
    return Bar(Instrument("TEST", market, "Synthetic only", currency="USD", exchange="fixture"),
        at + timedelta(hours=16), at + timedelta(hours=23), value, value + 2,
        value - 1, value + 1, Decimal(100), turnover=turnover, source="synthetic")


def _read(bars, *, at=AT, market=Market.US):
    return calendar_period_diagnostics(tuple(bars), market=market, as_of=at)


def test_calendar_week_ohlcv_is_exact_not_five_observation_return_or_coverage_claim():
    bars = (_bar("2026-11-02", 10), _bar("2026-11-04", 12), _bar("2026-11-06", 11))
    result = _read(bars)
    week = result["weekly"][0]
    assert week["period_start_date"] == "2026-11-02"
    assert week["period_end_exclusive_date"] == "2026-11-09"
    assert week["ohlcv"] == {"open": "10", "high": "14", "low": "9", "close": "12",
                             "volume": "300", "turnover": None}
    assert week["observed_date_count"] == 3
    assert week["status"] == "CALENDAR_PERIOD_ENDED_COVERAGE_UNVERIFIED"
    assert week["calendar_period_ended"] and week["expected_session_count"] is None
    assert week["session_coverage_percent"] is None and not week["scoring_authorized"]
    assert all(value is None for value in result["monthly"][0]["ohlcv"].values())
    assert result["monthly"][0]["status"] == "CALENDAR_PERIOD_NOT_ENDED"
    assert all(result[key] is False for key in ("calendar_verified", "scoring_authorized",
        "source_adjustment_basis_verified", "lifecycle_resumption_verified",
        "historical_replay_eligible", "validation_authorized", "execution_authorized"))
    assert result["source_freshness"] == "UNASSESSED"
    assert result["source_trust"] == "NOT_ASSESSED"


@pytest.mark.parametrize("known", [False, True])
def test_unknown_turnover_is_not_zero_and_exact_zero_is_preserved(known):
    bars = (_bar("2026-11-02", turnover=Decimal(0)),
            _bar("2026-11-03", turnover=Decimal(0) if known else None))
    week = _read(bars)["weekly"][0]
    assert week["ohlcv"]["turnover"] == ("0" if known else None)


def test_decimal_volume_and_turnover_aggregation_do_not_use_float_rounding():
    value = Decimal("12345678901234567890.000000000000000001")
    bars = tuple(replace(_bar(day, turnover=value), volume=value)
                 for day in ("2026-11-02", "2026-11-03"))
    candle = _read(bars)["weekly"][0]["ohlcv"]
    expected = "24691357802469135780.000000000000000002"
    assert candle["volume"] == expected and candle["turnover"] == expected


def test_missing_periods_remain_visible_without_forward_fill_or_zero_volume():
    result = _read((_bar("2026-08-03"), _bar("2026-11-02")))
    months = {row["period_start_date"]: row for row in result["monthly"]}
    for start in ("2026-09-01", "2026-10-01"):
        assert months[start]["status"] == "MISSING_PERIOD_OBSERVATIONS"
        assert months[start]["calendar_period_ended"]
        assert months[start]["observed_date_count"] == 0
        assert all(value is None for value in months[start]["ohlcv"].values())
    assert any(row["status"] == "MISSING_PERIOD_OBSERVATIONS" for row in result["weekly"])


def test_current_period_withholds_prices_until_calendar_boundary_not_assumed_friday_close():
    bars = (_bar("2026-11-02"), _bar("2026-11-06"))
    friday = _read(bars, at=datetime(2026, 11, 7, tzinfo=UTC))
    assert friday["weekly"][0]["status"] == "CALENDAR_PERIOD_NOT_ENDED"
    assert friday["weekly"][0]["ohlcv"]["close"] is None
    before = _read(bars, at=AT - timedelta(microseconds=1))
    assert not before["weekly"][0]["calendar_period_ended"]
    after = _read(bars)
    assert after["weekly"][0]["calendar_period_ended"]
    assert after["weekly"][0]["ohlcv"]["close"] == "11"
    assert after["weekly"][-1]["status"] == "MISSING_PERIOD_OBSERVATIONS"


def test_market_local_month_and_new_york_utc_date_boundaries_are_distinct():
    stamp = datetime(2026, 11, 1, 1, tzinfo=UTC)
    end = datetime(2026, 12, 1, 6, tzinfo=UTC)
    starts = []
    for market in (Market.US, Market.HONG_KONG, Market.MALAYSIA, Market.CHINA_A):
        bar = replace(_bar("2026-11-01", market=market), timestamp=stamp, available_at=stamp)
        result = _read((bar,), at=end, market=market)
        starts.append(result["monthly"][0]["period_start_date"])
    assert starts == ["2026-10-01", "2026-11-01", "2026-11-01", "2026-11-01"]


def test_dst_calendar_week_boundary_uses_market_timezone_not_fixed_utc_hours():
    end = datetime(2026, 11, 2, 5, tzinfo=UTC)
    result = _read((_bar("2026-10-26"), _bar("2026-10-30")), at=end)
    first = result["weekly"][0]
    start = datetime(2026, 10, 26, tzinfo=ZoneInfo("America/New_York")).astimezone(UTC)
    assert (first["calendar_end_at"] - start).total_seconds() == 169 * 3600
    assert first["calendar_end_at"] == end and first["calendar_period_ended"]


@pytest.mark.parametrize("day,cutoff,start,end", [
    ("2024-02-29", datetime(2024, 3, 1, 5, tzinfo=UTC), "2024-02-01", "2024-03-01"),
    ("2026-12-31", datetime(2027, 1, 4, 5, tzinfo=UTC), "2026-12-01", "2027-01-01"),
])
def test_leap_and_year_end_months_use_calendar_dates(day, cutoff, start, end):
    result = _read((_bar(day),), at=cutoff)
    first = result["monthly"][0]
    assert (first["period_start_date"], first["period_end_exclusive_date"]) == (start, end)
    assert first["calendar_period_ended"] and first["ohlcv"]["volume"] == "100"


def test_suspensions_are_not_deleted_or_replaced_with_an_older_active_close():
    halted = replace(_bar("2026-11-03"), is_suspended=True,
        open=Decimal(0), high=Decimal(0), low=Decimal(0), close=Decimal(0), volume=Decimal(0))
    result = _read((_bar("2026-11-02"), halted))
    assert result["status"] == "SUSPENDED_LATEST"
    assert result["weekly"] == result["monthly"] == []
    assert result["selected_observation_count"] == 2 and result["suspension_observations"]
    later = _read((_bar("2026-11-02"), halted, _bar("2026-11-09")),
                  at=datetime(2026, 11, 16, 5, tzinfo=UTC))
    assert later["weekly"][0]["status"] == "SUSPENSION_OBSERVED_IN_PERIOD"
    assert later["weekly"][0]["ohlcv"]["close"] is None
    assert later["weekly"][1]["ohlcv"]["close"] == "11"
    assert not later["lifecycle_resumption_verified"]


def test_versions_select_latest_visible_without_inflating_observed_count():
    bar = _bar("2026-11-02")
    revised = replace(bar, close=Decimal("11.5"),
                      available_at=bar.available_at + timedelta(hours=1))
    result = _read((bar, bar, revised))
    assert result["supplied_row_count"] == 3 and result["selected_observation_count"] == 1
    assert result["weekly"][0]["observed_date_count"] == 1
    assert result["weekly"][0]["ohlcv"]["close"] == "11.5"
    conflict = replace(revised, close=Decimal("11.7"))
    with pytest.raises(ValueError, match="conflicting"):
        _read((bar, revised, conflict))


def test_same_market_local_date_on_two_utc_dates_is_not_a_daily_series():
    first = replace(_bar("2026-11-01"),
        timestamp=datetime(2026, 11, 1, 23, 30, tzinfo=UTC),
        available_at=datetime(2026, 11, 2, 2, tzinfo=UTC))
    second = replace(first, timestamp=datetime(2026, 11, 2, 0, 30, tzinfo=UTC))
    with pytest.raises(ValueError, match="market-local date"):
        _read((first, second))


@pytest.mark.parametrize("defect", ["future", "future_available", "future_ingested", "adjusted",
    "market", "asset", "currency", "exchange", "source", "precision", "secret"])
def test_bad_daily_inputs_cannot_be_hidden_by_a_period_bucket(defect):
    bar = _bar("2026-11-03")
    if defect == "future":
        bar = replace(bar, timestamp=AT + timedelta(days=1), available_at=AT + timedelta(days=1))
    elif defect == "future_available":
        bar = replace(bar, available_at=AT + timedelta(microseconds=1))
    elif defect == "future_ingested":
        bar = replace(bar, ingested_at=AT + timedelta(microseconds=1))
    elif defect == "adjusted":
        bar = replace(bar, adjustment=Adjustment.FORWARD)
    elif defect in {"market", "asset", "currency", "exchange"}:
        bar = replace(bar, instrument=replace(bar.instrument, **{
            "market": {"market": Market.HONG_KONG}, "asset": {"asset_type": AssetType.ETF},
            "currency": {"currency": "CNY"}, "exchange": {"exchange": "other"}}[defect]))
    elif defect == "source":
        bar = replace(bar, source="other source")
    elif defect == "precision":
        bar = replace(bar, volume=Decimal("1e25"))
    else:
        bar = replace(bar, source="token=synthetic-forbidden")
    with pytest.raises(ValueError):
        _read((_bar("2026-11-02"), bar))


def test_empty_input_and_equivalent_timezones_preserve_deterministic_diagnostic_hashes():
    empty = _read(())
    assert empty["status"] == "MISSING" and empty["weekly"] == empty["monthly"] == []
    bars = (_bar("2026-11-02"), _bar("2026-11-06"))
    first = _read(bars)
    assert first == _read(tuple(reversed(bars)))
    assert first == _read(bars, at=AT.astimezone(ZoneInfo("Asia/Kuala_Lumpur")))
    digest = first.pop("input_hash")
    assert digest == sha256(financial_input_json(first).encode()).hexdigest()


def test_calendar_capture_combination_is_rejected_before_filesystem_access(tmp_path):
    result = subprocess.run([sys.executable, "scripts/inspect_global_technical.py", "--database",
        str(tmp_path / "absent.sqlite3"), "--artifact-root", str(tmp_path / "raw"),
        "--market", "us", "--symbol", "TEST", "--capture", "--calendar-periods"],
        capture_output=True, text=True)
    assert result.returncode == 2 and "read-only" in result.stderr and not result.stdout
    assert not (tmp_path / "absent.sqlite3").exists()
