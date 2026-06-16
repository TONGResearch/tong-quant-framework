from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Protocol

from tong_quant.domain.enums import (
    InvestmentAssessmentStatus,
    ResearchConclusion,
    ResearchModuleName,
    ResearchRunStatus,
)
from tong_quant.market_regime.models import MarketRegime
from tong_quant.research.models import (
    InvestmentAssessment,
    InvestmentScore,
    InvestmentScoreComponent,
    ResearchAssessment,
    ResearchReport,
)


@dataclass(frozen=True, slots=True)
class InvestmentScoreConfig:
    weights: Mapping[str, float]
    model_version: str
    maximum_component_weight: float = 0.35
    require_all_components: bool = False
    minimum_confidence: float = 60
    minimum_scored_components: int = 2

    def __post_init__(self) -> None:
        if not self.weights:
            raise ValueError("investment score configuration requires weights")
        if any(weight <= 0 for weight in self.weights.values()):
            raise ValueError("investment score weights must be positive")
        if not 0 < self.maximum_component_weight < 1:
            raise ValueError("maximum_component_weight must be between zero and one")
        if not 0 <= self.minimum_confidence <= 100:
            raise ValueError("minimum_confidence must be between 0 and 100")
        if self.minimum_scored_components <= 0:
            raise ValueError("minimum_scored_components must be positive")


def default_investment_score_config() -> InvestmentScoreConfig:
    return InvestmentScoreConfig(
        weights={
            ResearchModuleName.POLICY.value: 0.08,
            ResearchModuleName.FINANCIAL.value: 0.12,
            ResearchModuleName.INDUSTRY.value: 0.12,
            ResearchModuleName.VALUE.value: 0.15,
            ResearchModuleName.TECHNICAL.value: 0.10,
            ResearchModuleName.TREND.value: 0.10,
            ResearchModuleName.PATTERN.value: 0.08,
            "market_regime": 0.25,
        },
        model_version="investment-score-v0.6.1",
        require_all_components=False,
    )


class InvestmentAssessmentRepository(Protocol):
    def save_assessment(self, assessment: InvestmentAssessment) -> str: ...


