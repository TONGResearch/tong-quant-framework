from dataclasses import dataclass

from tong_quant.domain.enums import ValidationModuleName
from tong_quant.validation.base import (
    assessment,
    integrity_checks,
    observed_accuracy,
    resolved_samples,
    sample_confidence,
)
from tong_quant.validation.models import (
    ValidationModuleResult,
    ValidationRequest,
    ValidationSplit,
)


@dataclass(frozen=True, slots=True)
class HistoricalValidationModule:
    module: ValidationModuleName = ValidationModuleName.HISTORICAL
    model_version: str = "historical-v0.6"

    def evaluate(
        self,
        request: ValidationRequest,
        splits: tuple[ValidationSplit, ...],
    ) -> ValidationModuleResult:
        del splits
        resolved = resolved_samples(request.samples)
        checks = integrity_checks(request.samples, as_of=request.requested_at)
        score = observed_accuracy(resolved) if resolved else None
        confidence = sample_confidence(len(resolved), request.minimum_observations)
        return ValidationModuleResult(
            assessment=assessment(
                module=self.module,
                score=score,
                confidence=confidence,
                sample_size=len(resolved),
                evaluated_at=request.requested_at,
                metrics={
                    "resolved_samples": len(resolved),
                    "unresolved_samples": len(request.samples) - len(resolved),
                    "research_accuracy": score,
                },
                findings=(
                    f"Historical validation evaluated {len(resolved)} resolved samples",
                ),
                risks=(
                    "Historical accuracy does not establish future reliability",
                ),
                limitations=(
                    "Validation consumes stored historical outputs; provider "
                    "replay is an adapter boundary",
                ),
                checks=checks,
                model_version=self.model_version,
            )
        )


__all__ = ["HistoricalValidationModule"]
