import math
from collections.abc import Sequence
from statistics import pstdev

from tong_quant.domain.enums import ValidationStatus
from tong_quant.validation.models import (
    AccuracyMetrics,
    IntegrityCheck,
    ValidationAssessment,
    ValidationOutcome,
    ValidationSample,
)


def resolved_samples(samples: Sequence[ValidationSample]) -> tuple[ValidationSample, ...]:
    return tuple(sample for sample in samples if sample.outcome.succeeded is not None)


def observed_accuracy(samples: Sequence[ValidationSample]) -> float:
    resolved = resolved_samples(samples)
    if not resolved:
        return 0.0
    correct = sum(
        sample.research_expected_success is sample.outcome.succeeded
        for sample in resolved
    )
    return 100 * correct / len(resolved)


def sample_confidence(sample_size: int, minimum_observations: int) -> float:
    if sample_size <= 0:
        return 0.0
    return min(100.0, 100 * sample_size / minimum_observations)


def status_for_score(
    score: float | None,
    confidence: float,
    *,
    reliable_threshold: float,
    conditional_threshold: float,
) -> ValidationStatus:
    if score is None or confidence < 25:
        return ValidationStatus.INCONCLUSIVE
    if score >= reliable_threshold and confidence >= 75:
        return ValidationStatus.RELIABLE
    if score >= conditional_threshold:
        return ValidationStatus.CONDITIONALLY_RELIABLE
    return ValidationStatus.UNRELIABLE


def integrity_checks(
    samples: Sequence[ValidationSample],
    *,
    as_of: object,
) -> tuple[IntegrityCheck, ...]:
    from datetime import datetime

    if not isinstance(as_of, datetime):
        raise TypeError("integrity checks require a datetime as_of")
    future = tuple(
        sample.sample_id
        for sample in samples
        if sample.outcome.available_at > as_of
        or sample.research_report.available_at > sample.decision_at
    )
    duplicates = len({sample.sample_id for sample in samples}) != len(samples)
    return (
        IntegrityCheck(
            check_id="point_in_time",
            passed=not future,
            checked_at=as_of,
            reasons=(
                ("No future research or outcomes detected",)
                if not future
                else (f"Future data detected in: {', '.join(future)}",)
            ),
        ),
        IntegrityCheck(
            check_id="unique_samples",
            passed=not duplicates,
            checked_at=as_of,
            reasons=(
                ("Validation sample ids are unique",)
                if not duplicates
                else ("Duplicate validation sample ids detected",)
            ),
        ),
    )


def research_accuracy_metrics(
    samples: Sequence[ValidationSample],
) -> AccuracyMetrics | None:
    resolved = resolved_samples(samples)
    if not resolved:
        return None
    probabilities = [
        sample.research_report.confidence.confidence / 100 for sample in resolved
    ]
    actuals = [1.0 if sample.outcome.succeeded else 0.0 for sample in resolved]
    predictions = [
        probability if sample.research_expected_success else 1 - probability
        for sample, probability in zip(resolved, probabilities, strict=True)
    ]
    brier = sum(
        (prediction - actual) ** 2
        for prediction, actual in zip(predictions, actuals, strict=True)
    ) / len(resolved)
    calibration = _calibration_error(predictions, actuals)
    high_confidence = [
        (prediction, actual)
        for prediction, actual in zip(predictions, actuals, strict=True)
        if prediction >= 0.75
    ]
    high_failure = (
        100
        * sum(actual < 0.5 for _, actual in high_confidence)
        / len(high_confidence)
        if high_confidence
        else 0.0
    )
    return AccuracyMetrics(
        sample_size=len(resolved),
        accuracy=round(observed_accuracy(resolved), 4),
        brier_score=round(brier, 6),
        calibration_error=round(calibration, 4),
        high_confidence_failure_rate=round(high_failure, 4),
    )


def success_rate(outcomes: Sequence[ValidationOutcome]) -> float | None:
    resolved = [outcome for outcome in outcomes if outcome.succeeded is not None]
    if not resolved:
        return None
    return 100 * sum(bool(outcome.succeeded) for outcome in resolved) / len(resolved)


def stability_score(values: Sequence[float]) -> float:
    if len(values) <= 1:
        return 100.0
    return max(0.0, 100.0 - min(100.0, pstdev(values) * 2))


def pearson(values: Sequence[float], outcomes: Sequence[float]) -> float:
    if len(values) != len(outcomes) or len(values) < 2:
        return 0.0
    mean_x = sum(values) / len(values)
    mean_y = sum(outcomes) / len(outcomes)
    numerator = sum(
        (value - mean_x) * (outcome - mean_y)
        for value, outcome in zip(values, outcomes, strict=True)
    )
    denominator = math.sqrt(
        sum((value - mean_x) ** 2 for value in values)
        * sum((outcome - mean_y) ** 2 for outcome in outcomes)
    )
    return 0.0 if denominator == 0 else numerator / denominator


def assessment(
    *,
    module: object,
    score: float | None,
    confidence: float,
    sample_size: int,
    evaluated_at: object,
    metrics: dict[str, object],
    findings: tuple[str, ...],
    risks: tuple[str, ...] = (),
    limitations: tuple[str, ...] = (),
    checks: tuple[IntegrityCheck, ...] = (),
    model_version: str,
    reliable_threshold: float = 65,
    conditional_threshold: float = 50,
) -> ValidationAssessment:
    from datetime import datetime

    from tong_quant.domain.enums import ValidationModuleName

    if not isinstance(module, ValidationModuleName) or not isinstance(
        evaluated_at, datetime
    ):
        raise TypeError("invalid validation assessment inputs")
    failed = any(not check.passed for check in checks)
    status = (
        ValidationStatus.FAILED_INTEGRITY_CHECK
        if failed
        else status_for_score(
            score,
            confidence,
            reliable_threshold=reliable_threshold,
            conditional_threshold=conditional_threshold,
        )
    )
    return ValidationAssessment(
        module=module,
        status=status,
        score=None if failed else score,
        confidence=0.0 if failed else round(confidence, 4),
        sample_size=sample_size,
        evaluated_at=evaluated_at,
        metrics=metrics,  # type: ignore[arg-type]
        findings=findings,
        risks=risks,
        limitations=limitations,
        integrity_checks=checks,
        model_version=model_version,
    )


def _calibration_error(
    predictions: Sequence[float],
    actuals: Sequence[float],
) -> float:
    bins: dict[int, list[tuple[float, float]]] = {}
    for prediction, actual in zip(predictions, actuals, strict=True):
        bins.setdefault(min(9, int(prediction * 10)), []).append((prediction, actual))
    total = len(predictions)
    return 100 * sum(
        len(items)
        / total
        * abs(
            sum(prediction for prediction, _ in items) / len(items)
            - sum(actual for _, actual in items) / len(items)
        )
        for items in bins.values()
    )
