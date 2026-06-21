from dataclasses import dataclass, replace
from datetime import UTC, datetime

from tong_quant.data.calibration.models import DatasetConfidenceAssessment
from tong_quant.data.models import PITReadinessAssessment
from tong_quant.domain.enums import DataTrustLevel, PITReadinessClassification
from tong_quant.version import PIT_READINESS_VERSION


@dataclass(frozen=True, slots=True)
class PITReadinessInput:
    dataset: str
    expected_records: int
    observed_records: int
    trust_level: DataTrustLevel
    coverage_known: bool = True
    missing_critical_fields: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    availability_score: float = 0.0
    revision_score: float = 0.0
    continuity_score: float = 0.0
    provider_consistency_score: float | None = None
    provider_consistency_required: bool = False
    provider_conflict_count: int = 0
    critical_provider_conflict_count: int = 0
    assumptions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.expected_records < 0 or self.observed_records < 0:
            raise ValueError("readiness record counts cannot be negative")
        scores = (
            self.availability_score,
            self.revision_score,
            self.continuity_score,
        )
        if any(not 0 <= score <= 100 for score in scores):
            raise ValueError("readiness dimension scores must be between zero and 100")
        if self.provider_consistency_score is not None and not (
            0 <= self.provider_consistency_score <= 100
        ):
            raise ValueError("provider consistency score must be between zero and 100")
        if self.provider_conflict_count < 0 or self.critical_provider_conflict_count < 0:
            raise ValueError("provider conflict counts cannot be negative")
        if self.critical_provider_conflict_count > self.provider_conflict_count:
            raise ValueError("critical provider conflicts cannot exceed total conflicts")


@dataclass(frozen=True, slots=True)
class PITReadinessEvaluator:
    minimum_coverage_ratio: float = 0.95
    minimum_trust_level: DataTrustLevel = DataTrustLevel.MEDIUM
    usable_score: float = 80.0
    caution_score: float = 50.0
    model_version: str = PIT_READINESS_VERSION

    def evaluate(
        self,
        readiness_input: PITReadinessInput,
        *,
        assessed_at: datetime | None = None,
    ) -> PITReadinessAssessment:
        assessed = assessed_at or datetime.now(UTC)
        expected = readiness_input.expected_records
        coverage = (
            1.0
            if expected == 0
            else readiness_input.observed_records / expected
            if readiness_input.coverage_known
            else 0.0
        )
        trust_ok = _trust_rank(readiness_input.trust_level) >= _trust_rank(
            self.minimum_trust_level
        )
        trust_score = _trust_rank(readiness_input.trust_level) / 4 * 100
        provider_score = readiness_input.provider_consistency_score
        assumptions = readiness_input.assumptions
        if provider_score is None:
            provider_score = 50.0
            assumptions = (*assumptions, "No secondary-provider calibration is available")
        components = {
            "coverage": min(coverage, 1.0) * 100,
            "trust": trust_score,
            "availability": readiness_input.availability_score,
            "revision": readiness_input.revision_score,
            "continuity": readiness_input.continuity_score,
            "provider_consistency": provider_score,
        }
        score = (
            components["coverage"] * 0.35
            + components["trust"] * 0.20
            + components["availability"] * 0.15
            + components["revision"] * 0.10
            + components["continuity"] * 0.10
            + components["provider_consistency"] * 0.10
        )
        if readiness_input.missing_critical_fields:
            score = min(score, self.caution_score - 1)
        if readiness_input.trust_level in {
            DataTrustLevel.LOW,
            DataTrustLevel.UNKNOWN,
        }:
            score = min(score, self.usable_score - 1)
        if readiness_input.critical_provider_conflict_count:
            score = min(score, self.usable_score - 1)
        if (
            readiness_input.provider_consistency_required
            and readiness_input.provider_consistency_score is None
        ):
            score = min(score, self.usable_score - 1)
        if (
            score >= self.usable_score
            and coverage >= self.minimum_coverage_ratio
            and trust_ok
            and not readiness_input.missing_critical_fields
        ):
            classification = PITReadinessClassification.USABLE
        elif score >= self.caution_score:
            classification = PITReadinessClassification.CAUTION
        else:
            classification = PITReadinessClassification.UNSUITABLE
        warnings = readiness_input.warnings
        if not readiness_input.coverage_known:
            warnings = (*warnings, "coverage is unmeasurable")
        elif coverage < self.minimum_coverage_ratio:
            warnings = (
                *warnings,
                f"coverage {coverage:.1%} is below required {self.minimum_coverage_ratio:.1%}",
            )
        if not trust_ok:
            warnings = (
                *warnings,
                f"trust level {readiness_input.trust_level.value} is below required "
                f"{self.minimum_trust_level.value}",
            )
        if readiness_input.provider_consistency_score is None:
            warnings = (*warnings, "secondary-provider consistency is unknown")
        if (
            readiness_input.provider_consistency_required
            and readiness_input.provider_consistency_score is None
        ):
            warnings = (
                *warnings,
                "required provider calibration is unavailable",
            )
        if readiness_input.provider_conflict_count:
            warnings = (
                *warnings,
                f"{readiness_input.provider_conflict_count} provider conflicts detected",
            )
        if readiness_input.critical_provider_conflict_count:
            warnings = (
                *warnings,
                "high-severity provider conflicts prevent usable PIT classification",
            )
        return PITReadinessAssessment(
            dataset=readiness_input.dataset,
            assessed_at=assessed,
            coverage_ratio=round(min(coverage, 1.0), 6),
            trust_level=readiness_input.trust_level,
            missing_critical_fields=readiness_input.missing_critical_fields,
            warnings=warnings,
            ready_for_historical_replay=(
                classification is PITReadinessClassification.USABLE
            ),
            readiness_score=round(score, 2),
            classification=classification,
            score_components={key: round(value, 2) for key, value in components.items()},
            assumptions=assumptions,
            model_version=self.model_version,
        )


def apply_provider_confidence(
    readiness_input: PITReadinessInput,
    confidence: DatasetConfidenceAssessment,
) -> PITReadinessInput:
    if confidence.dataset != readiness_input.dataset:
        raise ValueError("provider confidence dataset does not match readiness dataset")
    return replace(
        readiness_input,
        provider_consistency_score=confidence.confidence_score,
        provider_conflict_count=confidence.conflict_count,
        critical_provider_conflict_count=confidence.critical_conflict_count,
        assumptions=(
            *readiness_input.assumptions,
            f"Provider calibration report: {confidence.report_id}",
        ),
    )


def _trust_rank(level: DataTrustLevel) -> int:
    return {
        DataTrustLevel.UNKNOWN: 0,
        DataTrustLevel.LOW: 1,
        DataTrustLevel.MEDIUM: 2,
        DataTrustLevel.HIGH: 3,
        DataTrustLevel.VERIFIED: 4,
    }[level]


__all__ = [
    "PITReadinessEvaluator",
    "PITReadinessInput",
    "apply_provider_confidence",
]
