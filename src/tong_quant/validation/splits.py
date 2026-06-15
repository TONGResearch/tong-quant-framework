from datetime import date, timedelta

from tong_quant.domain.enums import ValidationSplitKind
from tong_quant.validation.models import (
    OutOfSamplePolicy,
    ValidationSplit,
    WalkForwardPolicy,
)


def walk_forward_splits(
    start: date,
    end: date,
    policy: WalkForwardPolicy,
    configuration_hash: str,
) -> tuple[ValidationSplit, ...]:
    splits: list[ValidationSplit] = []
    training_start = start
    sequence = 0
    while True:
        training_end = training_start + timedelta(days=policy.training_days - 1)
        validation_start = training_end + timedelta(days=policy.embargo_days + 1)
        validation_end = validation_start + timedelta(days=policy.validation_days - 1)
        if validation_end > end:
            break
        splits.extend(
            (
                ValidationSplit(
                    split_id=f"wf-{sequence}-training",
                    kind=ValidationSplitKind.TRAINING,
                    start_date=training_start,
                    end_date=training_end,
                    frozen_configuration_hash=configuration_hash,
                    sequence=sequence,
                ),
                ValidationSplit(
                    split_id=f"wf-{sequence}-validation",
                    kind=ValidationSplitKind.VALIDATION,
                    start_date=validation_start,
                    end_date=validation_end,
                    frozen_configuration_hash=configuration_hash,
                    sequence=sequence,
                ),
            )
        )
        training_start += timedelta(days=policy.step_days)
        sequence += 1
    return tuple(splits)


def out_of_sample_split(
    policy: OutOfSamplePolicy,
) -> ValidationSplit:
    return ValidationSplit(
        split_id="final-out-of-sample",
        kind=ValidationSplitKind.OUT_OF_SAMPLE,
        start_date=policy.out_of_sample_start,
        end_date=policy.out_of_sample_end,
        frozen_configuration_hash=policy.frozen_configuration_hash,
        sequence=0,
    )


__all__ = ["out_of_sample_split", "walk_forward_splits"]
