from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from tong_quant.domain.enums import (
    InvestmentAssessmentStatus,
    PortfolioAssetCategory,
    PortfolioProposalStatus,
    ValidationStatus,
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
    research_report_id: str
    investment_assessment_id: str
    investment_score_id: str
    validation_report_id: str
    score: float
    confidence: float
    assessment_status: InvestmentAssessmentStatus
    validation_status: ValidationStatus
    validation_generated_at: datetime
    validation_configuration_hash: str
    validation_model_version: str
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
        if not isinstance(self.assessment_status, InvestmentAssessmentStatus):
            raise ValueError("portfolio candidate assessment status must be typed")
        if not isinstance(self.validation_status, ValidationStatus):
            raise ValueError("portfolio candidate validation status must be typed")
        if not self.research_report_id.strip():
            raise ValueError("portfolio candidates require a ResearchReport identifier")
        if not self.investment_assessment_id.strip() or not self.investment_score_id.strip():
            raise ValueError("portfolio candidates require InvestmentScore identifiers")
        if not self.validation_report_id.strip():
            raise ValueError("portfolio candidates require validation evidence")
        require_timezone(self.validation_generated_at, "validation_generated_at")
        if len(self.validation_configuration_hash) != 64:
            raise ValueError("portfolio candidates require a validation configuration hash")
        if not self.validation_model_version.strip():
            raise ValueError("portfolio candidates require a validation model version")
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
        if self.validation_status not in {
            ValidationStatus.RELIABLE,
            ValidationStatus.CONDITIONALLY_RELIABLE,
        }:
            raise ValueError(
                "portfolio candidates require reliable or conditionally reliable validation"
            )
        if not self.reasons:
            raise ValueError("portfolio candidate must be explainable")


@dataclass(frozen=True, slots=True)
class PortfolioEvidenceReference:
    instrument: Instrument
    research_report_id: str
    investment_assessment_id: str
    investment_assessment_status: InvestmentAssessmentStatus
    investment_score_id: str
    investment_score: float
    investment_confidence: float
    validation_report_id: str
    validation_status: ValidationStatus
    validation_generated_at: datetime
    validation_configuration_hash: str
    validation_model_version: str

    def __post_init__(self) -> None:
        if not isinstance(self.investment_assessment_status, InvestmentAssessmentStatus):
            raise ValueError("portfolio evidence assessment status must be typed")
        if not isinstance(self.validation_status, ValidationStatus):
            raise ValueError("portfolio evidence validation status must be typed")
        identifiers = (
            self.research_report_id,
            self.investment_assessment_id,
            self.investment_score_id,
            self.validation_report_id,
        )
        if any(not identifier.strip() for identifier in identifiers):
            raise ValueError("portfolio evidence references require complete lineage")
        if self.investment_assessment_status not in {
            InvestmentAssessmentStatus.COMPLETED,
            InvestmentAssessmentStatus.LOW_CONFIDENCE,
        }:
            raise ValueError("portfolio evidence requires a scored assessment")
        _require_percentage("investment score", self.investment_score)
        _require_percentage("investment confidence", self.investment_confidence)
        require_timezone(self.validation_generated_at, "validation_generated_at")
        if len(self.validation_configuration_hash) != 64:
            raise ValueError("portfolio evidence requires a configuration hash")
        if not self.validation_model_version.strip():
            raise ValueError("portfolio evidence requires a validation model version")
        if self.validation_status not in {
            ValidationStatus.RELIABLE,
            ValidationStatus.CONDITIONALLY_RELIABLE,
        }:
            raise ValueError("portfolio evidence cannot carry rejected validation")


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
    evidence_references: tuple[PortfolioEvidenceReference, ...]
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
        cash_positions = tuple(
            position
            for position in self.positions
            if position.asset_category is PortfolioAssetCategory.CASH
        )
        if len(cash_positions) != 1 or abs(
            cash_positions[0].proposed_weight - self.cash_weight
        ) > 1e-6:
            raise ValueError("portfolio proposal requires one matching cash position")
        total_weight = sum(position.proposed_weight for position in self.positions)
        if abs(total_weight - 1) > 1e-6:
            raise ValueError("portfolio proposal weights must sum to one")
        if not self.reasons:
            raise ValueError("portfolio proposal must be explainable")
        if self.metadata.get("artifact_type") != "research_artifact":
            raise ValueError("PortfolioProposal must be marked as a research artifact")
        proposed_instruments = {
            _instrument_key(position.instrument)
            for position in self.positions
            if position.instrument is not None
        }
        evidence_instruments = {
            _instrument_key(reference.instrument)
            for reference in self.evidence_references
        }
        if len(proposed_instruments) != len(self.positions) - 1:
            raise ValueError("portfolio positions must be unique by instrument")
        if len(evidence_instruments) != len(self.evidence_references):
            raise ValueError("portfolio evidence references must be unique by instrument")
        if evidence_instruments != proposed_instruments:
            raise ValueError(
                "every non-cash position requires exactly one evidence reference"
            )
        if any(
            reference.validation_generated_at > self.as_of
            for reference in self.evidence_references
        ):
            raise ValueError("portfolio evidence cannot be newer than the proposal")
        if (
            self.status is PortfolioProposalStatus.PROPOSED
            and any(
                reference.validation_status is not ValidationStatus.RELIABLE
                or reference.investment_assessment_status
                is InvestmentAssessmentStatus.LOW_CONFIDENCE
                for reference in self.evidence_references
            )
        ):
            raise ValueError("conditional evidence cannot produce a proposed portfolio")
        if self.risk_assessment is None:
            raise ValueError("portfolio proposal requires a RiskAssessment")
        if self.risk_assessment.proposal_id != self.proposal_id:
            raise ValueError("portfolio risk assessment belongs to a different proposal")
        if self.risk_assessment.assessed_at > self.as_of:
            raise ValueError("portfolio risk assessment is from the future")
        if (
            self.status is PortfolioProposalStatus.PROPOSED
            and self.risk_assessment.status.value != "acceptable"
        ):
            raise ValueError("proposed portfolio requires acceptable risk")
        if (
            self.risk_assessment.status.value == "rejected"
            and self.status is not PortfolioProposalStatus.REJECTED
        ):
            raise ValueError("rejected risk requires a rejected portfolio")


def _instrument_key(instrument: Instrument) -> tuple[str, str, str]:
    return instrument.market.value, instrument.asset_type.value, instrument.symbol


__all__ = [
    "PortfolioCandidate",
    "PortfolioEvidenceReference",
    "PortfolioProposal",
    "PositionProposal",
]
