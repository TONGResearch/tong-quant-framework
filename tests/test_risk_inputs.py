from dataclasses import replace
from datetime import UTC, datetime

import pytest

from tong_quant.domain.enums import RiskAssessmentStatus, StressScenarioType
from tong_quant.risk.assessment import RiskAssessmentEngine, RiskConstraintConfig
from tong_quant.risk.models import (
    RiskBudget,
    RiskPositionInput,
    StressScenario,
    StressScenarioResult,
)


def _cash() -> RiskPositionInput:
    return RiskPositionInput(
        position_id="cash", asset_category="cash", proposed_weight=1,
        confidence=100, liquidity_score=100, volatility_estimate=0,
    )


@pytest.mark.parametrize("weights", [(0.1,), (0.7, 0.7), ()])
def test_risk_rejects_unfunded_or_overfunded_position_sets(weights: tuple[float, ...]) -> None:
    positions = tuple(
        replace(_cash(), position_id=f"cash-{index}", proposed_weight=weight)
        for index, weight in enumerate(weights)
    )
    with pytest.raises(ValueError, match="sum to one"):
        RiskAssessmentEngine().assess(
            proposal_id="proposal", positions=positions,
            risk_budget=RiskBudget(0.12, 0.03, 0.06, 0.05),
            as_of=datetime(2026, 1, 1, tzinfo=UTC),
        )


def test_risk_rejects_duplicate_position_identity() -> None:
    duplicate = replace(_cash(), proposed_weight=0.5)
    with pytest.raises(ValueError, match="unique identifiers"):
        RiskAssessmentEngine().assess(
            proposal_id="proposal", positions=(duplicate, duplicate),
            risk_budget=RiskBudget(0.12, 0.03, 0.06, 0.05),
        )


def test_acceptable_risk_cannot_hide_required_adjustments() -> None:
    assessment = RiskAssessmentEngine().assess(
        proposal_id="proposal", positions=(_cash(),),
        risk_budget=RiskBudget(0.12, 0.03, 0.06, 0.05),
    )
    assert assessment.status is RiskAssessmentStatus.ACCEPTABLE
    with pytest.raises(ValueError, match="unresolved breaches or adjustments"):
        replace(assessment, required_adjustments=("sector risk unresolved",))


@pytest.mark.parametrize("value", [0, -0.1, 1.1, float("nan"), float("inf")])
def test_risk_rejects_invalid_constraint_configuration(value: float) -> None:
    with pytest.raises(ValueError, match="maximum_drawdown"):
        RiskConstraintConfig(maximum_drawdown=value)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -0.1])
def test_stress_results_reject_non_finite_or_negative_loss(value: float) -> None:
    with pytest.raises(ValueError, match="finite and non-negative"):
        StressScenarioResult(
            scenario=StressScenario(StressScenarioType.BROAD_MARKET, "market decline", -0.1),
            estimated_loss=value, affected_weight=1, breached=False,
            reasons=("scenario evaluated",),
        )
