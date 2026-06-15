from typing import cast

from tong_quant.config.settings import ValidationSettings
from tong_quant.validation.decision_journal import DecisionJournalValidationModule
from tong_quant.validation.engine import ValidationEngine
from tong_quant.validation.factor_contribution import (
    FactorContributionValidationModule,
)
from tong_quant.validation.historical import HistoricalValidationModule
from tong_quant.validation.interfaces import ValidationModule, ValidationRepository
from tong_quant.validation.market_regime import MarketRegimeValidationModule
from tong_quant.validation.out_of_sample import OutOfSampleValidationModule
from tong_quant.validation.portfolio_risk import PortfolioRiskValidationModule
from tong_quant.validation.reporting import DefaultValidationReportBuilder
from tong_quant.validation.research_accuracy import (
    ResearchAccuracyValidationModule,
)
from tong_quant.validation.thesis import ThesisValidationModule
from tong_quant.validation.walk_forward import WalkForwardValidationModule


def validation_engine_from_settings(
    settings: ValidationSettings,
    *,
    repository: ValidationRepository | None = None,
) -> ValidationEngine:
    modules = cast(
        tuple[ValidationModule, ...],
        (
            HistoricalValidationModule(),
            WalkForwardValidationModule(
                minimum_windows=settings.robustness.minimum_windows
            ),
            OutOfSampleValidationModule(),
            MarketRegimeValidationModule(),
            ThesisValidationModule(),
            FactorContributionValidationModule(),
            ResearchAccuracyValidationModule(),
            DecisionJournalValidationModule(),
            PortfolioRiskValidationModule(
                maximum_category_weight=settings.portfolio.maximum_category_weight,
                maximum_hhi=settings.portfolio.maximum_hhi,
            ),
        ),
    )
    return ValidationEngine(
        modules=modules,
        report_builder=DefaultValidationReportBuilder(
            model_version=settings.model_version
        ),
        repository=repository,
    )


__all__ = ["validation_engine_from_settings"]
