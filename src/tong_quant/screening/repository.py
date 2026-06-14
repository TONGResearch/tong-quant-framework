from dataclasses import asdict, dataclass

from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.screening.models import CompositeScore, ResearchQueueEntry, ScreeningOutcome


@dataclass(slots=True)
class SQLiteScreeningRepository:
    store: SQLiteStore

    def save_outcome(self, outcome: ScreeningOutcome) -> None:
        self.store.save_signal(outcome.signal)
        for result in outcome.hard_screen_results:
            self.store.save_screening_result(
                instrument=outcome.candidate.instrument,
                dimension=f"hard:{result.rule_id}",
                evaluated_at=result.evaluated_at,
                available_at=result.available_at,
                passed=result.passed,
                score=None,
                reasons=result.reasons,
                features=dict(result.features),
                source="screening.hard",
                model_version="v0.4",
            )
        for assessment in outcome.dimension_assessments:
            self.store.save_screening_result(
                instrument=outcome.candidate.instrument,
                dimension=assessment.dimension.value,
                evaluated_at=assessment.evaluated_at,
                available_at=assessment.available_at,
                passed=True,
                score=assessment.score,
                reasons=assessment.reasons,
                features={
                    **assessment.features,
                    "confidence": assessment.confidence,
                },
                source=assessment.source,
                model_version=assessment.model_version,
            )
        if outcome.queue_entry is not None:
            self.save_queue_entry(outcome.queue_entry)
            self.save_score(outcome.queue_entry, outcome.queue_entry.research_score)

    def save_queue_entry(self, entry: ResearchQueueEntry) -> str:
        return self.store.save_research_queue_entry(
            instrument=entry.candidate.instrument,
            discovery_source=entry.candidate.discovery_source,
            discovered_at=entry.candidate.discovered_at,
            admitted_at=entry.admitted_at,
            priority_score=entry.priority_score,
            urgency_score=entry.urgency_score,
            confidence_score=entry.confidence_score,
            research_score=entry.research_score.score,
            status=entry.status,
            thesis=entry.candidate.thesis,
            evidence=entry.candidate.evidence,
            assigned_to=entry.assigned_to,
            model_version=entry.research_score.model_version,
        )

    def save_score(
        self,
        entry: ResearchQueueEntry,
        score: CompositeScore,
    ) -> str:
        components = [
            {
                **asdict(component),
                "reasons": list(component.reasons),
            }
            for component in score.components
        ]
        return self.store.save_screening_score(
            instrument=entry.candidate.instrument,
            score_type=score.score_type,
            calculated_at=score.calculated_at,
            score=score.score,
            confidence=score.confidence,
            components=components,
            reasons=score.reasons,
            model_version=score.model_version,
        )
