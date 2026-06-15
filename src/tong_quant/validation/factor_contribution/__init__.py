from dataclasses import dataclass

from tong_quant.domain.enums import ValidationModuleName
from tong_quant.validation.base import assessment, pearson, sample_confidence
from tong_quant.validation.models import (
    FactorContribution,
    ValidationModuleResult,
    ValidationRequest,
    ValidationSplit,
)


@dataclass(frozen=True, slots=True)
class FactorContributionValidationModule:
    module: ValidationModuleName = ValidationModuleName.FACTOR_CONTRIBUTION
    model_version: str = "factor-contribution-v0.6"
    stability_threshold: float = 0.05

    def evaluate(
        self,
        request: ValidationRequest,
        splits: tuple[ValidationSplit, ...],
    ) -> ValidationModuleResult:
        del splits
        resolved = tuple(
            sample
            for sample in request.samples
            if sample.outcome.succeeded is not None and sample.factor_scores
        )
        factor_names = sorted(
            {name for sample in resolved for name in sample.factor_scores}
        )
        contributions: list[FactorContribution] = []
        for factor in factor_names:
            eligible = tuple(
                sample for sample in resolved if factor in sample.factor_scores
            )
            values = [sample.factor_scores[factor] / 100 for sample in eligible]
            outcomes = [1.0 if sample.outcome.succeeded else 0.0 for sample in eligible]
            success_values = [
                value
                for value, outcome in zip(values, outcomes, strict=True)
                if outcome == 1
            ]
            failure_values = [
                value
                for value, outcome in zip(values, outcomes, strict=True)
                if outcome == 0
            ]
            gap = (
                100
                * (
                    sum(success_values) / len(success_values)
                    - sum(failure_values) / len(failure_values)
                )
                if success_values and failure_values
                else 0.0
            )
            full_predictions = [
                sum(sample.factor_scores.values())
                / len(sample.factor_scores)
                / 100
                for sample in eligible
            ]
            without_predictions = [
                _prediction_without(sample.factor_scores, factor)
                for sample in eligible
            ]
            full_brier = _brier(full_predictions, outcomes)
            without_brier = _brier(without_predictions, outcomes)
            correlation = pearson(values, outcomes)
            delta = without_brier - full_brier
            contributions.append(
                FactorContribution(
                    factor=factor,
                    sample_size=len(eligible),
                    success_score_gap=round(gap, 6),
                    ablation_brier_delta=round(delta, 6),
                    stable=delta >= self.stability_threshold and correlation > 0,
                )
            )
        positive = sum(item.ablation_brier_delta > 0 for item in contributions)
        score = (
            100 * positive / len(contributions) if contributions else None
        )
        return ValidationModuleResult(
            assessment=assessment(
                module=self.module,
                score=score,
                confidence=sample_confidence(
                    len(resolved), request.minimum_observations
                ),
                sample_size=len(resolved),
                evaluated_at=request.requested_at,
                metrics={
                    "factors_evaluated": len(contributions),
                    "positive_incremental_factors": positive,
                },
                findings=(
                    f"{positive} of {len(contributions)} factors improved the "
                    "registered outcome model",
                ),
                risks=(
                    "Correlated factors can share or obscure incremental contribution",
                ),
                limitations=(
                    "V0.6 uses deterministic ablation and does not fit a black-box explainer",
                ),
                model_version=self.model_version,
            ),
            factor_contributions=tuple(contributions),
        )


def _prediction_without(scores: dict[str, float], excluded: str) -> float:
    remaining = [score for name, score in scores.items() if name != excluded]
    return sum(remaining) / len(remaining) / 100 if remaining else 0.5


def _brier(predictions: list[float], outcomes: list[float]) -> float:
    if not predictions:
        return 0.0
    return sum(
        (prediction - outcome) ** 2
        for prediction, outcome in zip(predictions, outcomes, strict=True)
    ) / len(predictions)


__all__ = ["FactorContributionValidationModule"]
