from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from tong_quant.domain.enums import ScoreType, ScreeningDimensionName
from tong_quant.market_regime.models import MarketRegime
from tong_quant.screening.models import CompositeScore, DimensionAssessment, ScoreComponent


@dataclass(frozen=True, slots=True)
class ScoreConfig:
    score_type: ScoreType
    weights: Mapping[str, float]
    model_version: str
    maximum_component_weight: float = 0.35
    require_all_components: bool = True

    def __post_init__(self) -> None:
        if not self.weights:
            raise ValueError("score configuration requires weights")
        if any(weight <= 0 for weight in self.weights.values()):
            raise ValueError("score weights must be positive")
        normalized = _normalized_weights(self.weights)
        if max(normalized.values()) > self.maximum_component_weight:
            raise ValueError("no single score component may exceed the configured maximum")


def default_research_score_config() -> ScoreConfig:
    return ScoreConfig(
        score_type=ScoreType.RESEARCH,
        weights={
            ScreeningDimensionName.NEWS.value: 0.15,
            ScreeningDimensionName.INDUSTRY.value: 0.20,
            ScreeningDimensionName.SURVIVAL.value: 0.15,
            ScreeningDimensionName.GROWTH.value: 0.15,
            ScreeningDimensionName.VALUATION.value: 0.10,
            ScreeningDimensionName.POSITIONING.value: 0.10,
            ScreeningDimensionName.MACRO.value: 0.15,
        },
        model_version="research-score-v0.4",
    )


def default_investment_score_config() -> ScoreConfig:
    return ScoreConfig(
        score_type=ScoreType.INVESTMENT,
        weights={
            ScreeningDimensionName.NEWS.value: 0.08,
            ScreeningDimensionName.INDUSTRY.value: 0.12,
            ScreeningDimensionName.SURVIVAL.value: 0.15,
            ScreeningDimensionName.GROWTH.value: 0.13,
            ScreeningDimensionName.VALUATION.value: 0.12,
            ScreeningDimensionName.POSITIONING.value: 0.08,
            ScreeningDimensionName.MACRO.value: 0.07,
            "market_regime": 0.25,
        },
        model_version="investment-score-v0.4",
    )


@dataclass(frozen=True, slots=True)
class WeightedScoreAggregator:
    config: ScoreConfig

    @property
    def score_type(self) -> ScoreType:
        return self.config.score_type

    def aggregate(
        self,
        assessments: tuple[DimensionAssessment, ...],
        *,
        calculated_at: datetime,
        regime: MarketRegime | None = None,
    ) -> CompositeScore:
        by_name = {assessment.dimension.value: assessment for assessment in assessments}
        if len(by_name) != len(assessments):
            raise ValueError("duplicate screening dimensions are not allowed")
        required = set(self.config.weights)
        if "market_regime" in required:
            if regime is None:
                raise ValueError("Investment Score requires a Market Regime assessment")
            required.remove("market_regime")
        missing = required.difference(by_name)
        if missing and self.config.require_all_components:
            raise ValueError(f"missing score components: {', '.join(sorted(missing))}")
        future = [
            assessment.dimension.value
            for assessment in assessments
            if assessment.available_at > calculated_at
        ]
        if future:
            raise ValueError(f"future score components are not allowed: {', '.join(future)}")
        if regime is not None and regime.as_of > calculated_at:
            raise ValueError("future Market Regime assessment is not allowed")

        inputs: dict[str, tuple[float, float, tuple[str, ...]]] = {
            name: (assessment.score, assessment.confidence, assessment.reasons)
            for name, assessment in by_name.items()
            if name in self.config.weights
        }
        if "market_regime" in self.config.weights and regime is not None:
            inputs["market_regime"] = (
                (regime.score + 100) / 2,
                float(regime.confidence),
                regime.reasons,
            )
        if not inputs:
            raise ValueError("no configured score components were supplied")

        configured_weights = {
            name: self.config.weights[name]
            for name in inputs
        }
        weights = _normalized_weights(configured_weights)
        components = tuple(
            ScoreComponent(
                name=name,
                score=values[0],
                confidence=values[1],
                weight=weights[name],
                contribution=values[0] * weights[name],
                reasons=values[2],
            )
            for name, values in inputs.items()
        )
        score = sum(component.contribution for component in components)
        confidence = sum(
            component.confidence * component.weight for component in components
        )
        ordered = sorted(
            components,
            key=lambda component: abs(component.contribution),
            reverse=True,
        )
        reasons = tuple(
            f"{component.name}: score {component.score:.1f}, "
            f"weight {component.weight:.1%}, contribution {component.contribution:.1f}"
            for component in ordered
        )
        return CompositeScore(
            score_type=self.config.score_type,
            score=round(score, 4),
            confidence=round(confidence, 4),
            calculated_at=calculated_at,
            components=components,
            reasons=reasons,
            model_version=self.config.model_version,
        )


def _normalized_weights(weights: Mapping[str, float]) -> dict[str, float]:
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("score weights must have a positive total")
    return {name: weight / total for name, weight in weights.items()}
