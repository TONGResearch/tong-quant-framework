from dataclasses import dataclass

from tong_quant.domain.enums import ValidationModuleName
from tong_quant.validation.base import (
    assessment,
    research_accuracy_metrics,
    sample_confidence,
)
from tong_quant.validation.models import (
    ValidationModuleResult,
    ValidationRequest,
    ValidationSplit,
)


@dataclass(frozen=True, slots=True)
class ResearchAccuracyValidationModule:
    module: ValidationModuleName = ValidationModuleName.RESEARCH_ACCURACY
    model_version: str = "research-accuracy-v0.6"

    def evaluate(
        self,
        request: ValidationRequest,
        splits: tuple[ValidationSplit, ...],
    ) -> ValidationModuleResult:
        del splits
        metrics = research_accuracy_metrics(request.samples)
        score = (
            None
            if metrics is None
            else max(
                0.0,
                metrics.accuracy
                - metrics.calibration_error * 0.5
                - metrics.high_confidence_failure_rate * 0.5,
            )
        )
        sample_size = 0 if metrics is None else metrics.sample_size
        return ValidationModuleResult(
            assessment=assessment(
                module=self.module,
                score=score,
                confidence=sample_confidence(
                    sample_size, request.minimum_observations
                ),
                sample_size=sample_size,
                evaluated_at=request.requested_at,
                metrics=(
                    {"accuracy_available": False}
                    if metrics is None
                    else {
                        "accuracy": metrics.accuracy,
                        "brier_score": metrics.brier_score,
                        "calibration_error": metrics.calibration_error,
                        "high_confidence_failure_rate": (
                            metrics.high_confidence_failure_rate
                        ),
                    }
                ),
                findings=(
                    "Research accuracy and confidence calibration were evaluated separately",
                ),
                risks=(
                    "High-confidence errors receive an explicit reliability penalty",
                ),
                model_version=self.model_version,
            ),
            accuracy=metrics,
        )


__all__ = ["ResearchAccuracyValidationModule"]
