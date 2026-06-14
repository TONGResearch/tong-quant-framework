from dataclasses import dataclass
from decimal import Decimal

from tong_quant.domain.enums import Market, SecurityStatus
from tong_quant.screening.hard_screening import (
    DataQualityRule,
    FinancialHealthRule,
    HardScreenPipeline,
    LiquidityRule,
    RiskFlagRule,
    SecurityLifecycleRule,
)


@dataclass(frozen=True, slots=True)
class ScreeningPolicy:
    market: Market
    rejected_statuses: frozenset[SecurityStatus]
    rejected_risk_flags: frozenset[str]
    minimum_average_turnover: Decimal | None
    minimum_financial_health_score: float | None
    require_liquidity_data: bool = True
    require_financial_health_data: bool = True

    def pipeline(self) -> HardScreenPipeline:
        return HardScreenPipeline(
            rules=(
                DataQualityRule(),
                SecurityLifecycleRule(self.rejected_statuses),
                RiskFlagRule(self.rejected_risk_flags),
                LiquidityRule(
                    self.minimum_average_turnover,
                    require_metric=self.require_liquidity_data,
                ),
                FinancialHealthRule(
                    self.minimum_financial_health_score,
                    require_metric=self.require_financial_health_data,
                ),
            )
        )
