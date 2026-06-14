from datetime import UTC, datetime, timedelta

import pytest

from tong_quant.domain.enums import Market
from tong_quant.market_regime.models import MarketRegimeInput, RegimeMetric


def test_regime_input_rejects_future_metrics() -> None:
    as_of = datetime(2025, 1, 2, tzinfo=UTC)
    metric = RegimeMetric(
        name="market_breadth",
        value=0.2,
        available_at=as_of + timedelta(seconds=1),
        source="test",
    )

    with pytest.raises(ValueError, match="future regime metrics"):
        MarketRegimeInput(
            market=Market.US,
            as_of=as_of,
            metrics=(metric,),
            subject="US market",
        )


def test_regime_metric_rejects_out_of_range_value() -> None:
    with pytest.raises(ValueError, match="between -1 and 1"):
        RegimeMetric(
            name="volatility",
            value=1.01,
            available_at=datetime(2025, 1, 2, tzinfo=UTC),
            source="test",
        )
