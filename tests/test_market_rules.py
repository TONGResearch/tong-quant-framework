from datetime import date
from decimal import Decimal

import pytest

from tong_quant.core.exceptions import MarketRuleEvidenceUnavailableError
from tong_quant.domain.enums import Market
from tong_quant.domain.models import Instrument
from tong_quant.markets.china_a import ChinaAShareRules
from tong_quant.markets.global_equity import GlobalEquityRules


@pytest.mark.parametrize("quantity", [0, 1, 250])
def test_a_share_quantities_fail_closed_without_dated_lot_rules(quantity: int) -> None:
    instrument = Instrument(
        symbol="600000",
        market=Market.CHINA_A,
        name="Example",
    )
    rules = ChinaAShareRules()

    with pytest.raises(MarketRuleEvidenceUnavailableError, match="lot-rule"):
        rules.normalize_buy_quantity(instrument, quantity)
    with pytest.raises(MarketRuleEvidenceUnavailableError, match="position-lot"):
        rules.normalize_sell_quantity(instrument, quantity)


def test_a_share_sellability_fails_closed_without_calendar_evidence() -> None:
    rules = ChinaAShareRules()

    with pytest.raises(MarketRuleEvidenceUnavailableError, match="trading calendar"):
        rules.earliest_sell_date(date(2026, 1, 5))


def test_a_share_price_limit_fails_closed_without_dated_board_rules() -> None:
    with pytest.raises(MarketRuleEvidenceUnavailableError, match="trade date"):
        ChinaAShareRules().daily_price_limit(Decimal("10.00"))

@pytest.mark.parametrize("market", [Market.US, Market.HONG_KONG, Market.MALAYSIA])
def test_global_quantities_fail_closed_without_dated_rules(market: Market) -> None:
    instrument = Instrument(symbol="TEST", market=market, name="Example")
    rules = GlobalEquityRules(market)

    with pytest.raises(MarketRuleEvidenceUnavailableError, match="account-rule"):
        rules.normalize_buy_quantity(instrument, 250)
    with pytest.raises(MarketRuleEvidenceUnavailableError, match="account-rule"):
        rules.normalize_sell_quantity(instrument, 250)


@pytest.mark.parametrize("market", [Market.US, Market.HONG_KONG, Market.MALAYSIA])
def test_global_sellability_fails_closed_without_dated_rules(market: Market) -> None:
    rules = GlobalEquityRules(market)

    with pytest.raises(MarketRuleEvidenceUnavailableError, match="settlement"):
        rules.earliest_sell_date(date(2026, 1, 5))


@pytest.mark.parametrize("market", [Market.US, Market.HONG_KONG, Market.MALAYSIA])
def test_global_price_limits_fail_closed_without_dated_rules(market: Market) -> None:
    rules = GlobalEquityRules(market)

    with pytest.raises(MarketRuleEvidenceUnavailableError, match="exchange-rule"):
        rules.daily_price_limit(Decimal("10.00"))
