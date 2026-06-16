from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from tong_quant.domain.enums import RiskAssessmentStatus, StressScenarioType
from tong_quant.portfolio.models import PositionProposal
from tong_quant.risk.models import (
    ExposureBreakdown,
    RiskAssessment,
    RiskBudget,
    StressScenario,
    StressScenarioResult,
)


@dataclass(frozen=True, slots=True)
class RiskConstraintConfig:
    maximum_single_position_weight: float = 0.10
    maximum_sector_weight: float = 0.30
    maximum_country_weight: float = 0.60
    maximum_theme_weight: float = 0.35
    target_volatility: float = 0.15
    maximum_drawdown: float = 0.20
    minimum_liquidity_score: float = 60
    maximum_average_correlation: float = 0.70
    stress_loss_limit: float = 0.12
    model_version: str = "risk-assessment-v0.7"
    stress_scenarios: tuple[StressScenario, ...] = field(
        default_factory=lambda: (
            StressScenario(
                StressScenarioType.BROAD_MARKET,
                "broad market -10%",
                -0.10,
            ),
            StressScenario(
                StressScenarioType.SECTOR,
                "sector -20%",
                -0.20,
            ),
            StressScenario(
                StressScenarioType.CURRENCY,
                "currency -5%",
                -0.05,
            ),
            StressScenario(
                StressScenarioType.SINGLE_INSTRUMENT,
                "single stock -30%",
                -0.30,
            ),
        )
    )


@dataclass(frozen=True, slots=True)
class RiskAssessmentEngine:
    config: RiskConstraintConfig = RiskConstraintConfig()

    def assess(
        self,
        *,
        proposal_id: str,
        positions: tuple[PositionProposal, ...],
        risk_budget: RiskBudget,
        as_of: datetime | None = None,
    ) -> RiskAssessment:
        assessed_at = as_of or datetime.now(UTC)
        exposure_sector = _exposure("sector", positions, self.config.maximum_sector_weight)
        exposure_country = _exposure("country", positions, self.config.maximum_country_weight)
        exposure_theme = _exposure("theme", positions, self.config.maximum_theme_weight)
        concentration_risk = _concentration_risk(
            positions,
            self.config.maximum_single_position_weight,
        )
        weighted_volatility = sum(
            position.proposed_weight * position.volatility_estimate
            for position in positions
        )
        weighted_drawdown = max(
            (position.proposed_weight * position.volatility_estimate * 2 for position in positions),
            default=0,
        )
        average_correlation = _weighted_average_correlation(positions)
        liquidity_risk = _liquidity_risk(positions, self.config.minimum_liquidity_score)
        scenario_results = tuple(
            _stress_result(scenario, positions, self.config.stress_loss_limit)
            for scenario in self.config.stress_scenarios
        )
        risk_budget_adjustments = _risk_budget_adjustments(positions, risk_budget)
        reasons = _risk_reasons(
            concentration_risk=concentration_risk,
            weighted_volatility=weighted_volatility,
            weighted_drawdown=weighted_drawdown,
            average_correlation=average_correlation,
            liquidity_risk=liquidity_risk,
            risk_budget=risk_budget,
        )
        required_adjustments = _required_adjustments(
            sector_exposure=exposure_sector,
            country_exposure=exposure_country,
            theme_exposure=exposure_theme,
            concentration_risk=concentration_risk,
            weighted_volatility=weighted_volatility,
            volatility_limit=self.config.target_volatility,
            weighted_drawdown=weighted_drawdown,
            drawdown_limit=self.config.maximum_drawdown,
            average_correlation=average_correlation,
            correlation_limit=self.config.maximum_average_correlation,
            liquidity_risk=liquidity_risk,
            scenario_results=scenario_results,
            risk_budget_adjustments=risk_budget_adjustments,
        )
        status = RiskAssessmentStatus.ACCEPTABLE
        if required_adjustments:
            status = RiskAssessmentStatus.CONDITIONAL
        if len(required_adjustments) >= 4 or any(result.breached for result in scenario_results):
            status = RiskAssessmentStatus.REJECTED
        score = max(0.0, 100.0 - 12.5 * len(required_adjustments))
        confidence = _risk_confidence(positions)
        return RiskAssessment(
            assessment_id=str(uuid4()),
            proposal_id=proposal_id,
            assessed_at=assessed_at,
            status=status,
            score=round(score, 4),
            confidence=confidence,
            risk_budget=risk_budget,
            concentration_risk=round(concentration_risk * 100, 4),
            sector_exposure=exposure_sector,
            country_exposure=exposure_country,
            theme_exposure=exposure_theme,
            correlation_risk=round(max(0.0, average_correlation) * 100, 4),
            volatility_risk=round(weighted_volatility * 100, 4),
            drawdown_risk=round(weighted_drawdown * 100, 4),
            liquidity_risk=round(liquidity_risk * 100, 4),
            scenario_results=scenario_results,
            reasons=reasons,
            required_adjustments=required_adjustments,
            limitations=("Research artifact only; not an execution instruction",),
            model_version=self.config.model_version,
        )


