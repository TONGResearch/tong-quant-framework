from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from tong_quant.domain.enums import Market
from tong_quant.domain.models import Instrument
from tong_quant.markets.base import MarketRules, PriceLimit


class ChinaAShareRules(MarketRules):
    market = Market.CHINA_A

    def normalize_buy_quantity(self, instrument: Instrument, quantity: int) -> int:
        if quantity <= 0:
            return 0
        lot_size = instrument.lot_size or 100
        return quantity // lot_size * lot_size

    def normalize_sell_quantity(self, instrument: Instrument, quantity: int) -> int:
        del instrument
        return max(0, quantity)

    def earliest_sell_date(self, buy_date: date) -> date:
        # The trading calendar will replace this calendar-day approximation.
        return buy_date + timedelta(days=1)

    def daily_price_limit(
        self,
        previous_close: Decimal,
        *,
        is_special_treatment: bool = False,
        is_initial_listing_period: bool = False,
    ) -> PriceLimit:
        if is_initial_listing_period:
            return PriceLimit(lower=None, upper=None)
        rate = Decimal("0.05") if is_special_treatment else Decimal("0.10")
        tick = Decimal("0.01")
        lower = (previous_close * (Decimal("1") - rate)).quantize(tick, ROUND_HALF_UP)
        upper = (previous_close * (Decimal("1") + rate)).quantize(tick, ROUND_HALF_UP)
        return PriceLimit(lower=lower, upper=upper)
