from collections.abc import Callable
from datetime import UTC, datetime
from time import sleep
from typing import Any, Protocol

import akshare as ak
import pandas as pd

from tong_quant.core.exceptions import DataProviderError
from tong_quant.data.cache import DataFrameCache
from tong_quant.data.models import (
    DailyBarRequest,
    ProviderResponse,
    RawDataset,
    dataframe_sha256,
)
from tong_quant.domain.enums import Adjustment, AssetType


class AkShareClient(Protocol):
    def stock_zh_a_hist(self, **kwargs: Any) -> pd.DataFrame: ...

    def index_zh_a_hist(self, **kwargs: Any) -> pd.DataFrame: ...

    def stock_zh_a_hist_tx(self, **kwargs: Any) -> pd.DataFrame: ...

    def tool_trade_date_hist_sina(self) -> pd.DataFrame: ...

    def stock_individual_info_em(self, **kwargs: Any) -> pd.DataFrame: ...

    def stock_profile_cninfo(self, **kwargs: Any) -> pd.DataFrame: ...

    def stock_zh_a_spot_em(self) -> pd.DataFrame: ...

    def stock_info_a_code_name(self) -> pd.DataFrame: ...

    def stock_financial_benefit_new_ths(self, **kwargs: Any) -> pd.DataFrame: ...

    def stock_financial_debt_new_ths(self, **kwargs: Any) -> pd.DataFrame: ...

    def stock_financial_cash_new_ths(self, **kwargs: Any) -> pd.DataFrame: ...

    def stock_zh_a_st_em(self) -> pd.DataFrame: ...

    def stock_zh_a_stop_em(self) -> pd.DataFrame: ...

    def stock_info_sh_delist(self, **kwargs: Any) -> pd.DataFrame: ...

    def stock_info_sz_delist(self, **kwargs: Any) -> pd.DataFrame: ...

    def index_stock_cons_csindex(self, **kwargs: Any) -> pd.DataFrame: ...

    def stock_fhps_detail_em(self, **kwargs: Any) -> pd.DataFrame: ...

    def stock_tfp_em(self, **kwargs: Any) -> pd.DataFrame: ...

    def stock_info_sz_change_name(self, **kwargs: Any) -> pd.DataFrame: ...

    def stock_yysj_em(self, **kwargs: Any) -> pd.DataFrame: ...

    def stock_zh_a_disclosure_report_cninfo(self, **kwargs: Any) -> pd.DataFrame: ...


