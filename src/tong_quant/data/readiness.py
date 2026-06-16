from dataclasses import dataclass
from datetime import UTC, datetime

from tong_quant.data.models import PITReadinessAssessment
from tong_quant.domain.enums import DataTrustLevel


@dataclass(frozen=True, slots=True)
class PITReadinessInput:
    dataset: str
    expected_records: int
    observed_records: int
    trust_level: DataTrustLevel
    missing_critical_fields: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.expected_records < 0 or self.observed_records < 0:
            raise ValueError("readiness record counts cannot be negative")


@dataclass(frozen=True, slots=True)
class PITReadinessEvaluator:
    minimum_coverage_ratio: float = 0.95
    minimum_trust_level: DataTrustLevel = DataTrustLevel.MEDIUM
    model_version: str = "pit-readiness-v0.6.2"

    def evaluate(
        self,
        readiness_input: PITReadinessInput,
        *,
        assessed_at: datetime | None = None,
    ) -> PITReadinessAssessment:
        assessed = assessed_at or datetime.now(UTC)
        expected = readiness_input.expected_records
        coverage = 1.0 if expected == 0 else readiness_input.observed_records / expected
        trust_ok = _trust_rank(readiness_input.trust_level) >= _trust_rank(
            self.minimum_trust_level
        )
        ready = (
            coverage >= self.minimum_coverage_ratio
            and trust_ok
            and not readiness_input.missing_critical_fields
        )
        warnings = readiness_input.warnings
        if coverage < self.minimum_coverage_ratio:
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
        return PITReadinessAssessment(
            dataset=readiness_input.dataset,
            assessed_at=assessed,
            coverage_ratio=round(min(coverage, 1.0), 6),
            trust_level=readiness_input.trust_level,
            missing_critical_fields=readiness_input.missing_critical_fields,
            warnings=warnings,
            ready_for_historical_replay=ready,
            model_version=self.model_version,
        )


def _trust_rank(level: DataTrustLevel) -> int:
    return {
        DataTrustLevel.UNKNOWN: 0,
        DataTrustLevel.LOW: 1,
        DataTrustLevel.MEDIUM: 2,
        DataTrustLevel.HIGH: 3,
        DataTrustLevel.VERIFIED: 4,
    }[level]


__all__ = ["PITReadinessEvaluator", "PITReadinessInput"]
