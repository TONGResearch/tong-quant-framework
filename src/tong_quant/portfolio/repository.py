from dataclasses import asdict, dataclass

from tong_quant.data.storage.sqlite import SQLiteStore, instrument_id
from tong_quant.portfolio.models import PortfolioProposal


@dataclass(slots=True)
class SQLitePortfolioRepository:
    store: SQLiteStore

    def save_proposal(self, proposal: PortfolioProposal) -> None:
        self.store.save_portfolio_proposal(
            proposal_id=proposal.proposal_id,
            as_of=proposal.as_of,
            base_currency=proposal.base_currency,
            status=proposal.status.value,
            cash_weight=proposal.cash_weight,
            target_volatility=proposal.target_volatility,
            expected_portfolio_volatility=proposal.expected_portfolio_volatility,
            expected_max_drawdown=proposal.expected_max_drawdown,
            concentration_summary=proposal.concentration_summary,
            exposure_summary=proposal.exposure_summary,
            correlation_summary=proposal.correlation_summary,
            reasons=proposal.reasons,
            limitations=proposal.limitations,
            metadata=proposal.metadata,
            model_version=proposal.model_version,
        )
        for position in proposal.positions:
            self.store.save_position_proposal(
                proposal_id=proposal.proposal_id,
                instrument_id_value=(
                    None if position.instrument is None else instrument_id(position.instrument)
                ),
                asset_category=position.asset_category.value,
                proposed_weight=position.proposed_weight,
                min_weight=position.min_weight,
                max_weight=position.max_weight,
                confidence=position.confidence,
                liquidity_score=position.liquidity_score,
                volatility_estimate=position.volatility_estimate,
                expected_role=position.expected_role,
                reasons=position.reasons,
                risk_flags=position.risk_flags,
                constraints_applied=position.constraints_applied,
            )
        assessment = proposal.risk_assessment
        if assessment is None:
            return
        self.store.save_risk_assessment(
            assessment_id=assessment.assessment_id,
            proposal_id=assessment.proposal_id,
            assessed_at=assessment.assessed_at,
            status=assessment.status.value,
            score=assessment.score,
            confidence=assessment.confidence,
            risk_budget=asdict(assessment.risk_budget),
            concentration_risk=assessment.concentration_risk,
            correlation_risk=assessment.correlation_risk,
            volatility_risk=assessment.volatility_risk,
            drawdown_risk=assessment.drawdown_risk,
            liquidity_risk=assessment.liquidity_risk,
            scenario_results=[asdict(result) for result in assessment.scenario_results],
            reasons=assessment.reasons,
            required_adjustments=assessment.required_adjustments,
            limitations=assessment.limitations,
            model_version=assessment.model_version,
        )
        for exposure in (
            assessment.sector_exposure,
            assessment.country_exposure,
            assessment.theme_exposure,
        ):
            self.store.save_portfolio_exposure(
                proposal_id=proposal.proposal_id,
                dimension=exposure.dimension,
                exposures=exposure.exposures,
                max_allowed=exposure.max_allowed,
                breached=exposure.breached,
                reasons=exposure.reasons,
            )
        for name, value in asdict(assessment.risk_budget).items():
            self.store.save_portfolio_constraint(
                proposal_id=proposal.proposal_id,
                constraint_name=name,
                constraint_value=float(value),
                breached=name in " ".join(assessment.required_adjustments),
                reasons=assessment.required_adjustments or ("constraint recorded",),
            )


__all__ = ["SQLitePortfolioRepository"]
