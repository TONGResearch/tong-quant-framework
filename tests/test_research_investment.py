from datetime import UTC, datetime

import pytest

from tong_quant.domain.enums import (
    InvestmentAssessmentStatus,
    Market,
    Regime,
    ResearchConclusion,
    ResearchModuleName,
    ResearchRunStatus,
    ScoreType,
)
from tong_quant.market_regime.models import MarketRegime, RegimeContribution
from tong_quant.research.compatibility import (
    LegacyResearchOutcomeAdapter,
    LegacyResearchOutcomeRecord,
)
from tong_quant.research.investment import InvestmentAssessmentBuilder
from tong_quant.research.models import (
    ConfidenceBreakdown,
    ResearchAssessment,
    ResearchReport,
    ThesisInvalidationCondition,
)


def test_investment_assessment_consumes_completed_research_report() -> None:
    as_of = datetime(2026, 1, 2, tzinfo=UTC)
    builder = InvestmentAssessmentBuilder()
    report = _report(as_of)

    bull = builder.build(
        report,
        assessed_at=as_of,
        market_regime=_regime(as_of, Regime.BULL, 80),
    )
    bear = builder.build(
        report,
        assessed_at=as_of,
        market_regime=_regime(as_of, Regime.BEAR, -80),
    )

    assert bull.status is InvestmentAssessmentStatus.COMPLETED
    assert bull.investment_score is not None
    assert bear.investment_score is not None
    assert bull.investment_score.score_type is ScoreType.INVESTMENT
    assert bull.investment_score.score > bear.investment_score.score
    assert not hasattr(bull, "approved")
    assert not hasattr(bull, "order")


def test_high_score_with_low_confidence_stays_low_confidence() -> None:
    as_of = datetime(2026, 1, 2, tzinfo=UTC)
    report = _report(as_of, score=95, confidence=35)

    assessment = InvestmentAssessmentBuilder().build(
        report,
        assessed_at=as_of,
        market_regime=_regime(as_of, Regime.BULL, 80),
    )

    assert assessment.status is InvestmentAssessmentStatus.LOW_CONFIDENCE
    assert assessment.investment_score is not None
    assert assessment.investment_score.score > 80
    assert assessment.investment_score.confidence < 60


def test_incomplete_report_cannot_produce_investment_score() -> None:
    as_of = datetime(2026, 1, 2, tzinfo=UTC)
    report = _report(as_of, status=ResearchRunStatus.INCOMPLETE)

    assessment = InvestmentAssessmentBuilder().build(report, assessed_at=as_of)

    assert assessment.status is InvestmentAssessmentStatus.INCOMPLETE
    assert assessment.investment_score is None


def test_insufficient_research_components_do_not_produce_score() -> None:
    as_of = datetime(2026, 1, 2, tzinfo=UTC)
    report = _report(
        as_of,
        assessments=(
            _assessment(ResearchModuleName.POLICY, as_of, score=None),
            _assessment(
                ResearchModuleName.PATTERN,
                as_of,
                score=None,
                conclusion=ResearchConclusion.NOT_APPLICABLE,
            ),
        ),
    )

    assessment = InvestmentAssessmentBuilder().build(report, assessed_at=as_of)

    assert assessment.status is InvestmentAssessmentStatus.INSUFFICIENT_DATA
    assert assessment.investment_score is None


def test_legacy_adapter_refuses_to_fabricate_missing_thesis_fields() -> None:
    as_of = datetime(2026, 1, 2, tzinfo=UTC)
    adapter = LegacyResearchOutcomeAdapter(
        assessment_mapper=lambda _: (_assessment(ResearchModuleName.POLICY, as_of),)
    )
    record = LegacyResearchOutcomeRecord(
        queue_id="queue-1",
        instrument_id="china_a:equity:600000",
        completed_at=as_of,
        available_at=as_of,
        thesis="Legacy thesis",
        risks=("Legacy risk",),
        confidence_score=70,
    )

    with pytest.raises(ValueError, match="counter thesis"):
        adapter.to_research_report(
            record,
            report_id="report-legacy",
            counter_thesis="",
            invalidation_conditions=(_invalidation(),),
        )


def _report(
    as_of: datetime,
    *,
    status: ResearchRunStatus = ResearchRunStatus.COMPLETED,
    score: float = 75,
    confidence: float = 80,
    assessments: tuple[ResearchAssessment, ...] | None = None,
) -> ResearchReport:
    module_assessments = assessments or (
        _assessment(ResearchModuleName.POLICY, as_of, score=score, confidence=confidence),
        _assessment(ResearchModuleName.FINANCIAL, as_of, score=score, confidence=confidence),
        _assessment(ResearchModuleName.INDUSTRY, as_of, score=score, confidence=confidence),
        _assessment(ResearchModuleName.VALUE, as_of, score=score, confidence=confidence),
        _assessment(ResearchModuleName.TECHNICAL, as_of, score=score, confidence=confidence),
        _assessment(ResearchModuleName.TREND, as_of, score=score, confidence=confidence),
    )
    return ResearchReport(
        report_id="report-1",
        queue_id="queue-1",
        instrument_id="china_a:equity:600000",
        generated_at=as_of,
        available_at=as_of,
        status=status,
        thesis="Research thesis",
        counter_thesis="Research counter thesis",
        invalidation_conditions=(_invalidation(),),
        assessments=module_assessments,
        policy_assessment=None,
        confidence=ConfidenceBreakdown(
            evidence_quality=confidence,
            data_completeness=confidence,
            module_agreement=confidence,
            point_in_time_integrity=100,
            confidence=confidence,
        ),
        key_findings=("Research finding",),
        key_risks=("Research risk",),
        unresolved_questions=(),
        market_regime=None,
        model_version="research-report-v0.5",
    )


def _assessment(
    module: ResearchModuleName,
    as_of: datetime,
    *,
    score: float | None = 75,
    confidence: float = 80,
    conclusion: ResearchConclusion = ResearchConclusion.SUPPORTIVE,
) -> ResearchAssessment:
    return ResearchAssessment(
        module=module,
        conclusion=conclusion,
        score=score,
        confidence=ConfidenceBreakdown(
            evidence_quality=confidence,
            data_completeness=confidence,
            module_agreement=confidence,
            point_in_time_integrity=100,
            confidence=confidence,
        ),
        evaluated_at=as_of,
        available_at=as_of,
        findings=(f"{module.value} finding",),
        risks=(f"{module.value} risk",),
        limitations=(),
        evidence_ids=(),
        model_version="test",
    )


def _invalidation() -> ThesisInvalidationCondition:
    return ThesisInvalidationCondition(
        condition_id="growth",
        description="Growth falls below zero",
        metric="growth",
        operator="<",
        threshold=0,
        observation_window="one year",
        rationale="Thesis depends on growth",
    )


def _regime(as_of: datetime, state: Regime, score: float) -> MarketRegime:
    contribution = RegimeContribution(
        metric="market_trend",
        value=score / 100,
        weight=1,
        contribution=score,
        reason="Market trend contribution",
    )
    return MarketRegime(
        market=Market.CHINA_A,
        state=state,
        confidence=80,
        reasons=(contribution.reason,),
        as_of=as_of,
        score=score,
        contributions=(contribution,),
        model_version="test",
        subject="China A-share market",
    )
