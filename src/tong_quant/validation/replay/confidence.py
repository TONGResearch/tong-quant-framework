from dataclasses import dataclass

from tong_quant.data.models import PITReadinessAssessment, ProviderLimitation
from tong_quant.domain.enums import (
    DataTrustLevel,
    PITReadinessClassification,
)
from tong_quant.validation.replay.models import ReplayConfidence
from tong_quant.version import REPLAY_CONFIDENCE_VERSION


@dataclass(frozen=True, slots=True)
class ReplayConfidenceInput:
    trust_levels: tuple[DataTrustLevel, ...]
    readiness_assessments: tuple[PITReadinessAssessment, ...]
    required_datasets: tuple[str, ...]
    minimum_trust_level: DataTrustLevel
    missing_data_count: int
    expected_input_count: int
    provider_limitations: tuple[ProviderLimitation, ...]
    integrity_blockers: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.missing_data_count < 0 or self.expected_input_count <= 0:
            raise ValueError("replay confidence input counts are invalid")
        if self.missing_data_count > self.expected_input_count:
            raise ValueError("missing data count cannot exceed expected inputs")
        if not self.required_datasets:
            raise ValueError("replay confidence requires readiness datasets")


@dataclass(frozen=True, slots=True)
class ReplayConfidenceEvaluator:
    model_version: str = REPLAY_CONFIDENCE_VERSION

    def evaluate(self, confidence_input: ReplayConfidenceInput) -> ReplayConfidence:
        readiness_trust = tuple(
            assessment.trust_level for assessment in confidence_input.readiness_assessments
        )
        observed_trust = confidence_input.trust_levels + readiness_trust
        data_trust_score = _data_trust_score(observed_trust)
        pit_readiness_score = _pit_readiness_score(confidence_input.readiness_assessments)
        missing_data_score = round(
            100 * (1 - confidence_input.missing_data_count / confidence_input.expected_input_count),
            6,
        )
        provider_limitation_score = max(
            0.0,
            100.0 - 20.0 * len(confidence_input.provider_limitations),
        )
        confidence = round(
            data_trust_score * 0.35
            + pit_readiness_score * 0.25
            + missing_data_score * 0.25
            + provider_limitation_score * 0.15,
            6,
        )
        blocking_reasons = _blocking_reasons(
            confidence_input,
            observed_trust=observed_trust,
        )
        reasons = (
            f"data trust score {data_trust_score:.1f}",
            f"PIT readiness score {pit_readiness_score:.1f}",
            f"missing data score {missing_data_score:.1f}",
            f"provider limitation score {provider_limitation_score:.1f}",
            (
                "validation data-quality gate passed"
                if not blocking_reasons
                else "validation data-quality gate failed"
            ),
        )
        return ReplayConfidence(
            data_trust_score=data_trust_score,
            pit_readiness_score=pit_readiness_score,
            missing_data_score=missing_data_score,
            provider_limitation_score=provider_limitation_score,
            confidence=confidence,
            reasons=reasons,
            validation_eligible=not blocking_reasons,
            blocking_reasons=blocking_reasons,
            model_version=self.model_version,
        )


def _blocking_reasons(
    confidence_input: ReplayConfidenceInput,
    *,
    observed_trust: tuple[DataTrustLevel, ...],
) -> tuple[str, ...]:
    blockers: list[str] = list(confidence_input.integrity_blockers)
    assessment_by_dataset = {
        assessment.dataset: assessment for assessment in confidence_input.readiness_assessments
    }
    for dataset in confidence_input.required_datasets:
        assessment = assessment_by_dataset.get(dataset)
        if assessment is None:
            blockers.append(f"missing PIT readiness assessment for {dataset}")
            continue
        if (
            assessment.classification is not PITReadinessClassification.USABLE
            or not assessment.ready_for_historical_replay
        ):
            blockers.append(f"PIT readiness for {dataset} is {assessment.classification.value}")
        if assessment.missing_critical_fields:
            blockers.append(f"critical PIT fields are missing for {dataset}")

    minimum_rank = trust_rank(confidence_input.minimum_trust_level)
    if not observed_trust:
        blockers.append("no data trust evidence is available")
    elif min(trust_rank(level) for level in observed_trust) < minimum_rank:
        blockers.append(
            f"observed data trust is below required {confidence_input.minimum_trust_level.value}"
        )
    if confidence_input.missing_data_count:
        blockers.append(f"{confidence_input.missing_data_count} required replay inputs are missing")
    return tuple(dict.fromkeys(blockers))


def trust_rank(level: DataTrustLevel) -> int:
    return {
        DataTrustLevel.UNKNOWN: 0,
        DataTrustLevel.LOW: 1,
        DataTrustLevel.MEDIUM: 2,
        DataTrustLevel.HIGH: 3,
        DataTrustLevel.VERIFIED: 4,
    }[level]


def _data_trust_score(levels: tuple[DataTrustLevel, ...]) -> float:
    if not levels:
        return 25.0
    weakest = min(trust_rank(level) for level in levels)
    return round(100 * weakest / trust_rank(DataTrustLevel.VERIFIED), 6)


def _pit_readiness_score(assessments: tuple[PITReadinessAssessment, ...]) -> float:
    if not assessments:
        return 50.0
    scores = []
    for assessment in assessments:
        score = assessment.coverage_ratio * 100
        if not assessment.ready_for_historical_replay:
            score -= 20
        scores.append(max(0.0, score))
    return round(sum(scores) / len(scores), 6)


__all__ = [
    "ReplayConfidenceEvaluator",
    "ReplayConfidenceInput",
    "trust_rank",
]
