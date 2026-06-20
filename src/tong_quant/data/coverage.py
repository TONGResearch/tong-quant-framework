from dataclasses import dataclass
from datetime import UTC, date, datetime

from tong_quant.data.models import (
    FundamentalPublicationEvent,
    HistoricalCoverageAssessment,
    SecurityLifecycleEvent,
)
from tong_quant.domain.enums import (
    AvailabilityPrecision,
    DataTrustLevel,
    HistoricalCoverageSubject,
    LifecycleEventType,
    PITReadinessClassification,
)
from tong_quant.domain.models import UniverseMembership
from tong_quant.version import HISTORICAL_COVERAGE_VERSION


@dataclass(frozen=True, slots=True)
class SecurityTimelineQualityInput:
    instrument_id: str
    period_start: date
    period_end: date
    events: tuple[SecurityLifecycleEvent, ...]
    expected_event_types: tuple[LifecycleEventType, ...]
    contradiction_count: int = 0
    expected_provider_count: int = 2


@dataclass(frozen=True, slots=True)
class UniverseMembershipQualityInput:
    universe: str
    period_start: date
    period_end: date
    memberships: tuple[UniverseMembership, ...]
    expected_snapshot_dates: tuple[date, ...]
    has_entry_exit_history: bool
    expected_provider_count: int = 2


@dataclass(frozen=True, slots=True)
class FundamentalPublicationQualityInput:
    instrument_id: str
    period_start: date
    period_end: date
    publications: tuple[FundamentalPublicationEvent, ...]
    expected_period_ends: tuple[date, ...]
    expected_provider_count: int = 2


@dataclass(frozen=True, slots=True)
class HistoricalCoverageEvaluator:
    model_version: str = HISTORICAL_COVERAGE_VERSION

    def security_timeline(
        self,
        quality_input: SecurityTimelineQualityInput,
        *,
        assessed_at: datetime | None = None,
    ) -> HistoricalCoverageAssessment:
        expected_types = set(quality_input.expected_event_types)
        observed_types = {event.event_type for event in quality_input.events}
        event_coverage = _ratio(len(expected_types & observed_types), len(expected_types))
        temporal = _average_precision(
            tuple(event.availability_precision for event in quality_input.events)
        )
        source_diversity = _source_diversity(
            tuple(event.source for event in quality_input.events),
            quality_input.expected_provider_count,
        )
        consistency = max(0.0, 100.0 - quality_input.contradiction_count * 25.0)
        components = {
            "event_type_coverage": event_coverage,
            "temporal_precision": temporal,
            "source_diversity": source_diversity,
            "consistency": consistency,
        }
        score = (
            event_coverage * 0.40
            + temporal * 0.30
            + source_diversity * 0.15
            + consistency * 0.15
        )
        warnings: list[str] = []
        missing = sorted(event.value for event in expected_types - observed_types)
        if missing:
            warnings.append(f"missing lifecycle event types: {', '.join(missing)}")
        if quality_input.contradiction_count:
            warnings.append("status timeline contains contradictory observations")
        return _assessment(
            subject_type=HistoricalCoverageSubject.SECURITY_LIFECYCLE,
            subject_id=quality_input.instrument_id,
            dataset="security_lifecycle_events",
            period_start=quality_input.period_start,
            period_end=quality_input.period_end,
            assessed_at=assessed_at,
            score=score,
            components=components,
            trust_level=_aggregate_trust(
                tuple(event.trust_level for event in quality_input.events)
            ),
            warnings=tuple(warnings),
            assumptions=(
                "Absence of a lifecycle event is not proof that no event occurred",
            ),
            model_version=self.model_version,
        )

    def universe_membership(
        self,
        quality_input: UniverseMembershipQualityInput,
        *,
        assessed_at: datetime | None = None,
    ) -> HistoricalCoverageAssessment:
        observed_dates = {item.effective_from for item in quality_input.memberships}
        expected_dates = set(quality_input.expected_snapshot_dates)
        snapshot_coverage = _ratio(len(observed_dates & expected_dates), len(expected_dates))
        temporal = _average_precision(
            tuple(item.availability_precision for item in quality_input.memberships)
        )
        source_diversity = _source_diversity(
            tuple(item.source for item in quality_input.memberships),
            quality_input.expected_provider_count,
        )
        entry_exit = 100.0 if quality_input.has_entry_exit_history else 0.0
        components = {
            "snapshot_coverage": snapshot_coverage,
            "temporal_precision": temporal,
            "source_diversity": source_diversity,
            "entry_exit_history": entry_exit,
        }
        score = (
            snapshot_coverage * 0.45
            + temporal * 0.25
            + source_diversity * 0.15
            + entry_exit * 0.15
        )
        warnings: tuple[str, ...] = ()
        if not quality_input.has_entry_exit_history:
            warnings = (
                "membership snapshots do not prove complete entry and exit history",
            )
        return _assessment(
            subject_type=HistoricalCoverageSubject.UNIVERSE_MEMBERSHIP,
            subject_id=quality_input.universe,
            dataset="universe_memberships",
            period_start=quality_input.period_start,
            period_end=quality_input.period_end,
            assessed_at=assessed_at,
            score=score,
            components=components,
            trust_level=_aggregate_trust(
                tuple(item.trust_level for item in quality_input.memberships)
            ),
            warnings=warnings,
            assumptions=(
                "Repeated retrieval-time snapshots improve forward coverage only",
            ),
            model_version=self.model_version,
        )

    def fundamental_publication(
        self,
        quality_input: FundamentalPublicationQualityInput,
        *,
        assessed_at: datetime | None = None,
    ) -> HistoricalCoverageAssessment:
        expected_periods = set(quality_input.expected_period_ends)
        observed_periods = {
            publication.period_end for publication in quality_input.publications
        }
        period_coverage = _ratio(
            len(expected_periods & observed_periods), len(expected_periods)
        )
        temporal = _average_precision(
            tuple(
                publication.availability_precision
                for publication in quality_input.publications
            )
        )
        source_diversity = _source_diversity(
            tuple(publication.source for publication in quality_input.publications),
            quality_input.expected_provider_count,
        )
        revision_periods = {
            publication.period_end
            for publication in quality_input.publications
            if publication.revision > 0
        }
        revision_score = 100.0 if revision_periods else 50.0
        components = {
            "period_coverage": period_coverage,
            "temporal_precision": temporal,
            "source_diversity": source_diversity,
            "revision_observability": revision_score,
        }
        score = (
            period_coverage * 0.40
            + temporal * 0.30
            + source_diversity * 0.15
            + revision_score * 0.15
        )
        warnings: tuple[str, ...] = ()
        if not revision_periods:
            warnings = ("no restatement or correction history was observed",)
        return _assessment(
            subject_type=HistoricalCoverageSubject.FUNDAMENTAL_PUBLICATION,
            subject_id=quality_input.instrument_id,
            dataset="fundamental_publications",
            period_start=quality_input.period_start,
            period_end=quality_input.period_end,
            assessed_at=assessed_at,
            score=score,
            components=components,
            trust_level=_aggregate_trust(
                tuple(
                    publication.trust_level
                    for publication in quality_input.publications
                )
            ),
            warnings=warnings,
            assumptions=(
                "Publication evidence is distinct from financial fact correctness",
            ),
            model_version=self.model_version,
        )