class AkShareAdapter:
    source_id = "akshare"
    supported_csi_indices = frozenset({"000300", "000905", "000852"})

    def __init__(
        self,
        *,
        client: AkShareClient = ak,
        cache: DataFrameCache | None = None,
        clock: Callable[[], datetime] | None = None,
        timeout_seconds: float = 15,
        max_attempts: int = 3,
        retry_delay_seconds: float = 1,
        sleeper: Callable[[float], None] = sleep,
    ) -> None:
        self._client = client
        self._cache = cache
        self._clock = clock or (lambda: datetime.now(UTC))
        self._timeout_seconds = timeout_seconds
        self._max_attempts = max_attempts
        self._retry_delay_seconds = retry_delay_seconds
        self._sleeper = sleeper
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")

    def daily_bars(self, request: DailyBarRequest) -> ProviderResponse:
        dataset_name = (
            "index_daily" if request.asset_type is AssetType.INDEX else "a_share_daily"
        )
        parameters = {
            "symbol": request.symbol,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "asset_type": request.asset_type.value,
            "adjustment": request.adjustment.value,
        }

        def fetch() -> pd.DataFrame:
            try:
                if request.asset_type is AssetType.INDEX:
                    frame = self._client.index_zh_a_hist(
                        symbol=request.symbol,
                        period="daily",
                        start_date=request.start_date,
                        end_date=request.end_date,
                    )
                    frame.attrs["tong_quant_source"] = "akshare:index_zh_a_hist"
                    return frame
                frame = self._client.stock_zh_a_hist(
                    symbol=request.symbol,
                    period="daily",
                    start_date=request.start_date,
                    end_date=request.end_date,
                    adjust=_akshare_adjustment(request.adjustment),
                    timeout=self._timeout_seconds,
                )
                frame.attrs["tong_quant_source"] = "akshare:stock_zh_a_hist"
                return frame
            except Exception:
                frame = self._client.stock_zh_a_hist_tx(
                    symbol=_market_symbol(request.symbol, request.asset_type),
                    start_date=request.start_date,
                    end_date=request.end_date,
                    adjust=_akshare_adjustment(request.adjustment),
                    timeout=self._timeout_seconds,
                )
                normalized = _normalize_tencent_frame(
                    frame,
                    request.symbol,
                    include_symbol=request.asset_type is AssetType.EQUITY,
                )
                normalized.attrs["tong_quant_source"] = "akshare:stock_zh_a_hist_tx"
                return normalized

        return self._fetch(dataset_name, parameters, fetch)

    def trading_calendar(self) -> ProviderResponse:
        return self._fetch(
            "trading_calendar",
            {},
            self._client.tool_trade_date_hist_sina,
        )

    def company_info(self, symbol: str) -> ProviderResponse:
        def fetch() -> pd.DataFrame:
            try:
                frame = self._client.stock_individual_info_em(
                    symbol=symbol,
                    timeout=self._timeout_seconds,
                )
                frame.attrs["tong_quant_source"] = "akshare:stock_individual_info_em"
                return frame
            except Exception:
                frame = self._client.stock_profile_cninfo(symbol=symbol)
                normalized = _normalize_cninfo_company(frame)
                normalized.attrs["tong_quant_source"] = "akshare:stock_profile_cninfo"
                return normalized

        return self._fetch(
            "company_info",
            {"symbol": symbol},
            fetch,
        )

    def a_share_universe(self) -> ProviderResponse:
        def fetch() -> pd.DataFrame:
            try:
                frame = self._client.stock_zh_a_spot_em()
                frame.attrs["tong_quant_source"] = "akshare:stock_zh_a_spot_em"
                return frame
            except Exception:
                frame = self._client.stock_info_a_code_name().rename(
                    columns={"code": "代码", "name": "名称"}
                )
                frame.attrs["tong_quant_source"] = "akshare:stock_info_a_code_name"
                return frame

        return self._fetch(
            "a_share_universe",
            {},
            fetch,
        )

    def financial_statement(self, symbol: str, statement: str) -> ProviderResponse:
        fetchers = {
            "income": self._client.stock_financial_benefit_new_ths,
            "balance": self._client.stock_financial_debt_new_ths,
            "cash_flow": self._client.stock_financial_cash_new_ths,
        }
        try:
            fetcher = fetchers[statement]
        except KeyError as error:
            raise ValueError(f"unsupported financial statement: {statement}") from error

        def fetch() -> pd.DataFrame:
            frame = fetcher(symbol=symbol, indicator="按报告期")
            frame.attrs["tong_quant_source"] = f"akshare:financial:{statement}"
            return frame

        return self._fetch(
            "fundamental_facts",
            {"symbol": symbol, "statement": statement},
            fetch,
        )

    def st_stocks(self) -> ProviderResponse:
        return self._fetch(
            "instrument_status_st",
            {},
            self._client.stock_zh_a_st_em,
        )

    def suspended_stocks(self) -> ProviderResponse:
        return self._fetch(
            "instrument_status_suspended",
            {},
            self._client.stock_zh_a_stop_em,
        )

    def delisted_stocks(self, exchange: str) -> ProviderResponse:
        fetchers = {
            "sh": self._client.stock_info_sh_delist,
            "sz": self._client.stock_info_sz_delist,
        }
        try:
            fetcher = fetchers[exchange]
        except KeyError as error:
            raise ValueError(f"unsupported delisting exchange: {exchange}") from error

        return self._fetch(
            "instrument_status_delisted",
            {"exchange": exchange},
            fetcher,
        )

    def index_membership(self, symbol: str) -> ProviderResponse:
        if symbol not in self.supported_csi_indices:
            raise ValueError(
                "historical calibration currently reserves CSI300, CSI500, and CSI1000"
            )
        def fetch() -> pd.DataFrame:
            frame = self._client.index_stock_cons_csindex(symbol=symbol)
            frame.attrs["tong_quant_source"] = "akshare:index_stock_cons_csindex"
            return frame

        return self._fetch(
            "index_membership",
            {"symbol": symbol},
            fetch,
        )

    def corporate_actions(self, symbol: str) -> ProviderResponse:
        def fetch() -> pd.DataFrame:
            frame = self._client.stock_fhps_detail_em(symbol=symbol)
            frame.attrs["tong_quant_source"] = "akshare:stock_fhps_detail_em"
            return frame

        return self._fetch(
            "corporate_actions",
            {"symbol": symbol},
            fetch,
        )

    def suspension_events(self, on_date: str) -> ProviderResponse:
        def fetch() -> pd.DataFrame:
            frame = self._client.stock_tfp_em(date=on_date)
            frame.attrs["tong_quant_source"] = "akshare:stock_tfp_em"
            return frame

        return self._fetch(
            "security_lifecycle_suspension",
            {"date": on_date},
            fetch,
        )

    def shenzhen_name_changes(self) -> ProviderResponse:
        def fetch() -> pd.DataFrame:
            frame = self._client.stock_info_sz_change_name(symbol="简称变更")
            frame.attrs["tong_quant_source"] = "akshare:stock_info_sz_change_name"
            return frame

        return self._fetch("security_lifecycle_name_change_sz", {}, fetch)

    def fundamental_publication_schedule(self, period_end: str) -> ProviderResponse:
        def fetch() -> pd.DataFrame:
            frame = self._client.stock_yysj_em(symbol="沪深A股", date=period_end)
            frame.attrs["tong_quant_source"] = "akshare:stock_yysj_em"
            return frame

        return self._fetch(
            "fundamental_publications_schedule",
            {"period_end": period_end},
            fetch,
        )

    def fundamental_disclosures(
        self,
        symbol: str,
        *,
        start_date: str,
        end_date: str,
        category: str = "",
    ) -> ProviderResponse:
        def fetch() -> pd.DataFrame:
            frame = self._client.stock_zh_a_disclosure_report_cninfo(
                symbol=symbol,
                market="沪深京",
                category=category,
                start_date=start_date,
                end_date=end_date,
            )
            frame.attrs["tong_quant_source"] = (
                "akshare:stock_zh_a_disclosure_report_cninfo"
            )
            return frame

        return self._fetch(
            "fundamental_publications_disclosure",
            {
                "symbol": symbol,
                "start_date": start_date,
                "end_date": end_date,
                "category": category,
            },
            fetch,
        )

    def _fetch(
        self,
        dataset_name: str,
        parameters: dict[str, Any],
        fetch: Callable[[], pd.DataFrame],
    ) -> ProviderResponse:
        if self._cache is not None:
            cached = self._cache.get(dataset_name, parameters)
            if cached is not None:
                return ProviderResponse(dataset=cached, cache_hit=True)

        frame = self._call_with_retry(dataset_name, fetch).copy()
        source = str(frame.attrs.get("tong_quant_source", self.source_id))
        dataset = RawDataset(
            dataset=dataset_name,
            frame=frame,
            retrieved_at=self._clock(),
            source=source,
            parameters=parameters,
            raw_data_hash=dataframe_sha256(frame, parameters),
        )
        if self._cache is not None:
            self._cache.put(dataset)
        return ProviderResponse(dataset=dataset, cache_hit=False)

    def _call_with_retry(
        self,
        dataset_name: str,
        fetch: Callable[[], pd.DataFrame],
    ) -> pd.DataFrame:
        last_error: Exception | None = None
        for attempt in range(1, self._max_attempts + 1):
            try:
                return fetch()
            except Exception as error:
                last_error = error
                if attempt < self._max_attempts:
                    self._sleeper(self._retry_delay_seconds * attempt)
        raise DataProviderError(
            f"AKShare dataset {dataset_name} failed after {self._max_attempts} attempts"
        ) from last_error


