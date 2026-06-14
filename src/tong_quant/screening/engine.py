from dataclasses import dataclass

from tong_quant.domain.enums import Market, SignalAction, SignalStage
from tong_quant.domain.models import Signal
from tong_quant.market_regime.models import MarketRegime
from tong_quant.screening.models import (
    InvestmentAssessment,
    ResearchOutcome,
    ResearchQueueEntry,
    ScreeningOutcome,
    ScreeningRequest,
    ScreeningRun,
    Watchlist,
    screening_instrument_id,
)
from tong_quant.screening.policies.base import ScreeningPolicy
from tong_quant.screening.research_queue import WeightedQueuePrioritizer
from tong_quant.screening.scoring import WeightedScoreAggregator


@dataclass(frozen=True, slots=True)
class ScreeningEngine:
    policies: dict[Market, ScreeningPolicy]
    research_scorer: WeightedScoreAggregator
    investment_scorer: WeightedScoreAggregator
    prioritizer: WeightedQueuePrioritizer
    source_id: str = "screening.engine"
    model_version: str = "v0.4"

    def run(self, request: ScreeningRequest) -> ScreeningRun:
        try:
            policy = self.policies[request.market]
        except KeyError as error:
            raise ValueError(f"no screening policy for market {request.market.value}") from error

        outcomes = []
        for observation in request.observations:
            candidate = observation.candidate
            hard_results = policy.pipeline().evaluate(observation)
            if not hard_results or not all(result.passed for result in hard_results):
                failure = next(result for result in hard_results if not result.passed)
                outcomes.append(
                    ScreeningOutcome(
                        candidate=candidate,
                        accepted=False,
                        hard_screen_results=hard_results,
                        dimension_assessments=(),
                        queue_entry=None,
                        signal=Signal(
                            source=self.source_id,
                            stage=SignalStage.SCREENING,
                            instrument=candidate.instrument,
                            generated_at=request.as_of,
                            effective_at=request.as_of,
                            action=SignalAction.EXCLUDE,
                            strength=1,
                            reasons=failure.reasons,
                            features={
                                "hard_failure": failure.rule_id,
                                "research_score_calculated": False,
                            },
                            model_version=self.model_version,
                        ),
                    )
                )
                continue

            key = screening_instrument_id(candidate.instrument)
            assessments = request.assessments.get(key, ())
            research_score = self.research_scorer.aggregate(
                assessments,
                calculated_at=request.as_of,
            )
            priority_score = self.prioritizer.prioritize(candidate, research_score)
            queue_entry = ResearchQueueEntry(
                candidate=candidate,
                admitted_at=request.as_of,
                priority_score=priority_score,
                urgency_score=candidate.urgency_score,
                confidence_score=candidate.confidence_score,
                research_score=research_score,
                hard_screen_results=hard_results,
            )
            outcomes.append(
                ScreeningOutcome(
                    candidate=candidate,
                    accepted=True,
                    hard_screen_results=hard_results,
                    dimension_assessments=assessments,
                    queue_entry=queue_entry,
                    signal=Signal(
                        source=self.source_id,
                        stage=SignalStage.SCREENING,
                        instrument=candidate.instrument,
                        generated_at=request.as_of,
                        effective_at=request.as_of,
                        action=SignalAction.RESEARCH,
                        strength=research_score.score / 100,
                        reasons=(
                            "Candidate passed every hard screen",
                            "Candidate admitted to the research queue",
                        ),
                        features={
                            "priority_score": priority_score,
                            "urgency_score": candidate.urgency_score,
                            "confidence_score": candidate.confidence_score,
                            "research_score": research_score.score,
                        },
                        model_version=self.model_version,
                    ),
                )
            )
        accepted = tuple(
            outcome.candidate for outcome in outcomes if outcome.accepted
        )
        queue = tuple(
            outcome.queue_entry
            for outcome in outcomes
            if outcome.queue_entry is not None
        )
        return ScreeningRun(
            market=request.market,
            as_of=request.as_of,
            outcomes=tuple(outcomes),
            watchlist=Watchlist(
                market=request.market,
                as_of=request.as_of,
                candidates=accepted,
            ),
            research_queue=queue,
        )

    def assess_investment(
        self,
        research: ResearchOutcome,
        *,
        regime: MarketRegime | None,
    ) -> InvestmentAssessment:
        score = self.investment_scorer.aggregate(
            research.assessments,
            calculated_at=research.available_at,
            regime=regime,
        )
        return InvestmentAssessment(
            research=research,
            investment_score=score,
            market_regime=regime,
        )
