from dataclasses import dataclass

from tong_quant.domain.enums import ThesisOutcomeStatus, ValidationModuleName
from tong_quant.validation.base import assessment, sample_confidence
from tong_quant.validation.models import (
    ValidationModuleResult,
    ValidationRequest,
    ValidationSplit,
)


@dataclass(frozen=True, slots=True)
class ThesisValidationModule:
    module: ValidationModuleName = ValidationModuleName.THESIS
    model_version: str = "thesis-validation-v0.6"

    def evaluate(
        self,
        request: ValidationRequest,
        splits: tuple[ValidationSplit, ...],
    ) -> ValidationModuleResult:
        del splits
        counts = {
            status: sum(
                sample.outcome.thesis_status is status for sample in request.samples
            )
            for status in ThesisOutcomeStatus
        }
        resolved = (
            counts[ThesisOutcomeStatus.SUPPORTED]
            + counts[ThesisOutcomeStatus.PARTIALLY_SUPPORTED]
            + counts[ThesisOutcomeStatus.INVALIDATED]
        )
        score = (
            100
            * (
                counts[ThesisOutcomeStatus.SUPPORTED]
                + 0.5 * counts[ThesisOutcomeStatus.PARTIALLY_SUPPORTED]
            )
            / resolved
            if resolved
            else None
        )
        invalidated = [
            sample
            for sample in request.samples
            if sample.outcome.thesis_status is ThesisOutcomeStatus.INVALIDATED
        ]
        detected = sum(
            sample.outcome.invalidation_triggered is True for sample in invalidated
        )
        detection_rate = 100 * detected / len(invalidated) if invalidated else None
        return ValidationModuleResult(
            assessment=assessment(
                module=self.module,
                score=score,
                confidence=sample_confidence(
                    resolved, request.minimum_observations
                ),
                sample_size=resolved,
                evaluated_at=request.requested_at,
                metrics={
                    **{
                        status.value: count for status, count in counts.items()
                    },
                    "invalidation_detection_rate": detection_rate,
                },
                findings=(
                    f"{resolved} thesis outcomes were observable and resolved",
                    f"{detected} of {len(invalidated)} invalidated theses "
                    "triggered a registered condition",
                ),
                risks=(
                    "Price outcomes alone must not be used as proof of a business thesis",
                ),
                limitations=(
                    "Unresolved and unobservable theses are retained rather "
                    "than treated as failures",
                ),
                model_version=self.model_version,
            )
        )


__all__ = ["ThesisValidationModule"]