def _exposure(
    dimension: str,
    positions: tuple[PositionProposal, ...],
    maximum: float,
) -> ExposureBreakdown:
    exposures: dict[str, float] = {}
    for position in positions:
        if position.asset_category.value == "cash":
            key = "cash"
        elif dimension == "sector":
            instrument = position.instrument
            key = "unknown" if instrument is None else str(instrument.industry or "unknown")
        elif dimension == "country":
            instrument = position.instrument
            key = "unknown" if instrument is None else instrument.market.value
        elif dimension == "theme":
            key = position.expected_role
        else:
            key = "unknown"
        exposures[key] = exposures.get(key, 0.0) + position.proposed_weight
    breached = any(weight > maximum for weight in exposures.values() if weight < 0.999999)
    reasons = tuple(
        f"{name} exposure {weight:.1%}"
        for name, weight in sorted(exposures.items())
    )
    return ExposureBreakdown(
        dimension=dimension,
        exposures={name: round(weight, 6) for name, weight in exposures.items()},
        max_allowed=maximum,
        breached=breached,
        reasons=reasons,
    )


def _concentration_risk(
    positions: tuple[PositionProposal, ...],
    maximum_single_position_weight: float,
) -> float:
    risky = [
        max(0.0, position.proposed_weight - maximum_single_position_weight)
        for position in positions
        if position.instrument is not None
    ]
    return max(risky, default=0.0)


def _weighted_average_correlation(positions: tuple[PositionProposal, ...]) -> float:
    values = [
        position.proposed_weight
        * float(position.risk_flags[0].split("=", 1)[1])
        for position in positions
        if position.risk_flags and position.risk_flags[0].startswith("correlation=")
    ]
    return sum(values)


def _liquidity_risk(
    positions: tuple[PositionProposal, ...],
    minimum_liquidity_score: float,
) -> float:
    risks = [
        position.proposed_weight
        * max(0.0, minimum_liquidity_score - position.liquidity_score)
        / minimum_liquidity_score
        for position in positions
        if position.instrument is not None
    ]
    return min(1.0, sum(risks))


def _stress_result(
    scenario: StressScenario,
    positions: tuple[PositionProposal, ...],
    stress_loss_limit: float,
) -> StressScenarioResult:
    affected = _affected_weight(scenario, positions)
    loss = abs(scenario.shock) * affected
    return StressScenarioResult(
        scenario=scenario,
        estimated_loss=round(loss, 6),
        affected_weight=round(affected, 6),
        breached=loss > stress_loss_limit,
        reasons=(f"{scenario.name}: estimated loss {loss:.1%}",),
    )


def _affected_weight(
    scenario: StressScenario,
    positions: tuple[PositionProposal, ...],
) -> float:
    non_cash = tuple(position for position in positions if position.instrument is not None)
    if scenario.scenario_type is StressScenarioType.BROAD_MARKET:
        return sum(position.proposed_weight for position in non_cash)
    if scenario.scenario_type is StressScenarioType.SINGLE_INSTRUMENT:
        return max((position.proposed_weight for position in non_cash), default=0.0)
    if scenario.scenario_type is StressScenarioType.CURRENCY:
        return sum(position.proposed_weight for position in non_cash)
    if scenario.scenario_type is StressScenarioType.SECTOR:
        exposures: dict[str, float] = {}
        for position in non_cash:
            instrument = position.instrument
            if instrument is None:
                continue
            sector = str(instrument.industry or "unknown")
            exposures[sector] = exposures.get(sector, 0.0) + position.proposed_weight
        return max(exposures.values(), default=0.0)
    return 0.0


