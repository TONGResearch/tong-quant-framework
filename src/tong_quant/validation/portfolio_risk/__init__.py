from dataclasses import dataclass

from tong_quant.domain.enums import ValidationModuleName
from tong_quant.validation.base import assessment
from tong_quant.validation.models import (
    ConcentrationMetric,
    IntegrityCheck,
    PortfolioResearchPosition,
    PortfolioRiskSummary,
    ValidationModuleResult,
    ValidationRequest,
    ValidationSplit,
)


@dataclass(frozen=True, slots=True)
class PortfolioRiskValidationModule:
    module: ValidationModuleName = ValidationModuleName.PORTFOLIO_RISK
    model_version: str = "portfolio-research-risk-v0.6"
    maximum_category_weight: float = 0.35
    maximum_hhi: float = 0.25

    def evaluate(
        self,
        request: ValidationRequest,
        splits: tuple[ValidationSplit, ...],
    ) -> ValidationModuleResult:
        del splits
        positions = tuple(
            sample.portfolio_position
            for sample in request.samples
            if sample.portfolio_position is not None
        )
        total_weight = sum(position.research_weight for position in positions)
        concentrations = tuple(
            _concentration(
                positions,
                dimension,
                self.maximum_category_weight,
                self.maximum_hhi,
            )
            for dimension in ("industry", "country", "theme", "style")
        )
        breaches = sum(metric.breached for metric in concentrations)
        score = 100 * (1 - breaches / len(concentrations)) if positions else None
        summary = PortfolioRiskSummary(
            total_weight=round(total_weight, 6),
            concentrations=concentrations,
        )
        checks = (
            IntegrityCheck(
                check_id="portfolio_research_weight",
                passed=total_weight <= 1 + 1e-9,
                checked_at=request.requested_at,
                reasons=(
                    ("Portfolio research weights do not exceed 100 percent",)
                    if total_weight <= 1 + 1e-9
                    else ("Portfolio research weights exceed 100 percent",)
                ),
            ),
        )
        return ValidationModuleResult(
            assessment=assessment(
                module=self.module,
                score=score,
                confidence=min(100.0, total_weight * 100),
                sample_size=len(positions),
                evaluated_at=request.requested_at,
                metrics={
                    "total_research_weight": round(total_weight, 6),
                    "concentration_breaches": breaches,
                    **{
                        f"{item.dimension}_maximum_weight": round(
                            item.maximum_weight, 6
                        )
                        for item in concentrations
                    },
                    **{
                        f"{item.dimension}_hhi": round(item.hhi, 6)
                        for item in concentrations
                    },
                },
                findings=(
                    "Industry, country, theme, and style research concentrations were evaluated",
                ),
                risks=(
                    f"{breaches} research concentration dimensions exceeded configured limits",
                ),
                limitations=(
                    "This is research-risk concentration analysis, not "
                    "portfolio return backtesting",
                ),
                checks=checks,
                model_version=self.model_version,
            ),
            portfolio_risk=summary,
        )


def _concentration(
    positions: tuple[PortfolioResearchPosition, ...],
    dimension: str,
    maximum_category_weight: float,
    maximum_hhi: float,
) -> ConcentrationMetric:
    weights: dict[str, float] = {}
    for position in positions:
        category = str(getattr(position, dimension))
        weights[category] = weights.get(category, 0.0) + position.research_weight
    total = sum(weights.values())
    normalized = (
        {category: weight / total for category, weight in weights.items()}
        if total
        else {}
    )
    maximum = max(normalized.values(), default=0.0)
    hhi = sum(weight**2 for weight in normalized.values())
    return ConcentrationMetric(
        dimension=dimension,
        maximum_weight=maximum,
        hhi=hhi,
        category_weights=normalized,
        breached=maximum > maximum_category_weight or hhi > maximum_hhi,
    )


__all__ = ["PortfolioRiskValidationModule"]
