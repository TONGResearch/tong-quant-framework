from datetime import date, datetime

from tong_quant.data.models import FundamentalPublicationEvent, SecurityLifecycleEvent
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Adjustment, AssetType, Market
from tong_quant.domain.models import Bar, FundamentalFact, Instrument, InstrumentStatus


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

    def fundamental_facts(
        self,
        symbol: str,
        market: Market,
        asset_type: AssetType,
        metric: str,
        *,
        as_of: datetime,
        period_end_on_or_before: date | None = None,
    ) -> list[FundamentalFact]:
        return self._store.fundamental_facts(
            symbol,
            market,
            asset_type,
            metric,
            as_of=as_of,
            period_end_on_or_before=period_end_on_or_before,
        )

    def fundamental_revision_history(
        self,
        symbol: str,
        market: Market,
        asset_type: AssetType,
        metric: str,
        *,
        as_of: datetime,
        period_end_on_or_before: date | None = None,
    ) -> list[FundamentalFact]:
        return self._store.fundamental_revision_history(
            symbol,
            market,
            asset_type,
            metric,
            as_of=as_of,
            period_end_on_or_before=period_end_on_or_before,
        )

    def fundamental_publications(
        self,
        symbol: str,
        market: Market,
        asset_type: AssetType,
        *,
        as_of: datetime,
        period_end_on_or_before: date | None = None,
    ) -> list[FundamentalPublicationEvent]:
        return self._store.fundamental_publication_events(
            symbol,
            market,
            asset_type,
            as_of=as_of,
            period_end_on_or_before=period_end_on_or_before,
        )

    def security_lifecycle(
        self,
        symbol: str,
        market: Market,
        asset_type: AssetType,
        *,
        as_of: datetime,
        effective_on_or_before: date | None = None,
    ) -> list[SecurityLifecycleEvent]:
        return self._store.security_lifecycle_events(
            symbol,
            market,
            asset_type,
            as_of=as_of,
            effective_on_or_before=effective_on_or_before,
        )

    def instrument_status(
        self,
        symbol: str,
        market: Market,
        asset_type: AssetType,
        *,
        on_date: date,
        as_of: datetime,
    ) -> InstrumentStatus | None:
        return self._store.instrument_status(
            symbol,
            market,
            asset_type,
            on_date=on_date,
            as_of=as_of,
        )

    def universe(
        self,
        universe: str,
        market: Market,
        *,
        on_date: date,
        as_of: datetime,
        tradable_only: bool = False,
    ) -> list[Instrument]:
        return self._store.universe_as_of(
            universe,
            market,
            on_date=on_date,
            as_of=as_of,
            tradable_only=tradable_only,
        )
