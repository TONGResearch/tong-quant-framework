from typing import cast

from tong_quant.config.settings import ResearchSettings
from tong_quant.research.engine import ResearchEngine
from tong_quant.research.financial import FinancialResearchModule
from tong_quant.research.industry import IndustryResearchModule
from tong_quant.research.interfaces import ResearchModule, ResearchRepository
from tong_quant.research.investment import (
    InvestmentAssessmentBuilder,
    InvestmentScoreConfig,
)
from tong_quant.research.pattern import PatternResearchModule
from tong_quant.research.policy import PolicyResearchModule
from tong_quant.research.reporting import DefaultResearchReportBuilder
from tong_quant.research.technical import TechnicalResearchModule
from tong_quant.research.trend import TrendResearchModule
from tong_quant.research.value import ValueResearchModule


def research_engine_from_settings(
    settings: ResearchSettings,
    *,
    repository: ResearchRepository | None = None,
) -> ResearchEngine:
    technical = settings.technical
    trend = settings.trend
    pattern = settings.pattern
    modules = cast(
        tuple[ResearchModule, ...],
        (
            PolicyResearchModule(),
            FinancialResearchModule(),
            TechnicalResearchModule(
                short_ma_period=technical.short_ma_period,
                long_ma_period=technical.long_ma_period,
                position_period=technical.position_period,
            ),
            IndustryResearchModule(),
            ValueResearchModule(),
            TrendResearchModule(
                breakout_period=trend.breakout_period,
                volume_period=trend.volume_period,
                atr_period=trend.atr_period,
                confirmation_threshold=trend.confirmation_threshold,
            ),
            PatternResearchModule(
                rising_stocks_threshold=pattern.rising_stocks_threshold,
                volume_period=pattern.volume_period,
            ),
        ),
    )
    return ResearchEngine(
        modules=modules,
        report_builder=DefaultResearchReportBuilder(
            model_version=settings.model_version
        ),
        repository=repository,
    )


def investment_assessment_builder_from_settings(
    settings: ResearchSettings,
) -> InvestmentAssessmentBuilder:
    investment_score = settings.investment_score
    return InvestmentAssessmentBuilder(
        InvestmentScoreConfig(
            weights=investment_score.weights,
            model_version=investment_score.model_version,
            maximum_component_weight=investment_score.maximum_component_weight,
            require_all_components=investment_score.require_all_components,
        )
    )


__all__ = ["investment_assessment_builder_from_settings", "research_engine_from_settings"]
