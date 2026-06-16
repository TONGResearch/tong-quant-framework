from datetime import UTC, date, datetime
from decimal import Decimal

from tong_quant.domain.enums import (
    Market,
    ScoreType,
    ScreeningDimensionName,
    SecurityStatus,
    SignalAction,
)
from tong_quant.domain.models import Instrument, InstrumentStatus
from tong_quant.screening.engine import ScreeningEngine
from tong_quant.screening.models import (
    DimensionAssessment,
    HardScreenObservation,
    OpportunityCandidate,
    ScreeningRequest,
    screening_instrument_id,
)
from tong_quant.screening.policies import default_market_policies
from tong_quant.screening.research_queue import WeightedQueuePrioritizer
from tong_quant.screening.scoring import (
    WeightedScoreAggregator,
    default_research_score_config,
)


def test_hard_failure_rejects_without_calculating_score() -> None:
    as_of = datetime(2026, 1, 2, tzinfo=UTC)
    candidate = _candidate(as_of)
    observation = _observation(
        candidate,
        as_of,
        status=SecurityStatus.SPECIAL_TREATMENT,
        tradable=True,
    )

    run = _engine().run(
        ScreeningRequest(
            market=Market.CHINA_A,
            as_of=as_of,
            observations=(observation,),
            assessments={},
        )
    )
    outcome = run.outcomes[0]

    assert outcome.accepted is False
    assert outcome.queue_entry is None
    assert outcome.signal.action is SignalAction.EXCLUDE
    assert outcome.signal.features["research_score_calculated"] is False
    assert [result.rule_id for result in outcome.hard_screen_results] == [
        "data_quality",
        "security_lifecycle",
    ]


def test_survivor_enters_research_queue_with_separate_scores() -> None:
    as_of = datetime(2026, 1, 2, tzinfo=UTC)
    candidate = _candidate(as_of)
    key = screening_instrument_id(candidate.instrument)

    run = _engine().run(
        ScreeningRequest(
            market=Market.CHINA_A,
            as_of=as_of,
            observations=(_observation(candidate, as_of),),
            assessments={key: _assessments(as_of)},
        )
    )
    outcome = run.outcomes[0]

    assert outcome.accepted is True
    assert outcome.signal.action is SignalAction.RESEARCH
    assert outcome.queue_entry is not None
    assert outcome.queue_entry.research_score.score_type is ScoreType.RESEARCH
    assert outcome.queue_entry.urgency_score == 90
    assert outcome.queue_entry.confidence_score == 40
    assert outcome.queue_entry.priority_score == 72
    assert outcome.queue_entry.priority_score != outcome.queue_entry.urgency_score
    assert outcome.queue_entry.priority_score != outcome.queue_entry.confidence_score
    assert run.watchlist.candidates == (candidate,)
    assert run.research_queue == (outcome.queue_entry,)


def test_shared_engine_has_four_distinct_market_policies() -> None:
    assert set(default_market_policies()) == {
        Market.CHINA_A,
        Market.US,
        Market.HONG_KONG,
        Market.MALAYSIA,
    }


def _engine() -> ScreeningEngine:
    return ScreeningEngine(
        policies=default_market_policies(),
        research_scorer=WeightedScoreAggregator(default_research_score_config()),
        prioritizer=WeightedQueuePrioritizer(),
    )


def _candidate(as_of: datetime) -> OpportunityCandidate:
    return OpportunityCandidate(
        instrument=Instrument("600000", Market.CHINA_A, "Example"),
        discovery_source="discovery.policy",
        discovered_at=as_of,
        available_at=as_of,
        thesis="Policy support may improve industry demand",
        evidence=("Policy evidence",),
        urgency_score=90,
        confidence_score=40,
    )


def _observation(
    candidate: OpportunityCandidate,
    as_of: datetime,
    *,
    status: SecurityStatus = SecurityStatus.LISTED,
    tradable: bool = True,
) -> HardScreenObservation:
    return HardScreenObservation(
        candidate=candidate,
        as_of=as_of,
        available_at=as_of,
        status=InstrumentStatus(
            candidate.instrument,
            effective_from=date(2026, 1, 1),
            status=status,
            is_tradable=tradable,
            available_at=as_of,
            source="test",
        ),
        data_quality_passed=True,
        average_daily_turnover=Decimal("10000000"),
        financial_health_score=70,
    )


def _assessments(as_of: datetime) -> tuple[DimensionAssessment, ...]:
    return tuple(
        DimensionAssessment(
            dimension=dimension,
            score=70,
            confidence=80,
            evaluated_at=as_of,
            available_at=as_of,
            reasons=(f"{dimension.value} evidence reviewed",),
            source=f"screening.{dimension.value}",
            model_version="v0.4",
        )
        for dimension in ScreeningDimensionName
    )
