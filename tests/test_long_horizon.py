"""Sparse synthetic observations exercise arithmetic, never session completeness."""

from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from zoneinfo import ZoneInfo

import pytest

from tong_quant.application.equity_note import render_equity_note
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.global_price_inputs import GlobalPriceInputs
from tong_quant.domain.enums import Adjustment, Market
from tong_quant.domain.models import Bar, Instrument
from tong_quant.research.technical.calendar_periods import calendar_period_diagnostics
from tong_quant.research.technical.diagnostics import technical_diagnostics
from tong_quant.research.technical.indicators import TechnicalParameters, kdj, macd, sma
from tong_quant.research.technical.long_horizon import (
    LongHorizonParameters,
    long_horizon_diagnostics,
)
from tong_quant.version import (
    CALENDAR_PERIOD_DIAGNOSTICS_VERSION,
    CALENDAR_YEAR_DIAGNOSTICS_VERSION,
)

AT = datetime(2026, 1, 1, 5, tzinfo=UTC)


def _bars():
    instrument = Instrument("TEST", Market.US, "Synthetic", currency="USD", exchange="fixture")
    result = []
    for index in range(48):
        stamp = datetime(2022 + index // 12, index % 12 + 1, 15, 16, tzinfo=UTC)
        close = Decimal(100 + index)
        result.append(Bar(instrument, stamp, stamp + timedelta(hours=7), close - 1,
                          close + 2, close - 2, close, Decimal(100), source="synthetic"))
    return tuple(result)


def _read(bars=None, **kwargs):
    return long_horizon_diagnostics(_bars() if bars is None else bars,
                                    market=Market.US, as_of=kwargs.pop("as_of", AT), **kwargs)


def test_ended_months_reuse_existing_formulas_and_years_keep_insufficient_history():
    result = _read()
    assert result == _read()
    monthly, yearly = result["monthly"], result["yearly"]
    assert monthly["calculation_period_count"] == 48
    assert yearly["calculation_period_count"] == 4
    assert monthly["last_ended_period_start"] == "2025-12-01"
    assert yearly["last_ended_period_start"] == "2025-01-01"
    values = tuple(float(bar.close) for bar in _bars())
    assert monthly["macd"]["values"] == asdict(macd(values, TechnicalParameters()))
    assert monthly["kdj"]["values"] == asdict(kdj(_bars(), TechnicalParameters()))
    assert monthly["moving_averages"][0]["value"] == sma(values, 6)[-1]
    assert yearly["macd"]["required_periods"] == 35
    assert yearly["macd"]["available_periods"] == 4
    assert yearly["macd"]["status"] == "INSUFFICIENT_HISTORY"
    assert yearly["macd"]["values"] is None
    assert yearly["kdj"]["status"] == "INSUFFICIENT_HISTORY"
    assert yearly["moving_averages"][0]["value"] is not None
    assert yearly["moving_averages"][1]["value"] is None
    assert result["cross_timeframe_decision"] == "NOT_EVALUATED"
    assert result["holding_horizon"] == "NOT_ESTIMATED"
    assert all(value is False for key, value in result.items()
               if key.endswith("_authorized") or key.endswith("_verified")
               or key == "historical_replay_eligible")
    assert monthly["session_coverage"] == yearly["session_coverage"] == "UNVERIFIED"
    body = {key: value for key, value in result.items() if key != "input_hash"}
    assert result["input_hash"] == sha256(financial_input_json(body).encode()).hexdigest()


def test_optional_years_preserve_legacy_calendar_receipt_when_disabled():
    baseline = calendar_period_diagnostics(_bars(), market=Market.US, as_of=AT)
    explicit = calendar_period_diagnostics(_bars(), market=Market.US, as_of=AT,
                                           include_yearly=False)
    enabled = calendar_period_diagnostics(_bars(), market=Market.US, as_of=AT, include_yearly=True)
    assert baseline == explicit and "yearly" not in baseline
    assert baseline["model_version"] == CALENDAR_PERIOD_DIAGNOSTICS_VERSION
    assert enabled["model_version"] == CALENDAR_YEAR_DIAGNOSTICS_VERSION
    assert baseline["weekly"] == enabled["weekly"]
    assert baseline["monthly"] == enabled["monthly"]


@pytest.mark.parametrize("market,year", [(Market.US, "2025"), (Market.CHINA_A, "2026"),
    (Market.HONG_KONG, "2026"), (Market.MALAYSIA, "2026")])
def test_year_buckets_follow_market_timezone_not_utc_year(market, year):
    stamp = datetime(2026, 1, 1, 0, 30, tzinfo=UTC)
    original = _bars()[0]
    bar = replace(original, instrument=replace(original.instrument, market=market),
                  timestamp=stamp, available_at=stamp)
    result = calendar_period_diagnostics((bar,), market=market,
        as_of=stamp + timedelta(days=1), include_yearly=True)
    assert result["yearly"][0]["period_start_date"] == f"{year}-01-01"


def test_year_is_not_ended_until_exact_local_calendar_boundary():
    before = _read(as_of=AT - timedelta(microseconds=1))["yearly"]
    after = _read()["yearly"]
    assert before["last_ended_period_start"] == "2024-01-01"
    assert before["calculation_period_count"] == 3
    assert after["last_ended_period_start"] == "2025-01-01"
    assert after["calculation_period_count"] == 4


def test_open_month_and_year_do_not_enter_indicators_even_with_extreme_prices():
    cutoff = datetime(2026, 1, 20, tzinfo=UTC)
    original = _bars()[-1]
    current = replace(original, timestamp=datetime(2026, 1, 15, 16, tzinfo=UTC),
                      available_at=datetime(2026, 1, 15, 23, tzinfo=UTC))
    high = replace(current, open=Decimal(999999), close=Decimal(999999),
                   high=Decimal(1000000), low=Decimal(999998))
    left = _read((*_bars(), current), as_of=cutoff)
    right = _read((*_bars(), high), as_of=cutoff)
    for frequency in ("monthly", "yearly"):
        for key in ("macd", "kdj", "moving_averages", "last_ended_close"):
            assert left[frequency][key] == right[frequency][key]
        assert left[frequency]["open_period_starts"]
    assert left["input_hash"] != right["input_hash"]


@pytest.mark.parametrize("missing", ["middle_month", "last_month", "whole_year"])
def test_ended_gaps_block_without_stitching_or_favorable_fallback(missing):
    bars = _bars()
    bars = tuple(bar for index, bar in enumerate(bars) if (
        index != 20 if missing == "middle_month" else index != 47 if missing == "last_month"
        else bar.timestamp.year != 2023))
    result = _read(bars)
    for frequency in ("monthly", "yearly"):
        item = result[frequency]
        assert item["status"] == "BLOCKED_PERIOD_GAPS_OR_SUSPENSIONS"
        assert item["blocking_period_starts"] and item["calculation_period_count"] == 0
        assert item["last_ended_close"] is None
        assert item["macd"]["values"] is None
        assert all(average["value"] is None for average in item["moving_averages"])


def test_known_leading_month_truncation_does_not_become_a_complete_year():
    result = _read(_bars()[6:])
    assert result["monthly"]["status"] == "OBSERVED_UNQUALIFIED"
    assert result["yearly"]["status"] == "BLOCKED_PERIOD_GAPS_OR_SUSPENSIONS"
    assert len(result["yearly"]["periods"][0]["underlying_month_gap_starts"]) == 6


@pytest.mark.parametrize("latest", [False, True])
def test_suspensions_remain_visible_and_cannot_resurrect_previous_active_values(latest):
    bars = list(_bars())
    index = -1 if latest else 20
    bars[index] = replace(bars[index], open=Decimal(0), high=Decimal(0), low=Decimal(0),
                          close=Decimal(0), volume=Decimal(0), is_suspended=True)
    result = _read(tuple(bars))
    for frequency in ("monthly", "yearly"):
        assert result[frequency]["status"] == (
            "SUSPENDED_LATEST" if latest else "BLOCKED_PERIOD_GAPS_OR_SUSPENSIONS")
        assert result[frequency]["last_ended_close"] is None
        assert result[frequency]["macd"]["values"] is None


def test_duplicate_rows_do_not_inflate_monthly_warmup_and_conflicts_reject():
    bars = _bars()
    result = _read((*bars, bars[0]))
    assert result["monthly"]["calculation_period_count"] == 48
    assert result["monthly"]["macd"] == _read()["monthly"]["macd"]
    conflict = replace(bars[0], close=bars[0].close + Decimal(1))
    with pytest.raises(ValueError, match="conflicting"):
        _read((*bars, conflict))


def test_future_fold_availability_rejects_and_equivalent_cutoff_labels_match():
    zone = ZoneInfo("America/New_York")
    cutoff = datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=0)
    future = cutoff.replace(fold=1)
    bars = _bars()
    with pytest.raises(ValueError, match="future"):
        _read((*bars[:-1], replace(bars[-1], available_at=future)), as_of=cutoff)
    assert _read() == _read(as_of=AT.astimezone(ZoneInfo("Asia/Kuala_Lumpur")))


