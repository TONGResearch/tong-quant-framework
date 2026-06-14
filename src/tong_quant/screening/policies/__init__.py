from tong_quant.domain.enums import Market
from tong_quant.screening.policies.base import ScreeningPolicy
from tong_quant.screening.policies.china_a import china_a_policy
from tong_quant.screening.policies.hong_kong import hong_kong_policy
from tong_quant.screening.policies.malaysia import malaysia_policy
from tong_quant.screening.policies.us import us_policy


def default_market_policies() -> dict[Market, ScreeningPolicy]:
    return {
        Market.CHINA_A: china_a_policy(),
        Market.US: us_policy(),
        Market.HONG_KONG: hong_kong_policy(),
        Market.MALAYSIA: malaysia_policy(),
    }


__all__ = [
    "ScreeningPolicy",
    "china_a_policy",
    "default_market_policies",
    "hong_kong_policy",
    "malaysia_policy",
    "us_policy",
]
