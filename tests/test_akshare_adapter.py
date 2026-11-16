import json
from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from tong_quant.core.exceptions import DataProviderError
from tong_quant.data.models import DailyBarRequest
from tong_quant.data.providers.akshare import (
    AkShareAdapter,
    AkShareDailyBarsUnavailableError,
    _market_symbol,
)
from tong_quant.domain.enums import AssetType


class FlakyClient:
    def __init__(self) -> None:
        self.calls = 0
        self.fallback_symbols: list[object] = []

    def stock_zh_a_hist(self, **kwargs: object) -> pd.DataFrame:
        del kwargs
        self.calls += 1
        raise ConnectionError("primary provider failure")

    def stock_zh_a_hist_tx(self, **kwargs: object) -> pd.DataFrame:
        self.fallback_symbols.append(kwargs["symbol"])
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
    assert client.calls == 2
    assert response.dataset.source == "akshare:stock_zh_a_hist_tx"
    assert response.dataset.frame["成交额"].isna().all()
    assert response.dataset.parameters["normalization_version"] == "akshare-market-data-v2"


@pytest.mark.parametrize("symbol,expected", [
    ("920982", "bj920982"), ("830982", "bj830982"), ("430001", "bj430001"),
    ("688363", "sh688363"), ("600109", "sh600109"), ("900901", "sh900901"),
    ("000063", "sz000063"), ("002624", "sz002624"),
])
def test_bse_920_routing_does_not_become_shanghai(symbol, expected):
    assert _market_symbol(symbol, AssetType.EQUITY) == expected
    client = FlakyClient()
    response = AkShareAdapter(client=client, max_attempts=1).daily_bars(  # type: ignore[arg-type]
        DailyBarRequest(symbol, "20240102", "20240102"))
    assert client.fallback_symbols == [expected]
    assert response.dataset.parameters["symbol_routing_version"] == (
        "akshare-symbol-routing-v2-bse920")


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


@pytest.mark.parametrize("endpoint", ["stock_zh_a_hist", "stock_zh_a_hist_tx"])
@pytest.mark.parametrize("error,category,field", [
    (ConnectionError("private provider response"), "network_or_upstream", ""),
    (KeyError("day"), "provider_or_contract", "day"),
    (KeyError("private provider response"), "provider_or_contract", ""),
    (KeyError({"private": "response"}), "provider_or_contract", ""),
])
def test_endpoint_diagnostics_never_render_raw_exception(endpoint, error, category, field):
    class Client:
        def stock_zh_a_hist(self, **kwargs):
            raise error

        def stock_zh_a_hist_tx(self, **kwargs):
            raise error

    result = AkShareAdapter(client=Client()).probe_daily_endpoint(
        DailyBarRequest("920982", "20240101", "20261019"), endpoint=endpoint)
    assert result["category"] == category and result["missing_field"] == field
    assert result["coverage_qualified"] is False
    assert "private" not in json.dumps(result)
    assert result["routed_symbol"] == ("920982" if endpoint == "stock_zh_a_hist" else "bj920982")


@pytest.mark.parametrize("shape", ["empty", "schema", "wrong_type"])
def test_invalid_primary_attempts_valid_fallback_without_repeating_bad_contract(shape):
    class Client(FlakyClient):
        def stock_zh_a_hist(self, **kwargs):
            self.calls += 1
            if shape == "empty":
                return pd.DataFrame()
            if shape == "wrong_type":
                return None
            return pd.DataFrame({"unexpected": [1]})

    client = Client()
    response = AkShareAdapter(client=client, sleeper=lambda _: None).daily_bars(
        DailyBarRequest("920982", "20240101", "20261019"))
    assert client.calls == 1
    assert client.fallback_symbols == ["bj920982"]
    assert response.dataset.source == "akshare:stock_zh_a_hist_tx"
    assert not response.dataset.frame.empty


@pytest.mark.parametrize("symbol,limitation", [
    ("920982", "bse_daily_payload_unavailable"),
    ("830982", "bse_daily_payload_unavailable"), ("000063", ""),
])
def test_daily_failure_keeps_both_causes_without_nested_retry_or_exception_leak(symbol, limitation):
    class Client(FlakyClient):
        def stock_zh_a_hist(self, **kwargs):
            self.calls += 1
            raise ConnectionError("private provider response with credentials")

        def stock_zh_a_hist_tx(self, **kwargs):
            self.fallback_symbols.append(kwargs["symbol"])
            raise KeyError("day")

    client = Client()
    waits = []
    adapter = AkShareAdapter(client=client, max_attempts=2, sleeper=waits.append)
    with pytest.raises(AkShareDailyBarsUnavailableError) as raised:
        adapter.daily_bars(DailyBarRequest(symbol, "20240101", "20261019"))
    record = raised.value.diagnostic_record()
    primary, fallback = record["endpoint_failures"]
    assert primary["error_type"] == "ConnectionError" and primary["attempts"] == 2
    assert fallback["missing_field"] == "day" and fallback["attempts"] == 1
    assert fallback["limitation"] == limitation
    assert client.calls == 2 and len(client.fallback_symbols) == 1 and waits == [1]
    assert record["coverage_qualified"] is False
    assert raised.value.__cause__ is None and raised.value.__context__ is None
    assert "private" not in str(raised.value) + json.dumps(record)


