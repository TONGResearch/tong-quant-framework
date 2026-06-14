from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from tong_quant.domain.enums import Market
from tong_quant.domain.models import Instrument


@dataclass(frozen=True, slots=True)
class PriceLimit:
    lower: Decimal | None
    upper: Decimal | None


class MarketRules(ABC):
    market: Market

    @abstractmethod
    def normalize_buy_quantity(self, instrument: Instrument, quantity: int) -> int:
        """Return a valid order quantity for this market."""

    @abstractmethod
    def normalize_sell_quantity(self, instrument: Instrument, quantity: int) -> int:
        """Return a valid sell quantity for this market."""

    @abstractmethod
    def earliest_sell_date(self, buy_date: date) -> date:
        """Return the earliest calendar date on which a new position may be sold."""

    @abstractmethod
    def daily_price_limit(
        self,
        previous_close: Decimal,
        *,
        is_special_treatment: bool = False,
        is_initial_listing_period: bool = False,
    ) -> PriceLimit:
        """Return the applicable daily price range."""
