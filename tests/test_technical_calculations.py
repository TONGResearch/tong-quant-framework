import ast
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from tong_quant.config.settings import TechnicalResearchSettings
from tong_quant.domain.enums import Adjustment, Market
from tong_quant.domain.models import Bar, Instrument
from tong_quant.research.technical.diagnostics import technical_diagnostics
from tong_quant.research.technical.events import (
    granville_events,
    startup_observation,
    triple_cross_events,
)
from tong_quant.research.technical.indicators import TechnicalParameters, atr, kdj, macd


def _bars(closes):
    instrument = Instrument("000063", Market.CHINA_A, "Fixture, not issuer observations")
    start = datetime(2025, 1, 1, tzinfo=UTC)
    return tuple(Bar(
        instrument=instrument, timestamp=start + timedelta(days=index),
        available_at=start + timedelta(days=index, hours=16),
        open=Decimal(str(close)), high=Decimal(str(close)) + Decimal("0.1"),
        low=Decimal(str(close)) - Decimal("0.1"), close=Decimal(str(close)),
        volume=Decimal(1000), source="synthetic",
    ) for index, close in enumerate(closes))


def _diagnostics(bars, parameters=None):
    return technical_diagnostics(tuple(bars), parameters or TechnicalParameters(),
                                 as_of=datetime(2026, 1, 1, tzinfo=UTC))


@pytest.mark.parametrize("name,value", [
    ("macd_fast", True), ("macd_slow", 0), ("macd_signal", 1.5),
    ("kdj_k", -1), ("kdj_d", False), ("kdj_period", 0), ("atr_period", 0),
    ("setup_expiry", -1), ("atr_multiple", float("nan")),
    ("support_tolerance", float("inf")), ("extreme_deviation", 1),
    ("triple_periods", (5, 5, 20)), ("triple_periods", (5, True, 20)),
    ("triple_periods", (5, 20)), ("macd_fast", 26),
])
def test_invalid_parameters_fail_closed(name, value):
    with pytest.raises(ValueError):
        replace(TechnicalParameters(), **{name: value})


@pytest.mark.parametrize("changes", [
    {"macd_fast": 30}, {"kdj_k": False}, {"triple_periods": [5, 5, 20]},
    {"extreme_deviation": float("nan")}, {"support_tolerance": 0.9},
])
def test_settings_reject_invalid_calculation_configuration(changes):
    with pytest.raises(ValueError):
        TechnicalResearchSettings(50, 200, 252, **changes)


def test_macd_matches_independent_recursive_reference():
    closes = [10 + index / 10 + (index % 4) for index in range(60)]
    parameters = TechnicalParameters()
    fast = slow = closes[0]
    dea = 0.0
    for close in closes[1:]:
        fast += 2 / 13 * (close - fast)
        slow += 2 / 27 * (close - slow)
        dif = fast - slow
        dea += 2 / 10 * (dif - dea)
    point = macd(closes, parameters)
    assert point is not None
    assert point.dif == pytest.approx(fast - slow)
    assert point.dea == pytest.approx(dea)
    assert point.histogram == pytest.approx(point.dif - point.dea)
    assert macd(closes[:34], parameters) is None


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), 0, -1, True])
def test_indicator_invalid_prices_are_not_interpolated(bad):
    with pytest.raises(ValueError):
        macd([10.0, bad], TechnicalParameters())


def test_kdj_seed_smoothing_and_unclipped_j():
    bars = _bars([10] * 9 + [12, 13])
    point = kdj(bars, TechnicalParameters())
    k = d = 50.0
    for index in range(8, len(bars)):
        window = bars[index - 8:index + 1]
        high = max(float(bar.high) for bar in window)
        low = min(float(bar.low) for bar in window)
        rsv = 100 * (float(bars[index].close) - low) / (high - low)
        k += (rsv - k) / 3
        d += (k - d) / 3
    assert point is not None
    assert point.k == pytest.approx(k)
    assert point.d == pytest.approx(d)
    assert point.j == pytest.approx(3 * k - 2 * d)
    extreme = kdj(_bars([10] * 9 + [100]), TechnicalParameters(kdj_k=1, kdj_d=10))
    assert extreme is not None and extreme.j > 100


def test_flat_kdj_is_neutral_and_warmup_is_missing():
    bars = tuple(replace(bar, high=bar.close, low=bar.close) for bar in _bars([10] * 10))
    result = kdj(bars, TechnicalParameters())
    assert result is not None and (result.k, result.d, result.j) == (50, 50, 50)
    assert result.cross == "none"
    assert kdj(bars[:9], TechnicalParameters()) is None


