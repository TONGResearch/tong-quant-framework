from datetime import datetime
from typing import Protocol

from tong_quant.domain.enums import Market, ScoreType
from tong_quant.market_regime.models import MarketRegime
from tong_quant.screening.dimensions import DimensionEvidence
from tong_quant.screening.models import (
    CompositeScore,
    DimensionAssessment,
    HardScreenObservation,
    HardScreenResult,
    OpportunityCandidate,
    ResearchQueueEntry,
    ScreeningOutcome,
    ScreeningRequest,
    ScreeningRun,
)


class OpportunitySource(Protocol):
    source_id: str

    def discover(self, *, as_of: datetime) -> tuple[OpportunityCandidate, ...]: ...


class HardScreenRule(Protocol):
    rule_id: str

    def evaluate(self, observation: HardScreenObservation) -> HardScreenResult: ...


class MarketScreeningPolicy(Protocol):
    market: Market

    def rules(self) -> tuple[HardScreenRule, ...]: ...


class ScreeningDimension(Protocol):
    source_id: str

    def evaluate(self, evidence: DimensionEvidence) -> DimensionAssessment: ...


class ScoreAggregator(Protocol):
    score_type: ScoreType

    def aggregate(
        self,
        assessments: tuple[DimensionAssessment, ...],
        *,
        calculated_at: datetime,
        regime: MarketRegime | None = None,
    ) -> CompositeScore: ...


class ResearchQueuePrioritizer(Protocol):
    def prioritize(
        self,
        candidate: OpportunityCandidate,
        research_score: CompositeScore,
    ) -> float: ...


class ScreeningRepository(Protocol):
    def save_outcome(self, outcome: ScreeningOutcome) -> None: ...

    def save_queue_entry(self, entry: ResearchQueueEntry) -> str: ...

    def save_score(
        self,
        entry: ResearchQueueEntry,
        score: CompositeScore,
    ) -> str: ...


class ScreeningApplication(Protocol):
    def run(self, request: ScreeningRequest) -> ScreeningRun: ...
