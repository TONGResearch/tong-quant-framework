from dataclasses import dataclass

from tong_quant.domain.enums import ScoreType
from tong_quant.screening.models import CompositeScore, OpportunityCandidate


@dataclass(frozen=True, slots=True)
class WeightedQueuePrioritizer:
    research_weight: float = 0.65
    urgency_weight: float = 0.25
    confidence_weight: float = 0.10

    def __post_init__(self) -> None:
        weights = (self.research_weight, self.urgency_weight, self.confidence_weight)
        if any(weight < 0 for weight in weights):
            raise ValueError("queue priority weights cannot be negative")
        if abs(sum(weights) - 1) > 1e-9:
            raise ValueError("queue priority weights must sum to one")

    def prioritize(
        self,
        candidate: OpportunityCandidate,
        research_score: CompositeScore,
    ) -> float:
        if research_score.score_type is not ScoreType.RESEARCH:
            raise ValueError("queue priority requires a Research Score")
        return round(
            research_score.score * self.research_weight
            + candidate.urgency_score * self.urgency_weight
            + candidate.confidence_score * self.confidence_weight,
            4,
        )