def test_adjusted_and_wrong_market_inputs_cannot_enter_long_horizon_calculations():
    bars = _bars()
    with pytest.raises(ValueError, match="unadjusted"):
        _read((replace(bars[0], adjustment=Adjustment.FORWARD),))
    with pytest.raises(ValueError, match="scope"):
        _read((replace(bars[0], instrument=replace(bars[0].instrument, market=Market.CHINA_A)),))


def test_missing_history_remains_missing_with_no_indicator_values():
    result = _read(())
    assert result["status"] == "MISSING"
    for frequency in ("monthly", "yearly"):
        assert result[frequency]["status"] == "MISSING"
        assert result[frequency]["calculation_period_count"] == 0
        assert result[frequency]["kdj"]["values"] is None


@pytest.mark.parametrize("periods", [(), [], (True,), (0,), (1, 1), (1001,)])
def test_invalid_average_parameters_fail_closed(periods):
    with pytest.raises(ValueError):
        LongHorizonParameters(monthly_sma_periods=periods)


@pytest.mark.parametrize("flag", [0, 1, None, "yes"])
def test_year_opt_in_does_not_coerce_non_boolean_values(flag):
    with pytest.raises(ValueError, match="boolean"):
        calendar_period_diagnostics(_bars(), market=Market.US, as_of=AT, include_yearly=flag)


