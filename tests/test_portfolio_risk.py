from datetime import UTC, datetime
from pathlib import Path

import pytest

from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import (
    InvestmentAssessmentStatus,
    Market,
    PortfolioAssetCategory,
    PortfolioProposalStatus,
)
from tong_quant.domain.models import Instrument
from tong_quant.portfolio import (
    PortfolioCandidate,
    PortfolioConstructionConfig,
    PortfolioProposalEngine,
    PositionProposal,
    SQLitePortfolioRepository,
)


def test_portfolio_proposal_consumes_investment_score_candidates_only() -> None:
    candidate = _candidate("600000", "score-1", 88, 82)

    proposal = PortfolioProposalEngine(
        PortfolioConstructionConfig(maximum_single_position_weight=0.20)
    ).build((candidate,), as_of=datetime(2026, 1, 2, tzinfo=UTC))

    assert proposal.status in {
        PortfolioProposalStatus.PROPOSED,
        PortfolioProposalStatus.CONDITIONAL,
        PortfolioProposalStatus.REJECTED,
    }
    assert proposal.metadata["artifact_type"] == "research_artifact"
    assert "Research artifact only" in proposal.limitations
    assert proposal.cash_weight >= 0.05
    assert proposal.risk_assessment is not None
    assert proposal.risk_assessment.risk_budget.total_risk_budget == 0.12
    assert len(proposal.risk_assessment.scenario_results) == 4
    assert not hasattr(proposal, "order")


def test_candidate_without_investment_score_is_rejected() -> None:
    with pytest.raises(ValueError, match="InvestmentScore"):
        PortfolioCandidate(
            instrument=_instrument("600000"),
            investment_assessment_id="assessment-1",
            investment_score_id="",
            validation_report_id="validation-1",
            score=80,
            confidence=80,
            assessment_status=InvestmentAssessmentStatus.COMPLETED,
            validation_status="reliable",
            expected_role="value",
            sector="Banks",
            country="China",
            theme="Value",
            volatility=0.2,
            liquidity_score=80,
            average_correlation=0.3,
            max_drawdown=0.2,
            reasons=("scored",),
        )


def test_low_confidence_high_score_remains_constrained() -> None:
    candidate = _candidate(
        "600000",
        "score-low-confidence",
        98,
        35,
        status=InvestmentAssessmentStatus.LOW_CONFIDENCE,
    )

    proposal = PortfolioProposalEngine().build(
        (candidate,),
        as_of=datetime(2026, 1, 2, tzinfo=UTC),
    )
    equity = [position for position in proposal.positions if position.instrument is not None][0]

    assert "low_confidence_investment_score" in equity.risk_flags
    assert equity.confidence == 35


def test_risk_assessment_flags_concentration_liquidity_and_stress() -> None:
    candidates = (
        _candidate("600000", "score-1", 90, 80, liquidity=40, volatility=0.35),
        _candidate("600001", "score-2", 85, 78, liquidity=45, volatility=0.32),
    )

    proposal = PortfolioProposalEngine(
        PortfolioConstructionConfig(
            maximum_single_position_weight=0.60,
            target_volatility=0.50,
            minimum_cash_weight=0.05,
        )
    ).build(candidates, as_of=datetime(2026, 1, 2, tzinfo=UTC))

    assert proposal.risk_assessment is not None
    assert proposal.risk_assessment.liquidity_risk > 0
    assert any(
        result.scenario.name == "single stock -30%"
        for result in proposal.risk_assessment.scenario_results
    )
    assert proposal.risk_assessment.required_adjustments
    assert any(
        "per_sector_risk_budget exceeded" in adjustment
        for adjustment in proposal.risk_assessment.required_adjustments
    )
    assert any(
        "per_theme_risk_budget exceeded" in adjustment
        for adjustment in proposal.risk_assessment.required_adjustments
    )


def test_fund_category_is_reserved_but_not_constructed_by_engine() -> None:
    fund_position = PositionProposal(
        instrument=_instrument("510300"),
        asset_category=PortfolioAssetCategory.FUND,
        proposed_weight=0.10,
        min_weight=0.0,
        max_weight=0.20,
        confidence=60,
        liquidity_score=80,
        volatility_estimate=0.12,
        expected_role="reserved fund exposure",
        reasons=("Fund category is reserved for future architecture",),
    )

    assert fund_position.asset_category is PortfolioAssetCategory.FUND


def test_portfolio_repository_persists_research_artifacts(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "portfolio.sqlite3")
    store.initialize()
    proposal = PortfolioProposalEngine().build(
        (_candidate("600000", "score-1", 88, 82),),
        as_of=datetime(2026, 1, 2, tzinfo=UTC),
    )

    SQLitePortfolioRepository(store).save_proposal(proposal)

    assert store.table_count("portfolio_proposals") == 1
    assert store.table_count("position_proposals") == 2
    assert store.table_count("risk_assessments") == 1
    assert store.table_count("portfolio_exposures") == 3
    assert store.table_count("portfolio_constraints") == 4


def _candidate(
    symbol: str,
    score_id: str,
    score: float,
    confidence: float,
    *,
    status: InvestmentAssessmentStatus = InvestmentAssessmentStatus.COMPLETED,
    liquidity: float = 85,
    volatility: float = 0.18,
) -> PortfolioCandidate:
    return PortfolioCandidate(
        instrument=_instrument(symbol),
        investment_assessment_id=f"assessment-{score_id}",
        investment_score_id=score_id,
        validation_report_id=f"validation-{score_id}",
        score=score,
        confidence=confidence,
        assessment_status=status,
        validation_status="conditionally_reliable",
        expected_role="Value",
        sector="Banks",
        country="China",
        theme="Value",
        volatility=volatility,
        liquidity_score=liquidity,
        average_correlation=0.35,
        max_drawdown=0.25,
        reasons=("InvestmentScore survived research and validation",),
        limitations=("PortfolioProposal is not an execution instruction",),
    )


def _instrument(symbol: str) -> Instrument:
    return Instrument(
        symbol=symbol,
        market=Market.CHINA_A,
        name=f"Instrument {symbol}",
        industry="Banks",
        available_at=datetime(2026, 1, 1, tzinfo=UTC),
        source="test",
    )