@dataclass(frozen=True, slots=True)
class InvestmentAssessmentBuilder:
    config: InvestmentScoreConfig = field(default_factory=default_investment_score_config)

    def build(
        self,
        report: ResearchReport,
        *,
        assessed_at: datetime,
        market_regime: MarketRegime | None = None,
    ) -> InvestmentAssessment:
        regime = market_regime if market_regime is not None else report.market_regime
        if report.status is not ResearchRunStatus.COMPLETED:
            return InvestmentAssessment(
                report=report,
                status=InvestmentAssessmentStatus.INCOMPLETE,
                assessed_at=assessed_at,
                investment_score=None,
                market_regime=regime,
                reasons=("ResearchReport is not completed",),
                limitations=("Investment Score requires a completed ResearchReport",),
                model_version=self.config.model_version,
            )
        if report.available_at > assessed_at:
            raise ValueError("investment assessment cannot use a future ResearchReport")
        if regime is not None and regime.as_of > assessed_at:
            raise ValueError("investment assessment cannot use a future Market Regime")

        inputs, limitations = self._score_inputs(report.assessments, regime)
        configured_names = set(self.config.weights)
        missing = configured_names.difference(inputs).difference(_not_applicable_names(report))
        if self.config.require_all_components and missing:
            return InvestmentAssessment(
                report=report,
                status=InvestmentAssessmentStatus.INSUFFICIENT_DATA,
                assessed_at=assessed_at,
                investment_score=None,
                market_regime=regime,
                reasons=("Required investment score components are missing",),
                limitations=tuple(
                    sorted((*limitations, f"missing components: {', '.join(sorted(missing))}"))
                ),
                model_version=self.config.model_version,
            )
        if len(inputs) < self.config.minimum_scored_components:
            return InvestmentAssessment(
                report=report,
                status=InvestmentAssessmentStatus.INSUFFICIENT_DATA,
                assessed_at=assessed_at,
                investment_score=None,
                market_regime=regime,
                reasons=("Too few scored research components are available",),
                limitations=tuple(
                    sorted(
                        (
                            *limitations,
                            "Investment Score needs at least two scored components",
                        )
                    )
                ),
                model_version=self.config.model_version,
            )

        configured_weights = {
            name: self.config.weights[name]
            for name in inputs
        }
        weights = _normalized_weights(configured_weights)
        components = tuple(
            InvestmentScoreComponent(
                name=name,
                score=values[0],
                confidence=values[1],
                weight=weights[name],
                contribution=values[0] * weights[name],
                reasons=values[2],
            )
            for name, values in inputs.items()
        )
        score = round(sum(component.contribution for component in components), 4)
        confidence = round(
            sum(component.confidence * component.weight for component in components),
            4,
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
        score_model = InvestmentScore(
            score=score,
            confidence=confidence,
            calculated_at=assessed_at,
            components=components,
            reasons=reasons,
            model_version=self.config.model_version,
        )
        status = InvestmentAssessmentStatus.COMPLETED
        if (
            confidence < self.config.minimum_confidence
            or report.confidence.confidence < self.config.minimum_confidence
        ):
            status = InvestmentAssessmentStatus.LOW_CONFIDENCE
            limitations = (
                *limitations,
                "Investment Score confidence is below the configured threshold",
            )
        if max(component.weight for component in components) > self.config.maximum_component_weight:
            status = InvestmentAssessmentStatus.LOW_CONFIDENCE
            limitations = (
                *limitations,
                "At least one component exceeds the maximum normalized weight",
            )
        return InvestmentAssessment(
            report=report,
            status=status,
            assessed_at=assessed_at,
            investment_score=score_model,
            market_regime=regime,
            reasons=reasons,
            limitations=tuple(dict.fromkeys(limitations)),
            model_version=self.config.model_version,
        )

    def _score_inputs(
        self,
        assessments: tuple[ResearchAssessment, ...],
        regime: MarketRegime | None,
    ) -> tuple[dict[str, tuple[float, float, tuple[str, ...]]], tuple[str, ...]]:
        inputs: dict[str, tuple[float, float, tuple[str, ...]]] = {}
        limitations: list[str] = []
        by_module = {assessment.module.value: assessment for assessment in assessments}
        if len(by_module) != len(assessments):
            raise ValueError("duplicate research module assessments are not allowed")
        for name in self.config.weights:
            if name == "market_regime":
                continue
            assessment = by_module.get(name)
            if assessment is None:
                limitations.append(f"{name} assessment is missing")
                continue
            if assessment.conclusion is ResearchConclusion.NOT_APPLICABLE:
                limitations.append(f"{name} assessment is not applicable")
                continue
            if assessment.score is None:
                limitations.append(f"{name} assessment has insufficient data")
                continue
            inputs[name] = (
                assessment.score,
                assessment.confidence.confidence,
                assessment.findings,
            )
        if "market_regime" in self.config.weights:
            if regime is None:
                limitations.append("Market Regime assessment is missing")
            else:
                inputs["market_regime"] = (
                    (regime.score + 100) / 2,
                    float(regime.confidence),
                    regime.reasons,
                )
        return inputs, tuple(limitations)


def _not_applicable_names(report: ResearchReport) -> set[str]:
    return {
        assessment.module.value
        for assessment in report.assessments
        if assessment.conclusion is ResearchConclusion.NOT_APPLICABLE
    }


def _normalized_weights(weights: Mapping[str, float]) -> dict[str, float]:
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("investment score weights must have a positive total")
    return {name: weight / total for name, weight in weights.items()}


def investment_assessment_to_record(
    assessment: InvestmentAssessment,
) -> dict[str, object]:
    score = assessment.investment_score
    return {
        "report_id": assessment.report.report_id,
        "instrument_id": assessment.report.instrument_id,
        "status": assessment.status.value,
        "assessed_at": assessment.assessed_at,
        "score": None if score is None else score.score,
        "confidence": None if score is None else score.confidence,
        "components": (
            []
            if score is None
            else [asdict(component) for component in score.components]
        ),
        "reasons": assessment.reasons,
        "limitations": assessment.limitations,
        "market_regime": (
            None
            if assessment.market_regime is None
            else asdict(assessment.market_regime)
        ),
        "model_version": assessment.model_version,
    }


__all__ = [
    "InvestmentAssessmentBuilder",
    "InvestmentAssessmentRepository",
    "InvestmentScoreConfig",
    "default_investment_score_config",
    "investment_assessment_to_record",
]
