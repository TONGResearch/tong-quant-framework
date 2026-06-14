from datetime import date, datetime

from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Adjustment, AssetType, Market
from tong_quant.domain.models import Bar, Instrument


class MarketDataService:
    """Point-in-time-safe read API for screening, research, and validation."""

    def __init__(self, store: SQLiteStore) -> None:
        self._store = store

    def instrument(
        self,
        symbol: str,
        market: Market,
        asset_type: AssetType,
        *,
        as_of: datetime,
    ) -> Instrument | None:
        return self._store.get_instrument(symbol, market, asset_type, as_of=as_of)

    def daily_bars(
        self,
        symbol: str,
        market: Market,
        asset_type: AssetType,
        start: date,
        end: date,
        *,
        as_of: datetime,
        adjustment: Adjustment = Adjustment.NONE,
    ) -> list[Bar]:
        return self._store.daily_bars(
            symbol,
            market,
            asset_type,
            start,
            end,
            as_of=as_of,
            adjustment=adjustment,
        )

    def trading_days(
        self,
        market: Market,
        start: date,
        end: date,
        *,
        as_of: datetime,
    ) -> list[date]:
        return self._store.trading_days(market, start, end, as_of=as_of)
