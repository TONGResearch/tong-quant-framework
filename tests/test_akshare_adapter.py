from datetime import UTC, datetime

import pandas as pd

from tong_quant.data.models import DailyBarRequest
from tong_quant.data.providers.akshare import AkShareAdapter


class FlakyClient:
    def __init__(self) -> None:
        self.calls = 0

    def stock_zh_a_hist(self, **kwargs: object) -> pd.DataFrame:
        del kwargs
        self.calls += 1
        raise ConnectionError("primary provider failure")

    def stock_zh_a_hist_tx(self, **kwargs: object) -> pd.DataFrame:
        del kwargs
        return pd.DataFrame(
            {
                "date": ["2024-01-02"],
                "open": [10],
                "close": [10.5],
                "high": [10.8],
                "low": [9.9],
                "amount": [100],
            }
        )


def test_akshare_adapter_uses_tencent_fallback() -> None:
    client = FlakyClient()
    adapter = AkShareAdapter(
        client=client,  # type: ignore[arg-type]
        clock=lambda: datetime(2024, 1, 3, tzinfo=UTC),
        max_attempts=2,
        sleeper=lambda _: None,
    )

    response = adapter.daily_bars(DailyBarRequest("600000", "20240102", "20240102"))

    assert response.dataset.frame.empty is False
    assert client.calls == 1
    assert response.dataset.source == "akshare:stock_zh_a_hist_tx"
