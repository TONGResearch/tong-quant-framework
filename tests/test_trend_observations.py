"""Synthetic price geometry never fills missing sentiment/industry confirmations."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from zoneinfo import ZoneInfo

import pytest

from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.domain.enums import Adjustment, Market
from tong_quant.domain.models import Bar, Instrument
from tong_quant.research.trend import TrendResearchModule

AT = datetime(2026, 11, 8, tzinfo=UTC)


def _bars(count=10):
    instrument = Instrument("TEST", Market.US, "Synthetic", currency="USD")
    return tuple(Bar(instrument, AT - timedelta(days=count - index), AT,
        Decimal(10), Decimal(11), Decimal(9), Decimal(10), Decimal(100), source="synthetic")
        for index in range(count))


def _module(**kwargs):
    return TrendResearchModule(breakout_period=3, volume_period=3, atr_period=3, **kwargs)


def test_prior_channel_excludes_current_high_and_preserves_missing_external_confirmations():
    bars = _bars()
    bars = (*bars[:-1], replace(bars[-1], high=Decimal(15), close=Decimal(12), volume=Decimal(300)))
    result = _module().price_observations(bars, as_of=AT)
    assert result["prior_channel_high"] == 11
    assert result["strict_breakout_observed"] is True
    assert result["breakout_threshold_observed"] is True
    assert result["prior_average_volume"] == 100 and result["volume_ratio"] == 3
    assert result["volume_threshold_observed"] is True
    assert result["market_sentiment_confirmation"] is None
    assert result["industry_heat_confirmation"] is None
    for key in ("four_confirmations_complete", "scoring_authorized", "validation_authorized",
                "historical_replay_eligible", "execution_authorized"):
        assert result[key] is False
    assert result["source_qualification"] == "NOT_ASSESSED"
    digest = result.pop("input_hash")
    assert digest == sha256(financial_input_json(result).encode()).hexdigest()


def test_touching_channel_is_not_strict_breakout():
    bars = _bars()
    bars = (*bars[:-1], replace(bars[-1], close=Decimal(11)))
    result = _module().price_observations(bars, as_of=AT)
    assert result["strict_breakout_observed"] is False
    assert result["breakout_threshold_observed"] is False


@pytest.mark.parametrize("threshold", [50, 60, 100])
def test_configured_threshold_is_observed_without_inventing_new_policy(threshold):
    bars = _bars()
    bars = (*bars[:-1], replace(bars[-1], high=Decimal(12), close=Decimal("11.055"),
                               volume=Decimal(120)))
    result = _module(confirmation_threshold=threshold).price_observations(bars, as_of=AT)
    assert result["strict_breakout_observed"] is True
    assert result["breakout_threshold_observed"] is (threshold <= 55)
    assert result["volume_threshold_observed"] is (threshold <= 60)


@pytest.mark.parametrize("count", [0, 1, 3])
def test_warmup_is_not_filled_with_fake_price_or_confirmation(count):
    result = _module().price_observations(_bars(count), as_of=AT)
    assert result["latest_close"] is None and result["volume_ratio"] is None
    assert result["strict_breakout_observed"] is None
    assert result["four_confirmations_complete"] is False


def test_zero_volume_and_latest_suspension_never_fall_back_to_positive_old_data():
    bars = tuple(replace(bar, volume=Decimal(0)) for bar in _bars())
    result = _module().price_observations(bars, as_of=AT)
    assert result["status"] == "ZERO_PRIOR_VOLUME"
    assert result["volume_ratio"] is result["volume_threshold_observed"] is None
    bars = _bars()
    suspended = (*bars[:-1], replace(bars[-1], is_suspended=True))
    result = _module().price_observations(suspended, as_of=AT)
    assert result["status"] == "SUSPENDED_LATEST" and result["usable_observations"] == 0
    assert result["latest_close"] is None
    original = _module().price_observations(bars, as_of=AT)
    assert result["bar_input_hash"] != original["bar_input_hash"]


@pytest.mark.parametrize("defect", ["future", "adjusted", "conflict", "intraday", "mixed"])
def test_invalid_original_series_is_rejected_not_trimmed(defect):
    bars = _bars()
    if defect == "future":
        bars = (*bars, replace(bars[-1], timestamp=AT + timedelta(seconds=1),
                              available_at=AT + timedelta(seconds=1)))
    elif defect == "adjusted":
        bars = (replace(bars[0], adjustment=Adjustment.FORWARD), *bars[1:])
    elif defect == "conflict":
        bars = (*bars, replace(bars[-1], close=Decimal("10.1")))
    elif defect == "intraday":
        bars = (*bars, replace(bars[-1], timestamp=bars[-1].timestamp + timedelta(hours=1)))
    else:
        bars = (*bars, replace(bars[-1], instrument=Instrument("OTHER", Market.US, "Other")))
    with pytest.raises(ValueError):
        _module().price_observations(bars, as_of=AT)


def test_duplicate_versions_do_not_inflate_warmup_and_equivalent_cutoffs_hash_identically():
    bars = _bars(3)
    result = _module().price_observations(bars * 3, as_of=AT)
    assert result["usable_observations"] == 3 and result["latest_close"] is None
    assert result == _module().price_observations(
        bars * 3, as_of=AT.astimezone(ZoneInfo("Asia/Kuala_Lumpur")))
    full = _bars()
    first = _module().price_observations(full, as_of=AT)
    changed = (*full[:-1], replace(full[-1], volume=Decimal(200)))
    assert _module().price_observations(changed, as_of=AT)["input_hash"] != first["input_hash"]
