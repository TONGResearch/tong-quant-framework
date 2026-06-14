from datetime import UTC, datetime

import pytest

from tong_quant.domain.enums import (
    Market,
    Regime,
    ScoreType,
    ScreeningDimensionName,
)
from tong_quant.market_regime.models import (
    MarketRegime,
    RegimeContribution,
)
from tong_quant.screening.dimensions import DimensionEvidence
from tong_quant.screening.macro import macro_evaluator
from tong_quant.screening.models import DimensionAssessment
from tong_quant.screening.scoring import (
    ScoreConfig,
    WeightedScoreAggregator,
    default_investment_score_config,
    default_research_score_config,
)


def test_research_score_uses_all_seven_dimensions() -> None:
    as_of = datetime(2026, 1, 2, tzinfo=UTC)
    score = WeightedScoreAggregator(default_research_score_config()).aggregate(
        _assessments(as_of, 70),
        calculated_at=as_of,
    )

    assert score.score_type is ScoreType.RESEARCH
    assert score.score == 70
    assert {component.name for component in score.components} == {
        dimension.value for dimension in ScreeningDimensionName
    }


def test_no_single_factor_can_exceed_configured_weight() -> None:
    with pytest.raises(ValueError, match="no single score component"):
        ScoreConfig(
            score_type=ScoreType.RESEARCH,
            weights={"growth": 0.8, "valuation": 0.2},
            model_version="test",
            maximum_component_weight=0.50,
        )


def test_market_regime_is_high_weight_but_not_a_hard_decision() -> None:
    as_of = datetime(2026, 1, 2, tzinfo=UTC)
    scorer = WeightedScoreAggregator(default_investment_score_config())
    assessments = _assessments(as_of, 70)

    bull = scorer.aggregate(
        assessments,
        calculated_at=as_of,
        regime=_regime(as_of, Regime.BULL, 80),
    )
    bear = scorer.aggregate(
        assessments,
        calculated_at=as_of,
        regime=_regime(as_of, Regime.BEAR, -80),
    )

    regime_component = next(
        component for component in bull.components if component.name == "market_regime"
    )
    assert regime_component.weight == 0.25
    assert bull.score > bear.score
    assert bull.score_type is ScoreType.INVESTMENT
    assert bear.score_type is ScoreType.INVESTMENT


def test_investment_score_requires_market_regime() -> None:
    as_of = datetime(2026, 1, 2, tzinfo=UTC)

    with pytest.raises(ValueError, match="requires a Market Regime"):
        WeightedScoreAggregator(default_investment_score_config()).aggregate(
            _assessments(as_of, 70),
            calculated_at=as_of,
        )


def test_macro_is_a_dedicated_dimension() -> None:
    as_of = datetime(2026, 1, 2, tzinfo=UTC)
    assessment = macro_evaluator().evaluate(
        DimensionEvidence(
            dimension=ScreeningDimensionName.MACRO,
            score=60,
            confidence=70,
            evaluated_at=as_of,
            available_at=as_of,
            reasons=("Credit conditions are stable",),
        )
    )

    assert assessment.dimension is ScreeningDimensionName.MACRO
    assert assessment.source == "screening.macro"


def _assessments(
    as_of: datetime,
    score: float,
) -> tuple[DimensionAssessment, ...]:
    return tuple(
        DimensionAssessment(
            dimension=dimension,
            score=score,
            confidence=80,
            evaluated_at=as_of,
            available_at=as_of,
            reasons=(f"{dimension.value} evidence reviewed",),
            source=f"screening.{dimension.value}",
            model_version="v0.4",
        )
        for dimension in ScreeningDimensionName
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
