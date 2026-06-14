from datetime import date
from decimal import Decimal

from tong_quant.domain.enums import Market
from tong_quant.domain.models import Instrument
from tong_quant.markets.base import MarketRules, PriceLimit


class GlobalEquityRules(MarketRules):
    def __init__(self, market: Market) -> None:
        if market is Market.CHINA_A:
            raise ValueError("use ChinaAShareRules for A-shares")
        self.market = market

    def normalize_buy_quantity(self, instrument: Instrument, quantity: int) -> int:
        if quantity <= 0:
            return 0
        lot_size = instrument.lot_size
        return quantity // lot_size * lot_size

    def normalize_sell_quantity(self, instrument: Instrument, quantity: int) -> int:
        if quantity <= 0:
            return 0
        lot_size = instrument.lot_size
        return quantity // lot_size * lot_size

    def earliest_sell_date(self, buy_date: date) -> date:
        return buy_date

    def daily_price_limit(
        self,
        previous_close: Decimal,
        *,
        is_special_treatment: bool = False,
        is_initial_listing_period: bool = False,
    ) -> PriceLimit:
        del previous_close, is_special_treatment, is_initial_listing_period
        return PriceLimit(lower=None, upper=None)
