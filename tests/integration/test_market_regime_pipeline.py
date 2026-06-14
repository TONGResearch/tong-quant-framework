from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from tong_quant.data.service import MarketDataService
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import AssetType, Market, Regime
from tong_quant.domain.models import Bar, Instrument
from tong_quant.market_regime.china import (
    ChinaMarketRegimeClassifier,
    ChinaMarketRegimeInputBuilder,
)
from tong_quant.market_regime.global_market import (
    GlobalMarketRegimeClassifier,
    GlobalMarketRegimeInputBuilder,
)
from tong_quant.market_regime.metrics import (
    breadth_metric,
    count_level_metric,
    level_change_metric,
)


@pytest.mark.integration
def test_china_regime_builds_from_point_in_time_sqlite_data(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "regime.sqlite3")
    store.initialize()
    as_of = datetime(2025, 1, 2, 8, tzinfo=UTC)
    for symbol in ("000300", "000985"):
        instrument = Instrument(
            symbol,
            Market.CHINA_A,
            symbol,
            asset_type=AssetType.INDEX,
            available_at=as_of - timedelta(days=120),
            source="test",
        )
        store.upsert_instruments([instrument])
        store.upsert_daily_bars(_rising_bars(instrument, as_of, 80))
        store.upsert_daily_bars([_future_bearish_revision(instrument, as_of)])

    external = {
        "rising_stocks": count_level_metric(
            name="rising_stocks",
            count=3800,
            universe_size=5200,
            available_at=as_of,
            source="breadth-feed",
        ),
        "market_turnover": level_change_metric(
            name="market_turnover",
            current=1.25,
            baseline=1.0,
            available_at=as_of,
            source="turnover-feed",
        ),
        "market_breadth": breadth_metric(
            name="market_breadth",
            advancing=3800,
            declining=1400,
            available_at=as_of,
            source="breadth-feed",
        ),
    }
    inputs = ChinaMarketRegimeInputBuilder(MarketDataService(store)).build(
        market=Market.CHINA_A,
        as_of=as_of,
        external_metrics=external,
    )
    regime, signal = ChinaMarketRegimeClassifier().classify(inputs)

    assert regime.state is Regime.BULL
    assert regime.as_of == as_of
    assert signal.effective_at == as_of
    assert all(metric.available_at <= as_of for metric in inputs.metrics)


@pytest.mark.integration
def test_global_regime_builds_from_reusable_interfaces(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "global-regime.sqlite3")
    store.initialize()
    as_of = datetime(2025, 1, 2, 21, tzinfo=UTC)
    for symbol, daily_change in (("SPX", Decimal("0.003")), ("WORLD", Decimal("0.001"))):
        instrument = Instrument(
            symbol,
            Market.US,
            symbol,
            asset_type=AssetType.INDEX,
            currency="USD",
            available_at=as_of - timedelta(days=120),
            source="test",
        )
        store.upsert_instruments([instrument])
        store.upsert_daily_bars(_market_bars(instrument, as_of, 80, daily_change))

    inputs = GlobalMarketRegimeInputBuilder(
        data=MarketDataService(store),
        market=Market.US,
        major_index_symbol="SPX",
        benchmark_symbol="WORLD",
        subject="US equity market",
    ).build(
        market=Market.US,
        as_of=as_of,
        external_metrics={
            "market_breadth": breadth_metric(
                name="market_breadth",
                advancing=3000,
                declining=1200,
                available_at=as_of,
                source="breadth-feed",
            )
        },
    )
    regime, signal = GlobalMarketRegimeClassifier(
        market=Market.US,
        subject="US equity market",
    ).classify(inputs)

    assert regime.state is Regime.BULL
    assert signal.features["primary_regime"] == Regime.BULL.value
    assert len(regime.contributions) == 4


def _rising_bars(
    instrument: Instrument,
    as_of: datetime,
    count: int,
) -> list[Bar]:
    bars = []
    price = Decimal("100")
    for offset in range(count):
        timestamp = as_of - timedelta(days=count - offset)
        price *= Decimal("1.003")
        bars.append(
            Bar(
                instrument=instrument,
                timestamp=timestamp,
                available_at=timestamp,
                open=price,
                high=price * Decimal("1.01"),
                low=price * Decimal("0.99"),
                close=price,
                volume=Decimal("1000"),
                source="test",
                ingested_at=as_of,
            )
        )
    return bars


def _market_bars(
    instrument: Instrument,
    as_of: datetime,
    count: int,
    daily_change: Decimal,
) -> list[Bar]:
    bars = []
    price = Decimal("100")
    for offset in range(count):
        timestamp = as_of - timedelta(days=count - offset)
        price *= Decimal("1") + daily_change
        bars.append(
            Bar(
                instrument=instrument,
                timestamp=timestamp,
                available_at=timestamp,
                open=price,
                high=price * Decimal("1.01"),
                low=price * Decimal("0.99"),
                close=price,
                volume=Decimal("1000"),
                source="test",
                ingested_at=as_of,
            )
        )
    return bars


def _future_bearish_revision(instrument: Instrument, as_of: datetime) -> Bar:
    timestamp = as_of - timedelta(days=1)
    return Bar(
        instrument=instrument,
        timestamp=timestamp,
        available_at=as_of + timedelta(days=1),
        open=Decimal("10"),
        high=Decimal("10"),
        low=Decimal("9"),
        close=Decimal("9"),
        volume=Decimal("1000"),
        source="future-test",
        ingested_at=as_of,
    )
