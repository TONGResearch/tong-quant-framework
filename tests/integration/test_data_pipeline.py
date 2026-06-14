from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from tong_quant.data.cache import DataFrameCache
from tong_quant.data.models import DailyBarRequest
from tong_quant.data.pipeline import DataIngestionPipeline
from tong_quant.data.providers.akshare import AkShareAdapter
from tong_quant.data.service import MarketDataService
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import AssetType, Market


class FakeAkShareClient:
    def __init__(self) -> None:
        self.daily_calls = 0
        self.index_calls = 0

    def stock_zh_a_hist(self, **kwargs: object) -> pd.DataFrame:
        del kwargs
        self.daily_calls += 1
        return _daily_frame(include_symbol=True)

    def index_zh_a_hist(self, **kwargs: object) -> pd.DataFrame:
        del kwargs
        self.index_calls += 1
        return _daily_frame(include_symbol=False)

    def tool_trade_date_hist_sina(self) -> pd.DataFrame:
        return pd.DataFrame({"trade_date": [date(2024, 1, 2), date(2024, 1, 3)]})

    def stock_individual_info_em(self, **kwargs: object) -> pd.DataFrame:
        del kwargs
        return pd.DataFrame(
            {
                "item": ["股票代码", "股票简称", "行业", "上市时间"],
                "value": ["600000", "浦发银行", "银行", 19991110],
            }
        )

    def stock_zh_a_spot_em(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "代码": ["600000", "000001"],
                "名称": ["浦发银行", "平安银行"],
            }
        )


@pytest.fixture
def data_foundation(tmp_path: Path) -> tuple[
    FakeAkShareClient,
    DataIngestionPipeline,
    MarketDataService,
    SQLiteStore,
]:
    client = FakeAkShareClient()
    retrieved_at = datetime(2024, 1, 5, 8, tzinfo=UTC)
    cache = DataFrameCache(
        tmp_path / "cache",
        timedelta(days=1),
        clock=lambda: retrieved_at,
    )
    adapter = AkShareAdapter(
        client=client,
        cache=cache,
        clock=lambda: retrieved_at,
    )
    store = SQLiteStore(tmp_path / "tong_quant.sqlite3")
    pipeline = DataIngestionPipeline(adapter, store)
    pipeline.initialize()
    return client, pipeline, MarketDataService(store), store


@pytest.mark.integration
def test_daily_pipeline_caches_normalizes_and_enforces_point_in_time(
    data_foundation: tuple[
        FakeAkShareClient,
        DataIngestionPipeline,
        MarketDataService,
        SQLiteStore,
    ],
) -> None:
    client, pipeline, service, store = data_foundation
    request = DailyBarRequest("600000", "20240102", "20240103")

    first = pipeline.ingest_daily_bars(request)
    second = pipeline.ingest_daily_bars(request)

    assert first.accepted == 2
    assert first.cached is False
    assert second.cached is True
    assert client.daily_calls == 1
    assert store.table_count("daily_bars") == 2

    before_second_bar = datetime(2024, 1, 3, 7, 0, tzinfo=UTC)
    visible = service.daily_bars(
        "600000",
        Market.CHINA_A,
        AssetType.EQUITY,
        date(2024, 1, 2),
        date(2024, 1, 3),
        as_of=before_second_bar,
    )
    assert [bar.timestamp.date() for bar in visible] == [date(2024, 1, 2)]

    after_second_bar = datetime(2024, 1, 3, 7, 2, tzinfo=UTC)
    visible = service.daily_bars(
        "600000",
        Market.CHINA_A,
        AssetType.EQUITY,
        date(2024, 1, 2),
        date(2024, 1, 3),
        as_of=after_second_bar,
    )
    assert [bar.timestamp.date() for bar in visible] == [
        date(2024, 1, 2),
        date(2024, 1, 3),
    ]


@pytest.mark.integration
def test_index_calendar_company_and_universe_ingestion(
    data_foundation: tuple[
        FakeAkShareClient,
        DataIngestionPipeline,
        MarketDataService,
        SQLiteStore,
    ],
) -> None:
    client, pipeline, service, store = data_foundation

    pipeline.ingest_daily_bars(
        DailyBarRequest(
            "000001",
            "20240102",
            "20240103",
            asset_type=AssetType.INDEX,
        )
    )
    pipeline.ingest_trading_calendar()
    pipeline.ingest_company_info("600000")
    pipeline.ingest_a_share_universe()

    assert client.index_calls == 1
    assert store.table_count("daily_bars") == 2
    assert store.table_count("trading_calendar") == 2
    assert store.table_count("instruments") == 3

    as_of = datetime(2024, 1, 6, tzinfo=UTC)
    company = service.instrument(
        "600000",
        Market.CHINA_A,
        AssetType.EQUITY,
        as_of=as_of,
    )
    assert company is not None
    assert company.name == "浦发银行"
    assert company.industry == "银行"
    assert company.listing_date == date(1999, 11, 10)
    assert service.trading_days(
        Market.CHINA_A,
        date(2024, 1, 1),
        date(2024, 1, 4),
        as_of=as_of,
    ) == [date(2024, 1, 2), date(2024, 1, 3)]


def _daily_frame(*, include_symbol: bool) -> pd.DataFrame:
    data: dict[str, object] = {
        "日期": [date(2024, 1, 2), date(2024, 1, 3)],
        "开盘": [10.0, 10.5],
        "收盘": [10.5, 10.8],
        "最高": [10.8, 11.0],
        "最低": [9.9, 10.3],
        "成交量": [1000, 1200],
        "成交额": [10000, 12500],
    }
    if include_symbol:
        data["股票代码"] = ["600000", "600000"]
    return pd.DataFrame(data)