def _akshare_adjustment(adjustment: Adjustment) -> str:
    return {
        Adjustment.NONE: "",
        Adjustment.FORWARD: "qfq",
        Adjustment.BACKWARD: "hfq",
    }[adjustment]


def _market_symbol(symbol: str, asset_type: AssetType) -> str:
    if asset_type is AssetType.INDEX:
        return f"sz{symbol}" if symbol.startswith("399") else f"sh{symbol}"
    if symbol.startswith(("6", "9")):
        return f"sh{symbol}"
    if symbol.startswith(("4", "8")):
        return f"bj{symbol}"
    return f"sz{symbol}"


def _normalize_tencent_frame(
    frame: pd.DataFrame,
    symbol: str,
    *,
    include_symbol: bool,
) -> pd.DataFrame:
    normalized = frame.rename(
        columns={
            "date": "日期",
            "open": "开盘",
            "close": "收盘",
            "high": "最高",
            "low": "最低",
            "amount": "成交量",
        }
    ).copy()
    normalized["成交额"] = 0
    if include_symbol:
        normalized["股票代码"] = symbol
    return normalized


def _normalize_cninfo_company(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["item", "value"])
    row = frame.iloc[0]
    mapping = {
        "股票代码": row.get("A股代码"),
        "股票简称": row.get("A股简称"),
        "行业": row.get("所属行业"),
        "上市时间": row.get("上市日期"),
    }
    return pd.DataFrame({"item": mapping.keys(), "value": mapping.values()})