@pytest.mark.parametrize("market", list((Market.US, Market.CHINA_A, Market.HONG_KONG,
                                       Market.MALAYSIA)))
def test_long_horizon_arithmetic_has_no_a_share_specific_rules(market):
    bars = tuple(replace(bar, instrument=replace(bar.instrument, market=market)) for bar in _bars())
    result = long_horizon_diagnostics(bars, market=market, as_of=AT)
    assert result["market"] == market.value
    assert result["monthly"]["calculation_period_count"] == 48
    assert result["monthly"]["macd"]["status"] == "OBSERVED_UNQUALIFIED"
    assert result["execution_authorized"] is False


def _note_document():
    bars = _bars()
    inputs = GlobalPriceInputs("TEST", Market.US, AT, "observed_unqualified", bars, (),
                               None, "UNASSESSED", None, None)
    return {"inputs": inputs.document(), "diagnostics": technical_diagnostics(
        bars, TechnicalParameters(), as_of=AT), "research_only": True,
        "research_report_created": False, "readiness_promoted": False, "long_horizon": _read()}


def test_long_horizon_note_displays_sample_units_and_preserves_default_view_version():
    document = _note_document()
    note = render_equity_note(document)
    assert "月线与年线观察" in note and "35个年度观察" in note
    assert "INSUFFICIENT_HISTORY" in note and "v3-long-horizon" in note
    assert "dif=" in note and "不据此估计持有年限" in note
    assert note == render_equity_note(document)
    del document["long_horizon"]
    default = render_equity_note(document)
    assert "月线与年线观察" not in default and "v2-utc-context" in default


