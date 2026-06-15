from dataclasses import dataclass

from tong_quant.domain.enums import ValidationModuleName, ValidationSplitKind
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
class WalkForwardValidationModule:
    module: ValidationModuleName = ValidationModuleName.WALK_FORWARD
    model_version: str = "walk-forward-v0.6"
    minimum_windows: int = 3

    def evaluate(
        self,
        request: ValidationRequest,
        splits: tuple[ValidationSplit, ...],
    ) -> ValidationModuleResult:
        validation_splits = tuple(
            split
            for split in splits
            if split.kind is ValidationSplitKind.VALIDATION
        )
        window_scores: list[float] = []
        for split in validation_splits:
            samples = tuple(
                sample
                for sample in request.samples
                if split.start_date <= sample.decision_at.date() <= split.end_date
                and sample.outcome.succeeded is not None
            )
            if samples:
                window_scores.append(observed_accuracy(samples))
        score = sum(window_scores) / len(window_scores) if window_scores else None
        confidence = min(
            sample_confidence(len(request.samples), request.minimum_observations),
            100 * len(window_scores) / self.minimum_windows,
        )
        stability = stability_score(window_scores)
        if score is not None:
            score = (score + stability) / 2
        return ValidationModuleResult(
            assessment=assessment(
                module=self.module,
                score=score,
                confidence=confidence,
                sample_size=len(request.samples),
                evaluated_at=request.requested_at,
                metrics={
                    "completed_windows": len(window_scores),
                    "window_accuracy": ",".join(f"{value:.4f}" for value in window_scores),
                    "window_stability": round(stability, 4),
                },
                findings=(
                    f"{len(window_scores)} walk-forward validation windows contained outcomes",
                ),
                risks=("Large window dispersion indicates temporal instability",),
                limitations=(
                    "Windows without resolved outcomes do not contribute a favorable default",
                ),
                model_version=self.model_version,
            )
        )


__all__ = ["WalkForwardValidationModule"]
