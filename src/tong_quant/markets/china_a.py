from datetime import date
from decimal import Decimal

from tong_quant.core.exceptions import MarketRuleEvidenceUnavailableError
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
        del buy_date
        raise MarketRuleEvidenceUnavailableError(
            "A-share sellability requires an exchange trading calendar and dated position lots"
        )

    def daily_price_limit(
        self,
        previous_close: Decimal,
        *,
        is_special_treatment: bool = False,
        is_initial_listing_period: bool = False,
    ) -> PriceLimit:
        del previous_close, is_special_treatment, is_initial_listing_period
        raise MarketRuleEvidenceUnavailableError(
            "A-share price limits require exchange, board, trade date, and dated status evidence"
        )
