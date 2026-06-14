from tong_quant.domain.enums import Market
from tong_quant.markets.base import MarketRules
from tong_quant.markets.china_a import ChinaAShareRules
from tong_quant.markets.global_equity import GlobalEquityRules


def build_market_rules(market_name: str) -> MarketRules:
    market = Market(market_name)
    if market is Market.CHINA_A:
        return ChinaAShareRules()
    return GlobalEquityRules(market)