@pytest.mark.parametrize("field,value", [
    ("subject", "OTHER"), ("market", "china_a"), ("as_of", AT - timedelta(seconds=1)),
    ("source_bars_content_hash", "f" * 64), ("supplied_daily_row_count", 999),
    ("model_version", "old"), ("calendar_verified", True), ("execution_authorized", True),
    ("scoring_authorized", True),
])
def test_long_horizon_renderer_rejects_rehashed_wrong_context_or_authority(field, value):
    document = _note_document()
    receipt = document["long_horizon"]
    receipt[field] = value
    receipt["input_hash"] = sha256(financial_input_json({
        key: item for key, item in receipt.items() if key != "input_hash"}).encode()).hexdigest()
    with pytest.raises(ValueError):
        render_equity_note(document)


WEEK_AT = datetime(2026, 1, 5, 5, tzinfo=UTC)


def _weekly_history():
    original = _bars()[0]
    result = []
    for index in range(104):
        stamp = datetime(2024, 1, 8, 16, tzinfo=UTC) + timedelta(weeks=index)
        value = Decimal(100 + index)
        result.append(replace(original, timestamp=stamp, available_at=stamp + timedelta(hours=7),
            open=value - 1, high=value + 2, low=value - 2, close=value))
    return tuple(result)


def _multi(bars=None, **kwargs):
    return long_horizon_diagnostics(_weekly_history() if bars is None else bars,
        market=Market.US, as_of=kwargs.pop("as_of", WEEK_AT), weekly_sma_periods=(13, 26, 52),
        **kwargs)


def test_weekly_opt_in_reuses_formulas_without_changing_v1_month_year_receipt():
    bars = _weekly_history()
    old = long_horizon_diagnostics(bars, market=Market.US, as_of=WEEK_AT)
    assert old == long_horizon_diagnostics(bars, market=Market.US, as_of=WEEK_AT,
                                         weekly_sma_periods=None)
    new = _multi()
    assert new["monthly"] == old["monthly"] and new["yearly"] == old["yearly"]
    assert "weekly" not in old and "timeframe_alignment" not in old
    week = new["weekly"]
    assert week["calculation_period_count"] == 104
    assert week["macd"]["values"] == asdict(macd(
        tuple(float(bar.close) for bar in bars), TechnicalParameters()))
    assert week["kdj"]["values"] == asdict(kdj(bars, TechnicalParameters()))
    assert week["moving_averages"][0]["periods"] == 13
    assert new == _multi()
    assert new["cross_timeframe_decision"] == "NOT_EVALUATED"
    assert new["timeframe_alignment"]["comparison_eligible"] is False
    assert new["timeframe_alignment"]["calendar_end_is_exchange_close"] is False


def test_current_week_is_excluded_and_its_new_price_changes_alignment_not_closed_indicators():
    bars = _weekly_history()
    current = replace(bars[-1], timestamp=datetime(2026, 1, 5, 16, tzinfo=UTC),
                      available_at=datetime(2026, 1, 5, 23, tzinfo=UTC))
    extreme = replace(current, open=Decimal(999998), high=Decimal(1000000),
                      low=Decimal(999997), close=Decimal(999999))
    cutoff = datetime(2026, 1, 7, tzinfo=UTC)
    original = _multi(bars, as_of=cutoff)
    result = _multi((*bars, extreme), as_of=cutoff)
    for frequency in ("weekly", "monthly", "yearly"):
        assert result[frequency]["macd"] == original[frequency]["macd"]
        assert result[frequency]["last_ended_close"] == original[frequency]["last_ended_close"]
    alignment = result["timeframe_alignment"]
    assert alignment["daily_reference_observed_at"] == current.timestamp
    weekly = alignment["periods"][0]
    assert weekly["last_ended_period_start"] == "2025-12-29"
    assert weekly["last_source_observed_at"] == bars[-1].timestamp
    assert weekly["lag_to_daily_observation_seconds"] == 7 * 86400


