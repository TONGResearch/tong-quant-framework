from dataclasses import dataclass

from tong_quant.domain.enums import ValidationModuleName, ValidationSplitKind
from tong_quant.validation.base import assessment, observed_accuracy, sample_confidence
from tong_quant.validation.models import (
    IntegrityCheck,
    ValidationModuleResult,
    ValidationRequest,
    ValidationSplit,
)


@dataclass(frozen=True, slots=True)
class OutOfSampleValidationModule:
    module: ValidationModuleName = ValidationModuleName.OUT_OF_SAMPLE
    model_version: str = "out-of-sample-v0.6"

    def evaluate(
        self,
        request: ValidationRequest,
        splits: tuple[ValidationSplit, ...],
    ) -> ValidationModuleResult:
        oos = [split for split in splits if split.kind is ValidationSplitKind.OUT_OF_SAMPLE]
        if len(oos) != 1:
            raise ValueError("exactly one final out-of-sample split is required")
        split = oos[0]
        frozen = split.frozen_configuration_hash == (
            request.framework_snapshot.configuration_hash
        )
        usage_valid = (
            request.out_of_sample_policy.previous_uses
            < request.out_of_sample_policy.maximum_uses
        )
        samples = tuple(
            sample
            for sample in request.samples
            if split.start_date <= sample.decision_at.date() <= split.end_date
            and sample.outcome.succeeded is not None
        )
        score = observed_accuracy(samples) if samples else None
        checks = (
            IntegrityCheck(
                check_id="oos_configuration_freeze",
                passed=frozen,
                checked_at=request.requested_at,
                reasons=(
                    ("OOS configuration hash matches the frozen snapshot",)
                    if frozen
                    else ("OOS configuration hash changed after freezing",)
                ),
            ),
            IntegrityCheck(
                check_id="oos_usage_count",
                passed=usage_valid,
                checked_at=request.requested_at,
                reasons=(
                    ("OOS usage remains within the pre-registered limit",)
                    if usage_valid
                    else ("OOS dataset has been reused beyond its registered limit",)
                ),
            ),
        )
        return ValidationModuleResult(
            assessment=assessment(
                module=self.module,
                score=score,
                confidence=sample_confidence(
                    len(samples), request.minimum_observations
                ),
                sample_size=len(samples),
                evaluated_at=request.requested_at,
                metrics={
                    "oos_accuracy": score,
                    "previous_uses": request.out_of_sample_policy.previous_uses,
                    "maximum_uses": request.out_of_sample_policy.maximum_uses,
                },
                findings=(f"OOS validation evaluated {len(samples)} samples",),
                risks=("Repeated OOS access converts the dataset into development data",),
                checks=checks,
                model_version=self.model_version,
            )
        )


__all__ = ["OutOfSampleValidationModule"]