@pytest.mark.parametrize("shape,status,category", [
    ("empty", "empty", "empty_response"),
    ("schema", "contract_mismatch", "response_schema"),
    ("wrong_type", "contract_mismatch", "response_type"),
])
def test_both_unusable_daily_responses_fail_before_cache_write(tmp_path, shape, status, category):
    from tong_quant.data.cache import DataFrameCache

    class Client(FlakyClient):
        def response(self):
            if shape == "empty":
                return pd.DataFrame()
            if shape == "wrong_type":
                return None
            return pd.DataFrame({"unexpected": [1]})

        def stock_zh_a_hist(self, **kwargs):
            self.calls += 1
            return self.response()

        def stock_zh_a_hist_tx(self, **kwargs):
            self.fallback_symbols.append(kwargs["symbol"])
            return self.response()

    client = Client()
    adapter = AkShareAdapter(client=client, cache=DataFrameCache(tmp_path, timedelta(hours=1)))
    with pytest.raises(AkShareDailyBarsUnavailableError) as raised:
        adapter.daily_bars(DailyBarRequest("920982", "20240101", "20261019"))
    assert all(item.status == status and item.category == category
               for item in raised.value.endpoint_failures)
    assert client.calls == 1 and len(client.fallback_symbols) == 1
    assert not list(tmp_path.rglob("*.json.gz"))


def test_daily_network_retry_can_recover_primary_without_calling_fallback():
    class Client(FlakyClient):
        def stock_zh_a_hist(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise TimeoutError("private")
            return pd.DataFrame({"日期": ["2024-01-02"], "开盘": [10], "收盘": [10],
                                 "最高": [11], "最低": [9], "成交量": [100]})

    client = Client()
    response = AkShareAdapter(client=client, sleeper=lambda _: None).daily_bars(
        DailyBarRequest("920982", "20240102", "20240102"))
    assert client.calls == 2 and not client.fallback_symbols
    assert response.dataset.source == "akshare:stock_zh_a_hist"


def test_legacy_empty_cache_cannot_bypass_repaired_daily_fetch(tmp_path):
    from tong_quant.data.cache import DataFrameCache
    from tong_quant.data.models import RawDataset

    cache = DataFrameCache(tmp_path, timedelta(hours=1))
    legacy = {"symbol": "920982", "start_date": "20240102", "end_date": "20240102",
              "asset_type": "equity", "adjustment": "none",
              "normalization_version": "akshare-market-data-v2",
              "symbol_routing_version": "akshare-symbol-routing-v2-bse920"}
    cache.put(RawDataset("a_share_daily", pd.DataFrame(), datetime.now(UTC),
                         "akshare:stock_zh_a_hist", legacy))
    client = FlakyClient()
    response = AkShareAdapter(client=client, cache=cache, max_attempts=1).daily_bars(
        DailyBarRequest("920982", "20240102", "20240102"))
    assert response.cache_hit is False and client.calls == 1
    assert response.dataset.parameters["fetch_version"] == (
        "akshare-daily-fetch-v2-endpoint-failures")
    assert cache.get("a_share_daily", legacy).frame.empty  # Preserve old evidence unchanged.


@pytest.mark.parametrize("primary_available", [True, False])
def test_index_daily_endpoint_repair_preserves_index_identity(primary_available):
    class Client(FlakyClient):
        def index_zh_a_hist(self, **kwargs):
            assert kwargs["symbol"] == "399001"
            if not primary_available:
                raise KeyError("klines")
            return pd.DataFrame({"日期": ["2024-01-02"], "开盘": [10], "收盘": [10],
                                 "最高": [11], "最低": [9], "成交量": [100]})

    client = Client()
    response = AkShareAdapter(client=client).daily_bars(
        DailyBarRequest("399001", "20240102", "20240102", asset_type=AssetType.INDEX))
    assert client.calls == 0
    assert client.fallback_symbols == ([] if primary_available else ["sz399001"])
    assert "股票代码" not in response.dataset.frame.columns
    assert response.dataset.dataset == "index_daily"


def test_sina_access_probe_is_separate_and_cannot_authorize_canonical_bars():
    class Client:
        def stock_zh_a_daily(self, **kwargs):
            assert kwargs["symbol"] == "bj920982" and "timeout" not in kwargs
            return pd.DataFrame({"date": ["2026-10-19"], "open": [10], "high": [11],
                                 "low": [9], "close": [10], "volume": [100], "amount": [1000]})

    result = AkShareAdapter(client=Client()).probe_daily_endpoint(
        DailyBarRequest("920982", "20240101", "20261019"), endpoint="stock_zh_a_daily")
    assert result["status"] == "available" and result["rows"] == 1
    assert result["coverage_qualified"] is False
    assert "forward-fill" in result["limitations"][0]


@pytest.mark.parametrize("shape,status", [
    ("empty", "empty"), ("schema", "contract_mismatch"),
    ("wrong_type", "contract_mismatch"), ("available", "available"),
])
def test_endpoint_access_is_not_coverage_and_empty_is_not_an_implementation_failure(shape, status):
    class Client(FlakyClient):
        def stock_zh_a_hist_tx(self, **kwargs):
            if shape == "empty":
                return pd.DataFrame()
            if shape == "schema":
                return pd.DataFrame({"unexpected": [1]})
            if shape == "wrong_type":
                return None
            return super().stock_zh_a_hist_tx(**kwargs)

    result = AkShareAdapter(client=Client()).probe_daily_endpoint(
        DailyBarRequest("000063", "20240101", "20261019"), endpoint="stock_zh_a_hist_tx")
    assert result["status"] == status
    assert result["coverage_qualified"] is False
