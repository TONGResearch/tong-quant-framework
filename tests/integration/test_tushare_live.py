import os
from datetime import UTC, datetime

import pytest

from tong_quant.data.calibration import CalibrationDataset, CalibrationQuery
from tong_quant.data.providers.tushare import TushareCalibrationAdapter


@pytest.mark.live_data
def test_tushare_publication_calibration_live() -> None:
    if os.getenv("TONG_QUANT_RUN_LIVE_DATA_TESTS") != "1":
        pytest.skip("set TONG_QUANT_RUN_LIVE_DATA_TESTS=1 to call live providers")
    if not os.getenv("TUSHARE_TOKEN"):
        pytest.skip("set TUSHARE_TOKEN for the opt-in Tushare live test")

    snapshot = TushareCalibrationAdapter().calibration_snapshot(
        CalibrationQuery(
            dataset=CalibrationDataset.FINANCIAL_PUBLICATION_DATES,
            as_of=datetime.now(UTC),
            parameters={"period_end": "20231231"},
        )
    )

    assert snapshot.provider == "tushare"
