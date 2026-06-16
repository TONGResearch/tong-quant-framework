from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from tong_quant.domain.enums import (
    InvestmentAssessmentStatus,
    PortfolioAssetCategory,
    PortfolioProposalStatus,
)
from tong_quant.portfolio.models import (
    PortfolioCandidate,
    PortfolioProposal,
    PositionProposal,
)
from tong_quant.risk.assessment import RiskAssessmentEngine
from tong_quant.risk.models import RiskBudget


@dataclass(frozen=True, slots=True)
class PortfolioConstructionConfig:
    base_currency: str = "CNY"
    minimum_cash_weight: float = 0.05
    maximum_single_position_weight: float = 0.10
    target_volatility: float = 0.15
    total_risk_budget: float = 0.12
    per_position_risk_budget: float = 0.03
    per_sector_risk_budget: float = 0.06
    per_theme_risk_budget: float = 0.05
    model_version: str = "portfolio-proposal-v0.7"


@dataclass(slots=True)
class PortfolioProposalEngine:
    config: PortfolioConstructionConfig = PortfolioConstructionConfig()
    risk_engine: RiskAssessmentEngine = field(default_factory=RiskAssessmentEngine)

    def build(
        self,
        candidates: tuple[PortfolioCandidate, ...],
        *,
        as_of: datetime | None = None,
    ) -> PortfolioProposal:
        proposal_as_of = as_of or datetime.now(UTC)
        if not candidates:
            raise ValueError("PortfolioProposal requires InvestmentScore candidates")
        eligible = tuple(_eligible_candidate(candidate) for candidate in candidates)
        weights = _raw_weights(eligible)
        weights = _cap_weights(weights, self.config.maximum_single_position_weight)
        weights = _apply_volatility_target(
            weights,
            eligible,
            self.config.target_volatility,
            self.config.minimum_cash_weight,
        )
        positions = tuple(
            _position(candidate, weights[candidate.investment_score_id])
            for candidate in eligible
        )
        cash_weight = max(0.0, 1.0 - sum(position.proposed_weight for position in positions))
        all_positions = (
            *positions,
            PositionProposal(
                instrument=None,
                asset_category=PortfolioAssetCategory.CASH,
                proposed_weight=round(cash_weight, 6),
                min_weight=0.0,
                max_weight=1.0,
                confidence=100,
                liquidity_score=100,
                volatility_estimate=0,
                expected_role="cash buffer",
                reasons=("Cash preserves optionality and risk budget",),
                constraints_applied=("minimum_cash_weight",),
            ),
        )
        proposal_id = str(uuid4())
        risk_budget = RiskBudget(
            total_risk_budget=self.config.total_risk_budget,
            per_position_risk_budget=self.config.per_position_risk_budget,
            per_sector_risk_budget=self.config.per_sector_risk_budget,
            per_theme_risk_budget=self.config.per_theme_risk_budget,
        )
        risk_assessment = self.risk_engine.assess(
            proposal_id=proposal_id,
            positions=all_positions,
            risk_budget=risk_budget,
            as_of=proposal_as_of,
        )
        status = PortfolioProposalStatus.PROPOSED
        if risk_assessment.status.value == "conditional":
            status = PortfolioProposalStatus.CONDITIONAL
        if risk_assessment.status.value == "rejected":
            status = PortfolioProposalStatus.REJECTED
        return PortfolioProposal(
            proposal_id=proposal_id,
            as_of=proposal_as_of,
            base_currency=self.config.base_currency,
            status=status,
            positions=all_positions,
            cash_weight=round(cash_weight, 6),
            target_volatility=self.config.target_volatility,
            expected_portfolio_volatility=round(
                sum(
                    position.proposed_weight * position.volatility_estimate
                    for position in all_positions
                ),
                6,
            ),
            expected_max_drawdown=round(
                max(
                    (
                        position.proposed_weight * position.volatility_estimate * 2
                        for position in all_positions
                    ),
                    default=0,
                ),
                6,
            ),
            concentration_summary=_concentration_summary(all_positions),
            exposure_summary=_exposure_summary(all_positions),
            correlation_summary=_correlation_summary(all_positions),
            risk_assessment=risk_assessment,
            reasons=("PortfolioProposal is a research artifact built from InvestmentScore",),
            limitations=(
                "Research artifact only",
                "Not an execution instruction",
                "No execution-side object or live connectivity is created",
            ),
            model_version=self.config.model_version,
            metadata={"artifact_type": "research_artifact"},
        )


