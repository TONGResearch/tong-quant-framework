from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from tong_quant.domain.enums import (
    EvidenceQuality,
    Market,
    ResearchConclusion,
    ResearchModuleName,
    ScoreType,
    SignalAction,
)
from tong_quant.domain.models import Bar, FundamentalFact, Instrument
from tong_quant.research.confidence import combine_confidence
from tong_quant.research.engine import ResearchEngine
from tong_quant.research.financial import FinancialResearchModule
from tong_quant.research.industry import IndustryResearchModule
from tong_quant.research.models import (
    ResearchContext,
    ResearchEvidence,
    ResearchRequest,
    ThesisInvalidationCondition,
)
from tong_quant.research.pattern import PatternResearchModule
from tong_quant.research.policy import PolicyResearchModule
from tong_quant.research.technical import TechnicalResearchModule
from tong_quant.research.trend import TrendResearchModule
from tong_quant.research.value import ValueResearchModule
from tong_quant.screening.models import (
    CompositeScore,
    HardScreenResult,
    OpportunityCandidate,
    ResearchQueueEntry,
    ScoreComponent,
)


def test_research_request_requires_counter_thesis_and_invalidation() -> None:
    context = _context(evidence=_evidence(ResearchModuleName.POLICY, "fiscal_policy"))
    with pytest.raises(ValueError, match="thesis and counter thesis"):
        ResearchRequest(
            context=context,
            modules=(ResearchModuleName.POLICY,),
            thesis="Demand may improve",
            counter_thesis="",
            invalidation_conditions=(_invalidation(),),
        )
    with pytest.raises(ValueError, match="invalidation"):
        ResearchRequest(
            context=context,
            modules=(ResearchModuleName.POLICY,),
            thesis="Demand may improve",
            counter_thesis="Policy support may be ineffective",
            invalidation_conditions=(),
        )


def test_context_rejects_future_evidence() -> None:
    as_of = datetime(2026, 1, 2, tzinfo=UTC)
    future = ResearchEvidence(
        evidence_id="future",
        module=ResearchModuleName.POLICY,
        name="fiscal_policy",
        value=70,
        observed_at=as_of,
        available_at=as_of + timedelta(days=1),
        source="test",
        quality=EvidenceQuality.PRIMARY,
    )
    with pytest.raises(ValueError, match="future data"):
        _context(as_of=as_of, evidence=(future,))


def test_confidence_is_not_a_simple_average_and_caps_weak_links() -> None:
    confidence = combine_confidence(
        evidence_quality=100,
        data_completeness=100,
        module_agreement=100,
        point_in_time_integrity=20,
    )

    assert confidence.confidence <= 30
    assert confidence.confidence != 80
    assert confidence.method == "weighted_geometric_with_weakest_link_cap"


def test_policy_assessment_contains_all_policy_dimensions() -> None:
    context = _context(evidence=_all_policy_evidence())
    output = PolicyResearchModule().evaluate(context, {})

    assert output.assessment.module is ResearchModuleName.POLICY
    assert output.regulatory_environment == "regulatory_environment summary"
    assert output.geopolitical_factors == "geopolitical_factors summary"
    assert output.assessment.confidence.data_completeness == 100


def test_value_research_runs_policy_financial_and_industry_dependencies() -> None:
    evidence = (
        *_all_policy_evidence(),
        *_evidence_set(
            ResearchModuleName.FINANCIAL,
            ("revenue", "profit", "cash_flow", "debt", "roe", "roic"),
        ),
        *_evidence_set(
            ResearchModuleName.INDUSTRY,
            ("industry_trend", "industry_heat", "industry_cycle", "relative_strength"),
        ),
        *_evidence_set(
            ResearchModuleName.VALUE,
            ("survival", "cycle", "valuation", "growth"),
        ),
    )
    context = _context(evidence=evidence)
    request = _request(context, modules=(ResearchModuleName.VALUE,))
    engine = ResearchEngine(
        modules=(
            PolicyResearchModule(),
            FinancialResearchModule(),
            IndustryResearchModule(),
            ValueResearchModule(),
        )
    )

    run = engine.run(request)

    assert [item.module for item in run.report.assessments] == [
        ResearchModuleName.FINANCIAL,
        ResearchModuleName.POLICY,
        ResearchModuleName.INDUSTRY,
        ResearchModuleName.VALUE,
    ]
    assert run.report.thesis == request.thesis
    assert run.report.counter_thesis == request.counter_thesis
    assert run.report.invalidation_conditions == request.invalidation_conditions
    assert run.signal.action is SignalAction.RESEARCH
    assert run.signal.features["informational_only"] is True
    assert not hasattr(run, "order")


