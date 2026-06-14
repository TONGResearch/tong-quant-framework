from decimal import Decimal

from tong_quant.domain.enums import Market, SecurityStatus
from tong_quant.screening.policies.base import ScreeningPolicy
from tong_quant.screening.policies.common import COMMON_RISK_FLAGS


def us_policy() -> ScreeningPolicy:
    return ScreeningPolicy(
        market=Market.US,
        rejected_statuses=frozenset(
            {
                SecurityStatus.DELISTING,
                SecurityStatus.DELISTED,
                SecurityStatus.SUSPENDED,
            }
        ),
        rejected_risk_flags=COMMON_RISK_FLAGS,
        minimum_average_turnover=Decimal("0"),
        minimum_financial_health_score=0,
    )