def _eligible_candidate(candidate: PortfolioCandidate) -> PortfolioCandidate:
    if candidate.assessment_status not in {
        InvestmentAssessmentStatus.COMPLETED,
        InvestmentAssessmentStatus.LOW_CONFIDENCE,
    }:
        raise ValueError("Portfolio must consume scored InvestmentScore outputs only")
    if not candidate.investment_score_id.strip():
        raise ValueError("Portfolio cannot bypass InvestmentScore")
    if not candidate.validation_report_id.strip():
        raise ValueError("Portfolio cannot bypass Validation")
    return candidate


def _raw_weights(candidates: tuple[PortfolioCandidate, ...]) -> dict[str, float]:
    weighted_scores = {
        candidate.investment_score_id: candidate.score * candidate.confidence / 100
        for candidate in candidates
    }
    total = sum(weighted_scores.values())
    if total <= 0:
        raise ValueError("Portfolio candidates have no positive InvestmentScore weight")
    return {key: value / total for key, value in weighted_scores.items()}


def _cap_weights(weights: dict[str, float], cap: float) -> dict[str, float]:
    capped = {key: min(value, cap) for key, value in weights.items()}
    total = sum(capped.values())
    if total <= 0:
        return capped
    return {key: value / total * min(total, 1.0) for key, value in capped.items()}


def _apply_volatility_target(
    weights: dict[str, float],
    candidates: tuple[PortfolioCandidate, ...],
    target_volatility: float,
    minimum_cash_weight: float,
) -> dict[str, float]:
    by_score_id = {candidate.investment_score_id: candidate for candidate in candidates}
    volatility = sum(
        weight * by_score_id[key].volatility
        for key, weight in weights.items()
    )
    investable_budget = max(0.0, 1.0 - minimum_cash_weight)
    scale = 1.0
    if volatility > target_volatility and volatility > 0:
        scale = target_volatility / volatility
    scale = min(scale, investable_budget / max(sum(weights.values()), 1e-12))
    return {key: round(value * scale, 6) for key, value in weights.items()}


def _position(candidate: PortfolioCandidate, weight: float) -> PositionProposal:
    flags: tuple[str, ...] = (f"correlation={candidate.average_correlation}",)
    if candidate.assessment_status is InvestmentAssessmentStatus.LOW_CONFIDENCE:
        flags = (*flags, "low_confidence_investment_score")
    return PositionProposal(
        instrument=candidate.instrument,
        asset_category=PortfolioAssetCategory.EQUITY,
        proposed_weight=round(weight, 6),
        min_weight=0.0,
        max_weight=min(1.0, max(weight, 0.10)),
        confidence=candidate.confidence,
        liquidity_score=candidate.liquidity_score,
        volatility_estimate=candidate.volatility,
        expected_role=candidate.expected_role,
        reasons=candidate.reasons,
        risk_flags=flags,
        constraints_applied=("investment_score_weighting", "risk_budget", "volatility_target"),
    )


def _concentration_summary(positions: tuple[PositionProposal, ...]) -> dict[str, float]:
    non_cash = [
        position.proposed_weight
        for position in positions
        if position.instrument is not None
    ]
    top_five = sorted(non_cash, reverse=True)[:5]
    return {
        "maximum_position_weight": round(max(non_cash, default=0), 6),
        "top_five_weight": round(sum(top_five), 6),
    }


def _exposure_summary(
    positions: tuple[PositionProposal, ...],
) -> dict[str, dict[str, float]]:
    summary: dict[str, dict[str, float]] = {
        "sector": {},
        "country": {},
        "theme": {},
        "asset_category": {},
    }
    for position in positions:
        category = position.asset_category.value
        summary["asset_category"][category] = (
            summary["asset_category"].get(category, 0.0) + position.proposed_weight
        )
        if position.instrument is None:
            for dimension in ("sector", "country", "theme"):
                summary[dimension]["cash"] = (
                    summary[dimension].get("cash", 0.0) + position.proposed_weight
                )
            continue
        sector = position.instrument.industry or "unknown"
        country = position.instrument.market.value
        theme = position.expected_role
        summary["sector"][sector] = summary["sector"].get(sector, 0.0) + position.proposed_weight
        summary["country"][country] = (
            summary["country"].get(country, 0.0) + position.proposed_weight
        )
        summary["theme"][theme] = summary["theme"].get(theme, 0.0) + position.proposed_weight
    return {
        dimension: {key: round(value, 6) for key, value in values.items()}
        for dimension, values in summary.items()
    }


def _correlation_summary(positions: tuple[PositionProposal, ...]) -> dict[str, float]:
    values = [
        position.proposed_weight * float(position.risk_flags[0].split("=", 1)[1])
        for position in positions
        if position.risk_flags and position.risk_flags[0].startswith("correlation=")
    ]
    return {"weighted_average_correlation": round(sum(values), 6)}


__all__ = ["PortfolioConstructionConfig", "PortfolioProposalEngine"]
