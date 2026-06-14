from datetime import date
from decimal import Decimal

from tong_quant.domain.enums import Market
from tong_quant.domain.models import Instrument
from tong_quant.markets.china_a import ChinaAShareRules
from tong_quant.markets.global_equity import GlobalEquityRules


def test_a_share_buy_quantity_uses_board_lot() -> None:
    instrument = Instrument(
        symbol="600000",
        market=Market.CHINA_A,
        name="Example",
        lot_size=100,
    )
    rules = ChinaAShareRules()

    assert rules.normalize_buy_quantity(instrument, 250) == 200


def test_a_share_has_t_plus_one_sale_constraint() -> None:
    rules = ChinaAShareRules()

    assert rules.earliest_sell_date(date(2026, 1, 5)) == date(2026, 1, 6)


def test_a_share_standard_price_limit() -> None:
    limit = ChinaAShareRules().daily_price_limit(Decimal("10.00"))

    assert limit.lower == Decimal("9.00")
    assert limit.upper == Decimal("11.00")


def test_global_market_can_sell_same_day_by_default() -> None:
    rules = GlobalEquityRules(Market.US)

    assert rules.earliest_sell_date(date(2026, 1, 5)) == date(2026, 1, 5)