def _assessment(
    *,
    subject_type: HistoricalCoverageSubject,
    subject_id: str,
    dataset: str,
    period_start: date,
    period_end: date,
    assessed_at: datetime | None,
    score: float,
    components: dict[str, float],
    trust_level: DataTrustLevel,
    warnings: tuple[str, ...],
    assumptions: tuple[str, ...],
    model_version: str,
) -> HistoricalCoverageAssessment:
    bounded = round(max(0.0, min(score, 100.0)), 2)
    weak_trust = trust_level in {DataTrustLevel.LOW, DataTrustLevel.UNKNOWN}
    if bounded >= 80 and not weak_trust:
        classification = PITReadinessClassification.USABLE
    elif bounded >= 50:
        classification = PITReadinessClassification.CAUTION
    else:
        classification = PITReadinessClassification.UNSUITABLE
    effective_warnings = warnings
    if weak_trust and bounded >= 80:
        effective_warnings = (
            *warnings,
            f"coverage score is capped at caution by {trust_level.value} trust",
        )
    return HistoricalCoverageAssessment(
        subject_type=subject_type,
        subject_id=subject_id,
        dataset=dataset,
        period_start=period_start,
        period_end=period_end,
        assessed_at=assessed_at or datetime.now(UTC),
        confidence_score=bounded,
        classification=classification,
        trust_level=trust_level,
        score_components={key: round(value, 2) for key, value in components.items()},
        warnings=effective_warnings,
        assumptions=assumptions,
        model_version=model_version,
    )


def _ratio(observed: int, expected: int) -> float:
    return 100.0 if expected == 0 else min(observed / expected, 1.0) * 100


def _average_precision(values: tuple[AvailabilityPrecision, ...]) -> float:
    if not values:
        return 0.0
    scores = {
        AvailabilityPrecision.EXACT: 100.0,
        AvailabilityPrecision.DATE_ONLY: 80.0,
        AvailabilityPrecision.ESTIMATED: 50.0,
        AvailabilityPrecision.RETRIEVAL_TIME: 25.0,
        AvailabilityPrecision.UNKNOWN: 0.0,
    }
    return sum(scores[value] for value in values) / len(values)


def _source_diversity(sources: tuple[str, ...], expected_count: int) -> float:
    if expected_count <= 0:
        return 100.0
    return min(len(set(sources)) / expected_count, 1.0) * 100


def _aggregate_trust(levels: tuple[DataTrustLevel, ...]) -> DataTrustLevel:
    if not levels:
        return DataTrustLevel.UNKNOWN
    ranks = {
        DataTrustLevel.UNKNOWN: 0,
        DataTrustLevel.LOW: 1,
        DataTrustLevel.MEDIUM: 2,
        DataTrustLevel.HIGH: 3,
        DataTrustLevel.VERIFIED: 4,
    }
    average = sum(ranks[level] for level in levels) / len(levels)
    if average >= 3.5:
        return DataTrustLevel.VERIFIED
    if average >= 2.5:
        return DataTrustLevel.HIGH
    if average >= 1.5:
        return DataTrustLevel.MEDIUM
    if average >= 0.5:
        return DataTrustLevel.LOW
    return DataTrustLevel.UNKNOWN


__all__ = [
    "FundamentalPublicationQualityInput",
    "HistoricalCoverageEvaluator",
    "SecurityTimelineQualityInput",
    "UniverseMembershipQualityInput",
]