@pytest.mark.parametrize("bullish", [True, False])
def test_triple_cross_requires_body_not_just_wick(bullish):
    parameters = TechnicalParameters(triple_periods=(2, 3, 4))
    bars = _bars([10] * 4)
    candle = replace(bars[-1], open=Decimal(8 if bullish else 12),
                     close=Decimal(12 if bullish else 8), high=Decimal(13), low=Decimal(7))
    expected = "bullish" if bullish else "bearish"
    assert triple_cross_events((*bars[:-1], candle), parameters) == (
        f"{expected}_body_crosses_ma_cluster",)
    wick = replace(candle, open=Decimal("10.01"), close=Decimal("10.02"))
    assert triple_cross_events((*bars[:-1], wick), parameters) == ()
    assert triple_cross_events(bars[:2], parameters) == ()


@pytest.mark.parametrize("closes,event", [
    ([10, 10, 9, 11], "bull_1"),
    ([8, 12, 12, 10.5], "bull_2"),
    ([9, 10, 11, 10.7], "bull_3"),
    ([10, 10, 10, 4], "bull_4"),
    ([10, 10, 11, 9], "bear_1"),
    ([12, 8, 8, 9], "bear_2"),
    ([11, 10, 9, 9.3], "bear_3"),
    ([10, 10, 10, 20], "bear_4"),
])
def test_eight_explicit_granville_event_definitions(closes, event):
    parameters = TechnicalParameters(granville_period=3, slope_period=1,
                                     support_tolerance=0.1, extreme_deviation=0.3)
    bars = _bars([closes[0], *closes])
    if event == "bull_3":
        bars = (*bars[:-1], replace(bars[-1], low=Decimal("10.6")))
    if event == "bear_3":
        bars = (*bars[:-1], replace(bars[-1], high=Decimal("9.4")))
    assert any(f"granville_{event}_" in value for value in granville_events(bars, parameters))
    assert granville_events(bars[:3], parameters) == ()


def test_startup_confirmation_is_causal_and_stop_only_tightens():
    parameters = TechnicalParameters(triple_periods=(2, 3, 4), atr_period=2)
    bars = _bars([10] * 4)
    trigger = replace(bars[-1], open=Decimal(8), close=Decimal(12),
                      low=Decimal(7), high=Decimal(13))
    prefix = (*bars[:-1], trigger)
    armed = startup_observation(prefix, parameters)
    assert armed.state == "ARMED" and armed.confirmed_index is None
    more = _bars([10] * 4 + [14, 15, 14.5])
    confirmed = startup_observation((*prefix, *more[4:5]), parameters)
    later = startup_observation((*prefix, *more[4:]), parameters)
    assert confirmed.state == later.state == "CONFIRMED"
    assert confirmed.trailing_reference <= later.trailing_reference
    assert startup_observation(prefix, parameters) == armed
    bad = replace(more[-1], open=Decimal(5), high=Decimal(6), low=Decimal(4), close=Decimal(5))
    assert startup_observation((*prefix, *more[4:-1], bad), parameters).state == "INVALIDATED"


def test_unconfirmed_startup_expires():
    parameters = TechnicalParameters(triple_periods=(2, 3, 4), setup_expiry=1)
    bars = _bars([10] * 4 + [12, 12])
    trigger = replace(bars[3], open=Decimal(8), close=Decimal(12),
                      low=Decimal(7), high=Decimal(13))
    assert startup_observation((*bars[:3], trigger, *bars[4:]), parameters).state == "EXPIRED"


def test_short_startup_stop_tightens_downward():
    parameters = TechnicalParameters(triple_periods=(2, 3, 4), atr_period=2)
    bars = _bars([20] * 4 + [16, 15, 15.5])
    trigger = replace(bars[3], open=Decimal(22), close=Decimal(18),
                      high=Decimal(23), low=Decimal(17))
    prefix = (*bars[:3], trigger)
    assert startup_observation(prefix, parameters).state == "ARMED"
    first = startup_observation((*prefix, bars[4]), parameters)
    last = startup_observation((*prefix, *bars[4:]), parameters)
    assert first.state == last.state == "CONFIRMED"
    assert last.trailing_reference <= first.trailing_reference


def test_family_cap_and_conflicts_are_not_averaged_away():
    bars = _bars([10 + index / 10 for index in range(260)])
    normal = _diagnostics(bars)
    assert normal["technical_family_count"] == 2
    assert normal["technical_scoring_admitted"] is False
    # Rising MA can coexist with bearish momentum: retain the contradiction.
    falling = _bars([10 + index / 10 for index in range(240)]
                    + [34 - index / 10 for index in range(20)])
    result = _diagnostics(falling)
    assert result["trend_structure_family"] == "BULLISH"
    assert result["momentum_family"] == "BEARISH"
    assert result["technical_confluence"] == "CONFLICTED"


