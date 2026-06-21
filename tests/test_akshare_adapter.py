from datetime import UTC, datetime

import pandas as pd
import pytest

from tong_quant.core.exceptions import DataProviderError
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


def test_index_membership_uses_guarded_fetcher_timeout() -> None:
    observed: list[tuple[str, float]] = []

    def fetch(symbol: str, timeout_seconds: float) -> pd.DataFrame:
        observed.append((symbol, timeout_seconds))
        return pd.DataFrame(
            [[20260620, 300, "沪深300", "CSI 300", 600000, "浦发银行", "SPDB", "SH", "SSE"]]
        )

    adapter = AkShareAdapter(
        index_membership_fetcher=fetch,
        timeout_seconds=2.5,
        clock=lambda: datetime(2026, 6, 21, tzinfo=UTC),
    )

    response = adapter.index_membership("000300")

    assert observed == [("000300", 2.5)]
    assert len(response.dataset.frame) == 1
    assert response.dataset.source.endswith("timeout_guarded")


def test_index_membership_timeout_fails_after_bounded_retries() -> None:
    calls = 0

    def fetch(symbol: str, timeout_seconds: float) -> pd.DataFrame:
        nonlocal calls
        del symbol, timeout_seconds
        calls += 1
        raise TimeoutError("controlled timeout")

    adapter = AkShareAdapter(
        index_membership_fetcher=fetch,
        timeout_seconds=0.01,
        max_attempts=2,
        retry_delay_seconds=0,
        sleeper=lambda _: None,
    )

    with pytest.raises(DataProviderError, match="index_membership failed") as error:
        adapter.index_membership("000300")

    assert calls == 2
    assert "TimeoutError" in str(error.value)
