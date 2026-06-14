import os
from pathlib import Path

import pytest

from tong_quant.data.models import DailyBarRequest
from tong_quant.data.pipeline import DataIngestionPipeline
from tong_quant.data.providers.akshare import AkShareAdapter
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import AssetType


@pytest.mark.live_data
@pytest.mark.skipif(
    os.getenv("TONG_QUANT_RUN_LIVE_DATA_TESTS") != "1",
    reason="set TONG_QUANT_RUN_LIVE_DATA_TESTS=1 to call AKShare",
)
def test_live_akshare_data_foundation_smoke(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "live.sqlite3")
    pipeline = DataIngestionPipeline(AkShareAdapter(), store)
    pipeline.initialize()

    stock = pipeline.ingest_daily_bars(
        DailyBarRequest("600000", "20240102", "20240105")
    )
    index = pipeline.ingest_daily_bars(
        DailyBarRequest(
            "000001",
            "20240102",
            "20240105",
            asset_type=AssetType.INDEX,
        )
    )
    calendar = pipeline.ingest_trading_calendar()
    company = pipeline.ingest_company_info("600000")
    universe = pipeline.ingest_a_share_universe()

    assert stock.accepted > 0
    assert index.accepted > 0
    assert calendar.accepted > 0
    assert company.accepted == 1
    assert universe.accepted > 0
    assert store.table_count("daily_bars") == stock.accepted + index.accepted
