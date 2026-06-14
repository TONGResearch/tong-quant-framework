from collections.abc import Mapping
from dataclasses import dataclass

from tong_quant.domain.enums import Regime
from tong_quant.market_regime.models import (
    MarketRegime,
    MarketRegimeInput,
    RegimeContribution,
)


@dataclass(frozen=True, slots=True)
class RegimeScoringConfig:
    weights: Mapping[str, float]
    bull_threshold: float = 25
    bear_threshold: float = -25
    transition_bull_threshold: float = 12
    transition_bear_threshold: float = -12
    transition_min_agreement: float = 0.60
    model_version: str = "v0.3"

    def __post_init__(self) -> None:
        if not self.weights:
            raise ValueError("regime scoring requires weights")
        if any(weight <= 0 for weight in self.weights.values()):
            raise ValueError("all regime weights must be positive")
        if self.bear_threshold >= self.bull_threshold:
            raise ValueError("bear threshold must be below bull threshold")
        if not self.bear_threshold < self.transition_bear_threshold < 0:
            raise ValueError("transition bear threshold must be between bear and zero")
        if not 0 < self.transition_bull_threshold < self.bull_threshold:
            raise ValueError("transition bull threshold must be between zero and bull")
        if not 0.5 <= self.transition_min_agreement <= 1:
            raise ValueError("transition agreement must be between 0.5 and 1")


def score_regime(
    inputs: MarketRegimeInput,
    config: RegimeScoringConfig,
) -> MarketRegime:
    input_names = {metric.name for metric in inputs.metrics}
    missing = set(config.weights).difference(input_names)
    if missing:
        raise ValueError(f"missing regime metrics: {', '.join(sorted(missing))}")

    total_weight = sum(config.weights.values())
    contributions = []
    for name, weight in config.weights.items():
        metric = inputs.metric(name)
        normalized_weight = weight / total_weight
        contribution = metric.value * normalized_weight * 100
        contributions.append(
            RegimeContribution(
                metric=name,
                value=metric.value,
                weight=normalized_weight,
                contribution=contribution,
                reason=_factor_reason(name, metric.value, contribution),
            )
        )

    score = sum(item.contribution for item in contributions)
    state = _state(score, contributions, config)
    confidence = _confidence(score, state, contributions, config)
    ordered = sorted(contributions, key=lambda item: abs(item.contribution), reverse=True)
    reasons = tuple(item.reason for item in ordered)
    return MarketRegime(
        market=inputs.market,
        state=state,
        confidence=confidence,
        reasons=reasons,
        as_of=inputs.as_of,
        score=round(score, 4),
        contributions=tuple(contributions),
        model_version=config.model_version,
        subject=inputs.subject,
        metadata={"metric_count": len(contributions)},
    )


def _state(
    score: float,
    contributions: list[RegimeContribution],
    config: RegimeScoringConfig,
) -> Regime:
    if score >= config.bull_threshold:
        return Regime.BULL
    if score <= config.bear_threshold:
        return Regime.BEAR
    values = [item.value for item in contributions]
    positive_agreement = sum(value > 0 for value in values) / len(values)
    negative_agreement = sum(value < 0 for value in values) / len(values)
    if (
        score >= config.transition_bull_threshold
        and positive_agreement >= config.transition_min_agreement
    ):
        return Regime.TRANSITION_TO_BULL
    if (
        score <= config.transition_bear_threshold
        and negative_agreement >= config.transition_min_agreement
    ):
        return Regime.TRANSITION_TO_BEAR
    return Regime.SIDEWAYS


def _confidence(
    score: float,
    state: Regime,
    contributions: list[RegimeContribution],
    config: RegimeScoringConfig,
) -> int:
    values = [item.value for item in contributions]
    if state is Regime.BULL:
        margin = (score - config.bull_threshold) / max(1, 100 - config.bull_threshold)
        agreement = sum(value > 0 for value in values) / len(values)
    elif state is Regime.BEAR:
        margin = (config.bear_threshold - score) / max(1, 100 + config.bear_threshold)
        agreement = sum(value < 0 for value in values) / len(values)
    elif state is Regime.TRANSITION_TO_BULL:
        width = config.bull_threshold - config.transition_bull_threshold
        margin = (score - config.transition_bull_threshold) / max(1, width)
        agreement = sum(value > 0 for value in values) / len(values)
    elif state is Regime.TRANSITION_TO_BEAR:
        width = config.transition_bear_threshold - config.bear_threshold
        margin = (config.transition_bear_threshold - score) / max(1, width)
        agreement = sum(value < 0 for value in values) / len(values)
    else:
        half_width = max(abs(config.bull_threshold), abs(config.bear_threshold))
        margin = 1 - min(abs(score) / max(1, half_width), 1)
        directional_balance = sum(
            1 if value > 0 else -1 if value < 0 else 0 for value in values
        )
        agreement = 1 - abs(directional_balance) / len(values)
    raw = 100 * (0.65 * max(0, min(margin, 1)) + 0.35 * max(0, min(agreement, 1)))
    return max(1, min(100, round(raw)))


def _factor_reason(name: str, value: float, contribution: float) -> str:
    direction = "supports bull conditions" if value > 0 else "supports bear conditions"
    if value == 0:
        direction = "is neutral"
    readable = name.replace("_", " ")
    return (
        f"{readable} {direction}: normalized value {value:.2f}, "
        f"weighted contribution {contribution:+.1f}"
    )
