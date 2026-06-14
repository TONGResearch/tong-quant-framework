from datetime import UTC, datetime, timedelta
from decimal import Decimal

from tong_quant.domain.enums import AssetType, Market
from tong_quant.domain.models import Bar, Instrument
from tong_quant.market_regime.metrics import (
    breadth_metric,
    level_change_metric,
    trend_metric,
    volatility_metric,
)


def test_metric_helpers_produce_normalized_values() -> None:
    as_of = datetime(2025, 1, 2, tzinfo=UTC)
    bars = _bars(as_of, count=80, daily_change=0.002)

    trend = trend_metric(bars, name="trend", as_of=as_of)
    volatility = volatility_metric(bars, name="volatility", as_of=as_of)
    breadth = breadth_metric(
        name="breadth",
        advancing=3500,
        declining=1500,
        available_at=as_of,
        source="test",
    )
    turnover = level_change_metric(
        name="turnover",
        current=1.2,
        baseline=1.0,
        available_at=as_of,
        source="test",
    )

    assert trend.value > 0
    assert -1 <= volatility.value <= 1
    assert breadth.value == 0.4
    assert 0 < turnover.value <= 1


def _bars(as_of: datetime, *, count: int, daily_change: float) -> list[Bar]:
    instrument = Instrument(
        "TEST",
        Market.US,
        "Test Index",
        asset_type=AssetType.INDEX,
        currency="USD",
    )
    price = 100.0
    bars = []
    for offset in range(count):
        timestamp = as_of - timedelta(days=count - offset)
        price *= 1 + daily_change
        bars.append(
            Bar(
                instrument=instrument,
                timestamp=timestamp,
                available_at=timestamp,
                open=Decimal(str(price)),
                high=Decimal(str(price * 1.01)),
                low=Decimal(str(price * 0.99)),
                close=Decimal(str(price)),
                volume=Decimal("1000"),
                source="test",
            )
        )
    return bars