def _required_adjustments(
    *,
    sector_exposure: ExposureBreakdown,
    country_exposure: ExposureBreakdown,
    theme_exposure: ExposureBreakdown,
    concentration_risk: float,
    weighted_volatility: float,
    volatility_limit: float,
    weighted_drawdown: float,
    drawdown_limit: float,
    average_correlation: float,
    correlation_limit: float,
    liquidity_risk: float,
    scenario_results: tuple[StressScenarioResult, ...],
    risk_budget_adjustments: tuple[str, ...],
) -> tuple[str, ...]:
    adjustments: list[str] = []
    if sector_exposure.breached:
        adjustments.append("sector exposure exceeds configured maximum")
    if country_exposure.breached:
        adjustments.append("country exposure exceeds configured maximum")
    if theme_exposure.breached:
        adjustments.append("theme exposure exceeds configured maximum")
    if concentration_risk > 0:
        adjustments.append("single-name concentration exceeds configured maximum")
    if weighted_volatility > volatility_limit:
        adjustments.append("portfolio volatility exceeds target volatility")
    if weighted_drawdown > drawdown_limit:
        adjustments.append("portfolio drawdown exceeds maximum drawdown")
    if average_correlation > correlation_limit:
        adjustments.append("average correlation exceeds configured maximum")
    if liquidity_risk > 0:
        adjustments.append("liquidity score below configured minimum")
    adjustments.extend(
        f"stress scenario breached: {result.scenario.name}"
        for result in scenario_results
        if result.breached
    )
    adjustments.extend(risk_budget_adjustments)
    return tuple(adjustments)


def _risk_budget_adjustments(
    positions: tuple[PositionProposal, ...],
    risk_budget: RiskBudget,
) -> tuple[str, ...]:
    non_cash = tuple(position for position in positions if position.instrument is not None)
    total_risk = sum(
        position.proposed_weight * position.volatility_estimate for position in non_cash
    )
    adjustments: list[str] = []
    if total_risk > risk_budget.total_risk_budget:
        adjustments.append("total_risk_budget exceeded")
    for position in non_cash:
        position_risk = position.proposed_weight * position.volatility_estimate
        if position_risk > risk_budget.per_position_risk_budget:
            adjustments.append(f"per_position_risk_budget exceeded: {_position_key(position)}")
    for sector, sector_risk in _risk_by_dimension(non_cash, "sector").items():
        if sector_risk > risk_budget.per_sector_risk_budget:
            adjustments.append(f"per_sector_risk_budget exceeded: {sector}")
    for theme, theme_risk in _risk_by_dimension(non_cash, "theme").items():
        if theme_risk > risk_budget.per_theme_risk_budget:
            adjustments.append(f"per_theme_risk_budget exceeded: {theme}")
    return tuple(adjustments)


def _position_key(position: PositionProposal) -> str:
    if position.instrument is None:
        return "cash"
    return position.instrument.symbol


def _risk_by_dimension(
    positions: tuple[PositionProposal, ...],
    dimension: str,
) -> dict[str, float]:
    values: dict[str, float] = {}
    for position in positions:
        if position.instrument is None:
            continue
        if dimension == "sector":
            key = str(position.instrument.industry or "unknown")
        elif dimension == "theme":
            key = position.expected_role
        else:
            key = "unknown"
        values[key] = values.get(key, 0.0) + (
            position.proposed_weight * position.volatility_estimate
        )
    return values


def _risk_reasons(
    *,
    concentration_risk: float,
    weighted_volatility: float,
    weighted_drawdown: float,
    average_correlation: float,
    liquidity_risk: float,
    risk_budget: RiskBudget,
) -> tuple[str, ...]:
    return (
        f"single-name concentration excess {concentration_risk:.1%}",
        f"estimated volatility {weighted_volatility:.1%}",
        f"estimated drawdown {weighted_drawdown:.1%}",
        f"average correlation {average_correlation:.1%}",
        f"liquidity risk {liquidity_risk:.1%}",
        f"total risk budget {risk_budget.total_risk_budget:.1%}",
    )


def _risk_confidence(positions: tuple[PositionProposal, ...]) -> float:
    total = sum(position.proposed_weight for position in positions)
    if total <= 0:
        return 0.0
    return round(
        sum(position.confidence * position.proposed_weight for position in positions) / total,
        4,
    )


__all__ = ["RiskAssessmentEngine", "RiskConstraintConfig"]