def test_technical_and_trend_research_produce_analysis_not_trade_decisions() -> None:
    context = _context(
        bars=_bars(260),
        evidence=_evidence_set(
            ResearchModuleName.TREND,
            ("market_sentiment_confirmation", "industry_heat_confirmation"),
            score=80,
        ),
    )
    technical = TechnicalResearchModule().evaluate(context, {})
    trend = TrendResearchModule().evaluate(
        context,
        {
            ResearchModuleName.POLICY: _supportive_assessment(
                ResearchModuleName.POLICY, context
            ),
            ResearchModuleName.INDUSTRY: _supportive_assessment(
                ResearchModuleName.INDUSTRY, context
            ),
            ResearchModuleName.TECHNICAL: technical,
        },
    )

    assert technical.score is not None
    assert technical.features["position_52_week"] is not None
    assert trend.features["framework_only"] is True
    assert "atr_stop_reference" in trend.features
    assert "pyramid_scenario_levels" in trend.features
    assert not hasattr(trend, "action")
    assert not hasattr(trend, "order")


def test_pattern_research_is_china_specific_and_requires_intraday_evidence() -> None:
    module = PatternResearchModule()
    us_context = _context(
        market=Market.US,
        bars=_bars(30, market=Market.US),
        evidence=(),
    )
    china_context = _context(bars=_bars(30), evidence=())

    not_applicable = module.evaluate(us_context, {})
    insufficient = module.evaluate(china_context, {})

    assert not_applicable.conclusion is ResearchConclusion.NOT_APPLICABLE
    assert insufficient.conclusion is ResearchConclusion.INSUFFICIENT_DATA
    assert insufficient.score is None


def test_financial_research_exposes_visible_restatement_history() -> None:
    as_of = datetime(2026, 1, 2, tzinfo=UTC)
    instrument = _instrument(Market.CHINA_A)
    facts = (
        FundamentalFact(
            instrument=instrument,
            metric="revenue",
            period_end=date(2025, 12, 31),
            published_at=as_of - timedelta(days=2),
            available_at=as_of - timedelta(days=2),
            value=Decimal("100"),
            source="test",
        ),
        FundamentalFact(
            instrument=instrument,
            metric="revenue",
            period_end=date(2025, 12, 31),
            published_at=as_of - timedelta(days=1),
            available_at=as_of - timedelta(days=1),
            value=Decimal("90"),
            revision=1,
            source="test",
        ),
    )
    context = _context(
        as_of=as_of,
        evidence=_evidence_set(
            ResearchModuleName.FINANCIAL,
            ("revenue", "profit", "cash_flow", "debt", "roe", "roic"),
        ),
        fundamentals={"revenue": facts},
    )

    assessment = FinancialResearchModule().evaluate(context, {})

    assert assessment.features["restatement_detected"] is True
    assert "revenue" in str(assessment.features["restated_metrics"])


def _supportive_assessment(
    module: ResearchModuleName,
    context: ResearchContext,
):
    from tong_quant.research.base import evidence_driven_assessment

    return evidence_driven_assessment(
        module=module,
        context=_context(evidence=_evidence(module, "score")),
        required_names=frozenset({"score"}),
        model_version="test",
    )


def _request(
    context: ResearchContext,
    *,
    modules: tuple[ResearchModuleName, ...],
) -> ResearchRequest:
    return ResearchRequest(
        context=context,
        modules=modules,
        thesis="Industry demand and company economics may improve",
        counter_thesis="Policy transmission or company execution may disappoint",
        invalidation_conditions=(_invalidation(),),
        unresolved_questions=("Can margins remain durable?",),
    )