@pytest.mark.parametrize("index", [20, 103])
def test_weekly_missing_periods_do_not_stitch_or_fall_back_in_alignment(index):
    result = _multi(tuple(bar for i, bar in enumerate(_weekly_history()) if i != index))
    assert result["weekly"]["status"] == "BLOCKED_PERIOD_GAPS_OR_SUSPENSIONS"
    assert result["weekly"]["macd"]["values"] is None
    if index == 103:
        aligned = result["timeframe_alignment"]["periods"][0]
        assert aligned["period_status"] == "MISSING_PERIOD_OBSERVATIONS"
        assert aligned["last_source_observed_at"] is None
        assert aligned["lag_to_daily_observation_seconds"] is None


def test_weekly_calendar_boundary_remains_exact_not_friday_close():
    before = _multi(as_of=WEEK_AT - timedelta(microseconds=1))
    after = _multi()
    assert before["weekly"]["calculation_period_count"] == 103
    assert after["weekly"]["calculation_period_count"] == 104
    assert before["timeframe_alignment"]["periods"][0]["calendar_end_at"] < WEEK_AT
    assert after["timeframe_alignment"]["periods"][0]["calendar_end_at"] == WEEK_AT


@pytest.mark.parametrize("suspended", [False, True])
def test_missing_or_latest_suspended_multi_input_has_no_favorable_metadata_fallback(suspended):
    bars = _weekly_history()
    bars = (*bars[:-1], replace(bars[-1], is_suspended=True, open=Decimal(0), high=Decimal(0),
                               low=Decimal(0), close=Decimal(0), volume=Decimal(0))) if (
                                   suspended) else ()
    result = _multi(bars)
    expected = "SUSPENDED_LATEST" if suspended else "MISSING"
    assert result["weekly"]["status"] == expected
    assert all(row["period_status"] == expected for row in result["timeframe_alignment"]["periods"])
    assert all(row["last_source_observed_at"] is None
               for row in result["timeframe_alignment"]["periods"])


@pytest.mark.parametrize("periods", [(), [], (True,), (0,), (13, 13), (1001,)])
def test_weekly_average_parameters_are_explicit_and_strict(periods):
    with pytest.raises(ValueError):
        long_horizon_diagnostics(_weekly_history(), market=Market.US, as_of=WEEK_AT,
                                 weekly_sma_periods=periods)


def _multi_document():
    bars = _weekly_history()
    inputs = GlobalPriceInputs("TEST", Market.US, WEEK_AT, "observed_unqualified", bars, (),
                               None, "UNASSESSED", None, None)
    return {"inputs": inputs.document(), "diagnostics": technical_diagnostics(
        bars, TechnicalParameters(), as_of=WEEK_AT), "research_only": True,
        "research_report_created": False, "readiness_promoted": False, "long_horizon": _multi()}


def test_multi_view_reports_source_dates_and_remains_informational():
    note = render_equity_note(_multi_document())
    assert "周/月/年观察" in note and "v4-timeframe-dates" in note
    assert "同一分析截止时间不等于同一天收盘" in note
    assert "周度观察" in note and "最新日线观察" in note
    assert "不据此估计持有年限或生成补仓/卖出指令" in note


@pytest.mark.parametrize("defect", ["cutoff", "daily_date", "negative_lag", "wrong_lag",
    "duplicate_frequency", "wrong_period", "future_end", "future_available", "eligible",
    "verified_close", "version", "missing_weekly"])
