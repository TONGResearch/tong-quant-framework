from collections.abc import Sequence
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from tong_quant.data.models import DailyBarRequest, RawDataset
from tong_quant.domain.enums import AssetType, Market
from tong_quant.domain.models import Bar, Instrument, TradingSession

SHANGHAI = ZoneInfo("Asia/Shanghai")
MARKET_CLOSE = time(hour=15)


def normalize_daily_bars(
    dataset: RawDataset,
    request: DailyBarRequest,
    instrument: Instrument,
) -> list[Bar]:
    bars: list[Bar] = []
    for row in dataset.frame.to_dict(orient="records"):
        trade_date = _to_date(row["日期"])
        timestamp = datetime.combine(trade_date, MARKET_CLOSE, tzinfo=SHANGHAI)
        available_at = timestamp + timedelta(minutes=1)
        if available_at > dataset.retrieved_at.astimezone(SHANGHAI):
            continue
        bars.append(
            Bar(
                instrument=instrument,
                timestamp=timestamp,
                available_at=available_at,
                open=_decimal(row["开盘"]),
                high=_decimal(row["最高"]),
                low=_decimal(row["最低"]),
                close=_decimal(row["收盘"]),
                volume=_decimal(row["成交量"]),
                turnover=_optional_decimal(row.get("成交额")),
                adjustment=request.adjustment,
                source=dataset.source,
                ingested_at=dataset.retrieved_at,
            )
        )
    return bars


def normalize_trading_calendar(dataset: RawDataset) -> list[TradingSession]:
    sessions = []
    for raw_date in dataset.frame["trade_date"].tolist():
        trade_date = _to_date(raw_date)
        known_at = datetime.combine(trade_date, time.min, tzinfo=SHANGHAI)
        sessions.append(
            TradingSession(
                market=Market.CHINA_A,
                trade_date=trade_date,
                is_open=True,
                available_at=known_at,
                source=dataset.source,
            )
        )
    return sessions


def normalize_company_info(dataset: RawDataset, symbol: str) -> Instrument:
    values = {
        str(row["item"]): row["value"]
        for row in dataset.frame.to_dict(orient="records")
        if pd.notna(row["item"])
    }
    listing_date = _optional_date(values.get("上市时间"))
    return Instrument(
        symbol=symbol,
        market=Market.CHINA_A,
        name=str(values.get("股票简称") or symbol),
        asset_type=AssetType.EQUITY,
        currency="CNY",
        lot_size=100,
        exchange=infer_exchange(symbol),
        industry=_optional_text(values.get("行业")),
        listing_date=listing_date,
        available_at=dataset.retrieved_at,
        source=dataset.source,
    )


def normalize_universe(dataset: RawDataset) -> list[Instrument]:
    instruments = []
    for row in dataset.frame.to_dict(orient="records"):
        symbol = str(row["代码"]).split(".")[0].zfill(6)
        instruments.append(
            Instrument(
                symbol=symbol,
                market=Market.CHINA_A,
                name=str(row["名称"]),
                asset_type=AssetType.EQUITY,
                currency="CNY",
                lot_size=100,
                exchange=infer_exchange(symbol),
                available_at=dataset.retrieved_at,
                source=dataset.source,
            )
        )
    return instruments


def build_index_instrument(symbol: str, retrieved_at: datetime) -> Instrument:
    return Instrument(
        symbol=symbol,
        market=Market.CHINA_A,
        name=symbol,
        asset_type=AssetType.INDEX,
        currency="CNY",
        lot_size=1,
        exchange=infer_exchange(symbol),
        available_at=retrieved_at,
        source="akshare",
    )


def build_bar_instrument(
    symbol: str,
    asset_type: AssetType,
    available_at: datetime,
) -> Instrument:
    return Instrument(
        symbol=symbol,
        market=Market.CHINA_A,
        name=symbol,
        asset_type=asset_type,
        currency="CNY",
        lot_size=1 if asset_type is AssetType.INDEX else 100,
        exchange=infer_exchange(symbol),
        available_at=available_at,
        source="akshare",
    )


def first_bar_available_at(dataset: RawDataset) -> datetime:
    first_date = min(_to_date(value) for value in dataset.frame["日期"].tolist())
    return datetime.combine(first_date, MARKET_CLOSE, tzinfo=SHANGHAI) + timedelta(minutes=1)


def infer_exchange(symbol: str) -> str:
    if symbol.startswith(("6", "9")):
        return "XSHG"
    if symbol.startswith(("0", "2", "3")):
        return "XSHE"
    if symbol.startswith(("4", "8")):
        return "XBSE"
    return "UNKNOWN"


def _to_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value)[:10]
    return date.fromisoformat(text)


def _optional_date(value: Any) -> date | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).replace(".0", "").strip()
    if len(text) == 8 and text.isdigit():
        return datetime.strptime(text, "%Y%m%d").date()
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def _optional_decimal(value: Any) -> Decimal | None:
    if value is None or pd.isna(value):
        return None
    return _decimal(value)


def _optional_text(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def normalize_instruments(datasets: Sequence[RawDataset]) -> list[Instrument]:
    instruments: list[Instrument] = []
    for dataset in datasets:
        if dataset.dataset == "a_share_universe":
            instruments.extend(normalize_universe(dataset))
    return instruments
