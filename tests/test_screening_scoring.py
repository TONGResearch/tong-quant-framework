from datetime import UTC, datetime

import pytest

from tong_quant.domain.enums import (
    ScoreType,
    ScreeningDimensionName,
)
from tong_quant.screening.dimensions import DimensionEvidence
from tong_quant.screening.macro import macro_evaluator
from tong_quant.screening.models import DimensionAssessment
from tong_quant.screening.scoring import (
    ScoreConfig,
    WeightedScoreAggregator,
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
