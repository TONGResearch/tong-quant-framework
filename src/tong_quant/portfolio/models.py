from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from tong_quant.domain.enums import (
    InvestmentAssessmentStatus,
    PortfolioAssetCategory,
    PortfolioProposalStatus,
)
from tong_quant.domain.models import Instrument, require_timezone

if TYPE_CHECKING:
    from tong_quant.risk.models import RiskAssessment


def _require_fraction(name: str, value: float) -> None:
    if not 0 <= value <= 1:
        raise ValueError(f"{name} must be between zero and one")


def _require_percentage(name: str, value: float) -> None:
    if not 0 <= value <= 100:
        raise ValueError(f"{name} must be between 0 and 100")


@dataclass(frozen=True, slots=True)
class PortfolioCandidate:
    instrument: Instrument
    investment_assessment_id: str
    investment_score_id: str
    validation_report_id: str
    score: float
    confidence: float
    assessment_status: InvestmentAssessmentStatus
    validation_status: str
    expected_role: str
    sector: str
    country: str
    theme: str
    volatility: float
    liquidity_score: float
    average_correlation: float
    max_drawdown: float
    reasons: tuple[str, ...]
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.investment_assessment_id.strip() or not self.investment_score_id.strip():
            raise ValueError("portfolio candidates require InvestmentScore identifiers")
        if not self.validation_report_id.strip():
            raise ValueError("portfolio candidates require validation evidence")
        _require_percentage("candidate score", self.score)
        _require_percentage("candidate confidence", self.confidence)
        _require_percentage("liquidity score", self.liquidity_score)
        for name, value in (
            ("volatility", self.volatility),
            ("average_correlation", self.average_correlation),
            ("max_drawdown", self.max_drawdown),
        ):
            _require_fraction(name, value)
        if self.assessment_status not in {
            InvestmentAssessmentStatus.COMPLETED,
            InvestmentAssessmentStatus.LOW_CONFIDENCE,
        }:
            raise ValueError("portfolio candidates require scored InvestmentAssessment")
        if not self.reasons:
            raise ValueError("portfolio candidate must be explainable")


@dataclass(frozen=True, slots=True)
class PositionProposal:
    instrument: Instrument | None
    asset_category: PortfolioAssetCategory
    proposed_weight: float
    min_weight: float
    max_weight: float
    confidence: float
    liquidity_score: float
    volatility_estimate: float
    expected_role: str
    reasons: tuple[str, ...]
    risk_flags: tuple[str, ...] = ()
    constraints_applied: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name, value in (
            ("proposed_weight", self.proposed_weight),
            ("min_weight", self.min_weight),
            ("max_weight", self.max_weight),
            ("volatility_estimate", self.volatility_estimate),
        ):
            _require_fraction(name, value)
        _require_percentage("position confidence", self.confidence)
        _require_percentage("position liquidity score", self.liquidity_score)
        if self.min_weight > self.proposed_weight or self.proposed_weight > self.max_weight:
            raise ValueError("position proposal weight is outside declared bounds")
        if self.asset_category is PortfolioAssetCategory.CASH and self.instrument is not None:
            raise ValueError("cash proposal must not carry an instrument")
        if self.asset_category is not PortfolioAssetCategory.CASH and self.instrument is None:
            raise ValueError("non-cash position proposals require an instrument")
        if not self.reasons:
            raise ValueError("position proposal must be explainable")


@dataclass(frozen=True, slots=True)
class PortfolioProposal:
    proposal_id: str
    as_of: datetime
    base_currency: str
    status: PortfolioProposalStatus
    positions: tuple[PositionProposal, ...]
    cash_weight: float
    target_volatility: float
    expected_portfolio_volatility: float
    expected_max_drawdown: float
    concentration_summary: dict[str, float]
    exposure_summary: dict[str, dict[str, float]]
    correlation_summary: dict[str, float]
    risk_assessment: RiskAssessment | None
    reasons: tuple[str, ...]
    limitations: tuple[str, ...]
    model_version: str = "portfolio-proposal-v0.7"
    metadata: dict[str, str | float | int | bool | None] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_timezone(self.as_of, "as_of")
        if not self.proposal_id.strip():
            raise ValueError("portfolio proposal requires an id")
        for name, value in (
            ("cash_weight", self.cash_weight),
            ("target_volatility", self.target_volatility),
            ("expected_portfolio_volatility", self.expected_portfolio_volatility),
            ("expected_max_drawdown", self.expected_max_drawdown),
        ):
            _require_fraction(name, value)
        if not self.positions:
            raise ValueError("portfolio proposal requires position proposals")
        total_weight = sum(position.proposed_weight for position in self.positions)
        if abs(total_weight - 1) > 1e-6:
            raise ValueError("portfolio proposal weights must sum to one")
        if not self.reasons:
            raise ValueError("portfolio proposal must be explainable")
        if self.metadata.get("artifact_type") != "research_artifact":
            raise ValueError("PortfolioProposal must be marked as a research artifact")


__all__ = [
    "PortfolioCandidate",
    "PortfolioProposal",
    "PositionProposal",
]