def test_rehashed_multi_view_rejects_false_alignment_or_version(defect):
    document = _multi_document()
    receipt = document["long_horizon"]
    aligned = receipt["timeframe_alignment"]
    period = aligned["periods"][0]
    if defect == "cutoff":
        aligned["as_of"] = WEEK_AT + timedelta(seconds=1)
    elif defect == "daily_date":
        aligned["daily_reference_observed_at"] += timedelta(days=1)
    elif defect == "negative_lag":
        period["lag_to_daily_observation_seconds"] = -1
    elif defect == "wrong_lag":
        period["lag_to_daily_observation_seconds"] = 1
    elif defect == "duplicate_frequency":
        aligned["periods"][1]["frequency"] = "weekly"
    elif defect == "wrong_period":
        period["last_ended_period_start"] = "2020-01-01"
    elif defect in {"future_end", "future_available"}:
        period["calendar_end_at" if defect == "future_end" else "latest_source_available_at"] = (
            WEEK_AT + timedelta(seconds=1))
    elif defect == "eligible":
        aligned["comparison_eligible"] = True
    elif defect == "verified_close":
        aligned["calendar_end_is_exchange_close"] = True
    elif defect == "version":
        from tong_quant.version import LONG_HORIZON_DIAGNOSTICS_VERSION
        receipt["model_version"] = LONG_HORIZON_DIAGNOSTICS_VERSION
    else:
        del receipt["weekly"]
    receipt["input_hash"] = sha256(financial_input_json({
        key: item for key, item in receipt.items() if key != "input_hash"}).encode()).hexdigest()
    with pytest.raises(ValueError):
        render_equity_note(document)


def _annual_coverage_document():
    from tong_quant.research.technical.calendar_coverage import calendar_coverage_diagnostics
    document = _note_document()
    document["calendar_coverage"] = calendar_coverage_diagnostics(
        _bars(), (), market=Market.US, as_of=AT, include_yearly=True)
    return document


def test_long_horizon_note_shows_annual_calendar_gaps_without_qualifying_them():
    document = _annual_coverage_document()
    note = render_equity_note(document)
    assert "v5-calendar-gaps" in note and "交易日期覆盖核对" in note
    assert "CALENDAR_DATES_MISSING" in note
    assert "100%也不是" in note and "不能自动当作周末或休市" in note
    assert document["calendar_coverage"]["supplied_calendar_row_count"] == 0
    assert all(row["observed_open_date_coverage_percent"] is None
               for row in document["calendar_coverage"]["yearly"])


@pytest.mark.parametrize("key,value", [("subject", "OTHER"), ("market", "china_a"),
    ("as_of", AT + timedelta(seconds=1)), ("source_bars_content_hash", "f" * 64),
    ("supplied_daily_row_count", 999), ("calendar_period_input_hash", "e" * 64),
    ("calendar_trust_level", "high"), ("calendar_availability_precision", "exact"),
    ("calendar_verified", True), ("latest_calendar_available_at", AT + timedelta(seconds=1))])
def test_calendar_coverage_view_rejects_rehashed_mismatches_or_trust_promotions(key, value):
    document = _annual_coverage_document()
    receipt = document["calendar_coverage"]
    receipt[key] = value
    receipt["input_hash"] = sha256(financial_input_json({
        k: v for k, v in receipt.items() if k != "input_hash"}).encode()).hexdigest()
    with pytest.raises(ValueError):
        render_equity_note(document)


def test_annual_calendar_missing_prices_remain_missing_in_the_note():
    from tong_quant.research.technical.calendar_coverage import calendar_coverage_diagnostics
    inputs = GlobalPriceInputs("TEST", Market.US, AT, "missing", (), (), None,
                               "UNASSESSED", None, None)
    document = {"inputs": inputs.document(), "diagnostics": technical_diagnostics(
        (), TechnicalParameters(), as_of=AT), "research_only": True,
        "research_report_created": False, "readiness_promoted": False,
        "long_horizon": _read(()), "calendar_coverage": calendar_coverage_diagnostics(
            (), (), market=Market.US, as_of=AT, include_yearly=True)}
    assert document["calendar_coverage"]["status"] == "MISSING_PRICES"
    assert document["calendar_coverage"]["yearly"] == []
    assert "MISSING_PRICES" in render_equity_note(document)