def _invalidation() -> ThesisInvalidationCondition:
    return ThesisInvalidationCondition(
        condition_id="revenue-growth",
        description="Revenue growth falls below 5 percent",
        metric="revenue_growth",
        operator="<",
        threshold=5,
        observation_window="two consecutive quarters",
        rationale="The thesis depends on durable demand growth",
    )


def _context(
    *,
    as_of: datetime | None = None,
    market: Market = Market.CHINA_A,
    bars: tuple[Bar, ...] = (),
    evidence: tuple[ResearchEvidence, ...] = (),
    fundamentals: dict[str, tuple[FundamentalFact, ...]] | None = None,
) -> ResearchContext:
    timestamp = as_of or datetime(2026, 1, 2, tzinfo=UTC)
    return ResearchContext(
        queue_id="queue-1",
        queue_entry=_queue_entry(timestamp, market),
        as_of=timestamp,
        bars=bars,
        fundamentals=fundamentals or {},
        evidence=evidence,
    )


def _queue_entry(as_of: datetime, market: Market) -> ResearchQueueEntry:
    candidate = OpportunityCandidate(
        instrument=_instrument(market),
        discovery_source="discovery.policy",
        discovered_at=as_of,
        available_at=as_of,
        thesis="Potential opportunity",
        evidence=("Published evidence",),
        urgency_score=70,
        confidence_score=75,
    )
    component = ScoreComponent(
        name="industry",
        score=70,
        confidence=80,
        weight=1,
        contribution=70,
        reasons=("Industry evidence",),
    )
    score = CompositeScore(
        score_type=ScoreType.RESEARCH,
        score=70,
        confidence=80,
        calculated_at=as_of,
        components=(component,),
        reasons=("Research priority",),
        model_version="v0.4",
    )
    hard_screen = HardScreenResult(
        rule_id="data_quality",
        passed=True,
        evaluated_at=as_of,
        available_at=as_of,
        reasons=("Data passed",),
    )
    return ResearchQueueEntry(
        candidate=candidate,
        admitted_at=as_of,
        priority_score=72,
        urgency_score=70,
        confidence_score=75,
        research_score=score,
        hard_screen_results=(hard_screen,),
    )


def _instrument(market: Market) -> Instrument:
    symbol = "600000" if market is Market.CHINA_A else "TEST"
    return Instrument(symbol, market, "Example")


def _evidence(
    module: ResearchModuleName,
    name: str,
    *,
    score: float = 70,
    as_of: datetime | None = None,
) -> tuple[ResearchEvidence, ...]:
    timestamp = as_of or datetime(2026, 1, 2, tzinfo=UTC)
    return (
        ResearchEvidence(
            evidence_id=f"{module.value}:{name}",
            module=module,
            name=name,
            value=score,
            observed_at=timestamp,
            available_at=timestamp,
            source="test",
            quality=EvidenceQuality.PRIMARY,
            metadata={"summary": f"{name} summary", "finding": f"{name} reviewed"},
        ),
    )


def _evidence_set(
    module: ResearchModuleName,
    names: tuple[str, ...],
    *,
    score: float = 70,
) -> tuple[ResearchEvidence, ...]:
    return tuple(item for name in names for item in _evidence(module, name, score=score))


def _all_policy_evidence() -> tuple[ResearchEvidence, ...]:
    return _evidence_set(
        ResearchModuleName.POLICY,
        (
            "regulatory_environment",
            "industrial_policy",
            "fiscal_policy",
            "monetary_policy",
            "geopolitical_factors",
        ),
    )


def _bars(count: int, *, market: Market = Market.CHINA_A) -> tuple[Bar, ...]:
    instrument = _instrument(market)
    start = datetime(2025, 1, 1, tzinfo=UTC)
    bars = []
    for index in range(count):
        timestamp = start + timedelta(days=index)
        close = Decimal("10") + Decimal(index) / Decimal("100")
        bars.append(
            Bar(
                instrument=instrument,
                timestamp=timestamp,
                available_at=timestamp,
                open=close - Decimal("0.05"),
                high=close + Decimal("0.10"),
                low=close - Decimal("0.10"),
                close=close,
                volume=Decimal("1000") + index,
                source="test",
            )
        )
    return tuple(bars)
