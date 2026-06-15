from dataclasses import dataclass

from tong_quant.domain.enums import ValidationModuleName
from tong_quant.validation.base import (
    assessment,
    observed_accuracy,
    sample_confidence,
    stability_score,
)
from tong_quant.validation.models import (
    ValidationModuleResult,
    ValidationRequest,
    ValidationSplit,
)


@dataclass(frozen=True, slots=True)
class MarketRegimeValidationModule:
    module: ValidationModuleName = ValidationModuleName.MARKET_REGIME
    model_version: str = "market-regime-validation-v0.6"

    def evaluate(
        self,
        request: ValidationRequest,
        splits: tuple[ValidationSplit, ...],
    ) -> ValidationModuleResult:
        del splits
        grouped: dict[str, list[object]] = {}
        for sample in request.samples:
            if sample.market_regime is None or sample.outcome.succeeded is None:
                continue
            grouped.setdefault(sample.market_regime.value, []).append(sample)
        regime_scores = {
            regime: observed_accuracy(samples)  # type: ignore[arg-type]
            for regime, samples in grouped.items()
        }
        score_values = list(regime_scores.values())
        score = sum(score_values) / len(score_values) if score_values else None
        stability = stability_score(score_values)
        if score is not None:
            score = (score + stability) / 2
        sample_size = sum(len(samples) for samples in grouped.values())
        return ValidationModuleResult(
            assessment=assessment(
                module=self.module,
                score=score,
                confidence=sample_confidence(
                    sample_size, request.minimum_observations
                ),
                sample_size=sample_size,
                evaluated_at=request.requested_at,
                metrics={
                    **{
                        f"{regime}_accuracy": round(value, 4)
                        for regime, value in regime_scores.items()
                    },
                    "regime_stability": round(stability, 4),
                    "regimes_observed": len(regime_scores),
                },
                findings=(
                    f"Research accuracy was separated across {len(regime_scores)} regimes",
                ),
                risks=(
                    "Regime-conditioned differences may reflect sector or sample composition",
                ),
                limitations=(
                    "Regime remains an explanatory variable and is not validated as a trade gate",
                ),
                model_version=self.model_version,
            )
        )


__all__ = ["MarketRegimeValidationModule"]
