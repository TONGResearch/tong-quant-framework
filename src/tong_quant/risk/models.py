from dataclasses import dataclass
from datetime import datetime

from tong_quant.domain.enums import RiskAssessmentStatus, StressScenarioType
from tong_quant.domain.models import require_timezone


def _require_fraction(name: str, value: float) -> None:
    if not 0 <= value <= 1:
        raise ValueError(f"{name} must be between zero and one")


def _require_percentage(name: str, value: float) -> None:
    if not 0 <= value <= 100:
        raise ValueError(f"{name} must be between 0 and 100")


@dataclass(frozen=True, slots=True)
class RiskBudget:
    total_risk_budget: float
    per_position_risk_budget: float
    per_sector_risk_budget: float
    per_theme_risk_budget: float

    def __post_init__(self) -> None:
        for name, value in (
            ("total_risk_budget", self.total_risk_budget),
            ("per_position_risk_budget", self.per_position_risk_budget),
            ("per_sector_risk_budget", self.per_sector_risk_budget),
            ("per_theme_risk_budget", self.per_theme_risk_budget),
        ):
            _require_fraction(name, value)


@dataclass(frozen=True, slots=True)
class RiskPositionInput:
    position_id: str
    asset_category: str
    proposed_weight: float
    confidence: float
    liquidity_score: float
    volatility_estimate: float
    sector: str = "unknown"
    country: str = "unknown"
    theme: str = "unknown"
    symbol: str | None = None
    average_correlation: float = 0.0

    def __post_init__(self) -> None:
        if not self.position_id.strip() or not self.asset_category.strip():
            raise ValueError("risk position input requires identifiers")
        for name, value in (
            ("proposed_weight", self.proposed_weight),
            ("volatility_estimate", self.volatility_estimate),
            ("average_correlation", self.average_correlation),
        ):
            _require_fraction(name, value)
        _require_percentage("risk position confidence", self.confidence)
        _require_percentage("risk position liquidity score", self.liquidity_score)
        if self.is_cash and self.symbol is not None:
            raise ValueError("cash risk input must not carry a symbol")
        if not self.is_cash and not self.symbol:
            raise ValueError("non-cash risk input requires a symbol")

    @property
    def is_cash(self) -> bool:
        return self.asset_category == "cash"


@dataclass(frozen=True, slots=True)
class ExposureBreakdown:
    dimension: str
    exposures: dict[str, float]
    max_allowed: float
    breached: bool
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_fraction("max_allowed", self.max_allowed)
        if not self.dimension.strip() or not self.exposures:
            raise ValueError("exposure breakdown requires a dimension and exposures")
        for value in self.exposures.values():
            _require_fraction("exposure weight", value)


@dataclass(frozen=True, slots=True)
class StressScenario:
    scenario_type: StressScenarioType
    name: str
    shock: float
    target: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("stress scenario requires a name")
        if not -1 <= self.shock <= 1:
            raise ValueError("stress shock must be between -100% and 100%")


@dataclass(frozen=True, slots=True)
class StressScenarioResult:
    scenario: StressScenario
    estimated_loss: float
    affected_weight: float
    breached: bool
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_fraction("affected_weight", self.affected_weight)
        if self.estimated_loss < 0:
            raise ValueError("estimated stress loss cannot be negative")
        if not self.reasons:
            raise ValueError("stress scenario result must be explainable")


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    assessment_id: str
    proposal_id: str
    assessed_at: datetime
    status: RiskAssessmentStatus
    score: float
    confidence: float
    risk_budget: RiskBudget
    concentration_risk: float
    sector_exposure: ExposureBreakdown
    country_exposure: ExposureBreakdown
    theme_exposure: ExposureBreakdown
    correlation_risk: float
    volatility_risk: float
    drawdown_risk: float
    liquidity_risk: float
    scenario_results: tuple[StressScenarioResult, ...]
    reasons: tuple[str, ...]
    required_adjustments: tuple[str, ...]
    limitations: tuple[str, ...]
    model_version: str = "risk-assessment-v0.7"

    def __post_init__(self) -> None:
        require_timezone(self.assessed_at, "assessed_at")
        if not self.assessment_id.strip() or not self.proposal_id.strip():
            raise ValueError("risk assessment requires identifiers")
        _require_percentage("risk score", self.score)
        _require_percentage("risk confidence", self.confidence)
        for name, value in (
            ("concentration_risk", self.concentration_risk),
            ("correlation_risk", self.correlation_risk),
            ("volatility_risk", self.volatility_risk),
            ("drawdown_risk", self.drawdown_risk),
            ("liquidity_risk", self.liquidity_risk),
        ):
            _require_percentage(name, value)
        if not self.scenario_results:
            raise ValueError("risk assessment requires scenario stress results")
        if not self.reasons:
            raise ValueError("risk assessment must be explainable")


__all__ = [
    "ExposureBreakdown",
    "RiskAssessment",
    "RiskBudget",
    "RiskPositionInput",
    "StressScenario",
    "StressScenarioResult",
]
