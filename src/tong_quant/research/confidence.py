import math
from collections.abc import Iterable, Sequence
from datetime import datetime

from tong_quant.domain.enums import EvidenceQuality
from tong_quant.research.models import (
    ConfidenceBreakdown,
    ResearchAssessment,
    ResearchEvidence,
)

QUALITY_SCORES = {
    EvidenceQuality.PRIMARY: 100.0,
    EvidenceQuality.VERIFIED_SECONDARY: 85.0,
    EvidenceQuality.SECONDARY: 65.0,
    EvidenceQuality.ESTIMATED: 35.0,
}


def confidence_from_evidence(
    evidence: Sequence[ResearchEvidence],
    *,
    required_names: frozenset[str],
    as_of: datetime,
    agreement_scores: Sequence[float] = (),
) -> ConfidenceBreakdown:
    visible = [item for item in evidence if item.available_at <= as_of]
    point_in_time_integrity = 100.0 if len(visible) == len(evidence) else 0.0
    quality = (
        sum(QUALITY_SCORES[item.quality] for item in visible) / len(visible)
        if visible
        else 0.0
    )
    present = {item.name for item in visible}
    completeness = (
        100.0
        if not required_names
        else 100 * len(required_names.intersection(present)) / len(required_names)
    )
    agreement = score_agreement(agreement_scores)
    return combine_confidence(
        evidence_quality=quality,
        data_completeness=completeness,
        module_agreement=agreement,
        point_in_time_integrity=point_in_time_integrity,
    )


def report_confidence(
    assessments: Sequence[ResearchAssessment],
    evidence: Sequence[ResearchEvidence],
    *,
    as_of: datetime,
) -> ConfidenceBreakdown:
    scored = [
        assessment.score
        for assessment in assessments
        if assessment.score is not None
    ]
    expected_modules = len(assessments)
    completed_modules = sum(
        assessment.score is not None for assessment in assessments
    )
    completeness = (
        100 * completed_modules / expected_modules if expected_modules else 0.0
    )
    quality = (
        sum(QUALITY_SCORES[item.quality] for item in evidence) / len(evidence)
        if evidence
        else 0.0
    )
    integrity = (
        100.0 if all(item.available_at <= as_of for item in evidence) else 0.0
    )
    return combine_confidence(
        evidence_quality=quality,
        data_completeness=completeness,
        module_agreement=score_agreement(scored),
        point_in_time_integrity=integrity,
    )


def report_confidence_from_assessments(
    assessments: Sequence[ResearchAssessment],
) -> ConfidenceBreakdown:
    if not assessments:
        return combine_confidence(
            evidence_quality=0,
            data_completeness=0,
            module_agreement=0,
            point_in_time_integrity=0,
        )
    count = len(assessments)
    scored = [
        assessment.score for assessment in assessments if assessment.score is not None
    ]
    return combine_confidence(
        evidence_quality=sum(
            item.confidence.evidence_quality for item in assessments
        )
        / count,
        data_completeness=sum(
            item.confidence.data_completeness for item in assessments
        )
        / count,
        module_agreement=score_agreement(scored),
        point_in_time_integrity=min(
            item.confidence.point_in_time_integrity for item in assessments
        ),
    )


def combine_confidence(
    *,
    evidence_quality: float,
    data_completeness: float,
    module_agreement: float,
    point_in_time_integrity: float,
) -> ConfidenceBreakdown:
    values = (
        max(evidence_quality, 0.01),
        max(data_completeness, 0.01),
        max(module_agreement, 0.01),
        max(point_in_time_integrity, 0.01),
    )
    weights = (0.30, 0.30, 0.25, 0.15)
    geometric = math.exp(
        sum(weight * math.log(value) for value, weight in zip(values, weights, strict=True))
    )
    weakest_link_cap = min(values) * 1.5
    confidence = min(100.0, geometric, weakest_link_cap)
    if point_in_time_integrity == 0:
        confidence = 0.0
    return ConfidenceBreakdown(
        evidence_quality=round(evidence_quality, 4),
        data_completeness=round(data_completeness, 4),
        module_agreement=round(module_agreement, 4),
        point_in_time_integrity=round(point_in_time_integrity, 4),
        confidence=round(confidence, 4),
    )


def score_agreement(scores: Iterable[float]) -> float:
    values = list(scores)
    if len(values) <= 1:
        return 100.0
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    standard_deviation = math.sqrt(variance)
    return max(0.0, 100.0 - min(100.0, standard_deviation * 2))