def test_determinism_identity_and_empty_data_are_explicit():
    bars = _bars([10 + index / 10 for index in range(60)])
    result = _diagnostics(bars)
    assert _diagnostics(tuple(reversed(bars))) == result
    assert _diagnostics((*bars, bars[-1])) == result
    assert _diagnostics(bars, TechnicalParameters(macd_signal=8))["technical_input_hash"] != (
        result["technical_input_hash"])
    assert _diagnostics(bars[:-1])["technical_input_hash"] != result["technical_input_hash"]
    assert _diagnostics(())["technical_confluence"] == "INSUFFICIENT_DATA"
    assert result["size_style_status"] == "INSUFFICIENT_DATA"
    assert result["seven_plus_one_status"] == "DEFERRED_BY_OWNER"


def test_latest_suspension_blocks_current_diagnostics_without_erasing_history():
    bars = _bars([10 + index / 10 for index in range(260)])
    suspended = replace(bars[-1], is_suspended=True,
                        available_at=bars[-1].available_at + timedelta(days=1))
    original = (*bars, suspended)
    result = _diagnostics(original)
    assert result["technical_input_status"] == "SUSPENDED_LATEST"
    assert result["technical_confluence"] == "INSUFFICIENT_DATA"
    assert result["technical_latest_close"] is result["technical_last_observed_at"] is None
    assert result["technical_usable_observations"] == 0
    assert result["technical_latest_supplied_observed_at"] == suspended.timestamp.isoformat()
    assert "latest_suspended_observation" in result["technical_missing_inputs"]
    assert result["macd_dif"] is result["kdj_k"] is None
    assert result["structural_invalidation_reference"] is None
    assert _diagnostics(tuple(reversed(original))) == result
    assert len(original) == 261 and bars[-1].is_suspended is False


@pytest.mark.parametrize("change", ["price", "volume", "time", "source"])
def test_blocked_observation_is_bound_not_replaced_with_empty_history(change):
    bars = _bars([10 + index / 10 for index in range(260)])
    suspended = replace(bars[-1], is_suspended=True,
                        available_at=bars[-1].available_at + timedelta(days=1))
    altered = {
        "price": {"close": suspended.close + Decimal("0.01")},
        "volume": {"volume": Decimal(1001)},
        "time": {"available_at": suspended.available_at + timedelta(seconds=1)},
        "source": {"source": "changed_synthetic"},
    }[change]
    # Source consistency is still checked; changing the whole series is not source verification.
    supplied = tuple(replace(bar, source="changed_synthetic") for bar in bars) if (
        change == "source") else bars
    result = _diagnostics((*supplied, replace(suspended, **altered)))
    original = _diagnostics((*bars, suspended))
    assert result["technical_input_status"] == original["technical_input_status"]
    assert result["technical_input_hash"] != original["technical_input_hash"]
    assert result["technical_input_hash"] != _diagnostics(())["technical_input_hash"]


def test_later_active_observation_allows_diagnostics_but_does_not_prove_resumption():
    bars = _bars([10 + index / 10 for index in range(260)])
    suspended = replace(bars[-2], is_suspended=True,
                        available_at=bars[-2].available_at + timedelta(days=1))
    result = _diagnostics((*bars, suspended))
    assert result["technical_input_status"] == "OBSERVED_UNQUALIFIED"
    assert result["technical_usable_observations"] == 259
    assert result["technical_latest_close"] == float(bars[-1].close)
    assert "latest_suspended_observation" not in result["technical_missing_inputs"]


@pytest.mark.parametrize("defect", [
    "future", "adjusted", "mixed_source", "conflicting", "intraday",
])
def test_diagnostic_entry_rejects_bad_inputs(defect):
    bars = _bars([10] * 40)
    if defect == "future":
        bars = (*bars[:-1], replace(bars[-1], available_at=datetime(2027, 1, 1, tzinfo=UTC)))
    elif defect == "adjusted":
        bars = (*bars[:-1], replace(bars[-1], adjustment=Adjustment.FORWARD))
    elif defect == "mixed_source":
        bars = (*bars[:-1], replace(bars[-1], source="another-source"))
    elif defect == "conflicting":
        bars = (*bars, replace(bars[-1], volume=Decimal(3000)))
    else:
        extra = replace(bars[-1], timestamp=bars[-1].timestamp + timedelta(hours=1))
        bars = (*bars, extra)
    with pytest.raises(ValueError):
        _diagnostics(bars)


def test_atr_includes_gaps_and_is_not_a_fill_price():
    bars = _bars([10, 20, 20])
    assert atr(bars, 2) == pytest.approx((10.1 + 0.2) / 2)
    assert atr(bars[:2], 2) is None


def test_new_technical_code_has_no_trading_dependencies():
    root = Path(__file__).resolve().parents[1] / "src/tong_quant/research/technical"
    forbidden = {"execution", "broker", "order", "trade", "fill", "paper", "portfolio",
                 "notifications"}
    for path in root.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not forbidden.intersection(node.module.split("."))
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not forbidden.intersection(alias.name.split("."))
