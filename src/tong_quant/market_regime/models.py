from dataclasses import dataclass, field
from datetime import datetime

from tong_quant.domain.enums import Market, Regime
from tong_quant.domain.models import require_timezone


@dataclass(frozen=True, slots=True)
class RegimeMetric:
    name: str
    value: float
    available_at: datetime
    source: str
    description: str = ""

    def __post_init__(self) -> None:
        require_timezone(self.available_at, "available_at")
        if not -1 <= self.value <= 1:
            raise ValueError("regime metric value must be between -1 and 1")


@dataclass(frozen=True, slots=True)
class MarketRegimeInput:
    market: Market
    as_of: datetime
    metrics: tuple[RegimeMetric, ...]
    subject: str

    def __post_init__(self) -> None:
        require_timezone(self.as_of, "as_of")
        if not self.metrics:
            raise ValueError("market regime input requires metrics")
        future = [metric.name for metric in self.metrics if metric.available_at > self.as_of]
        if future:
            raise ValueError(f"future regime metrics are not allowed: {', '.join(future)}")

    def metric(self, name: str) -> RegimeMetric:
        matches = [metric for metric in self.metrics if metric.name == name]
        if len(matches) != 1:
            raise ValueError(f"expected exactly one metric named {name}")
        return matches[0]


@dataclass(frozen=True, slots=True)
class RegimeContribution:
    metric: str
    value: float
    weight: float
    contribution: float
    reason: str


@dataclass(frozen=True, slots=True)
class MarketRegime:
    market: Market
    state: Regime
    confidence: int
    reasons: tuple[str, ...]
    as_of: datetime
    score: float
    contributions: tuple[RegimeContribution, ...]
    model_version: str
    subject: str
    metadata: dict[str, float | int | str | bool | None] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_timezone(self.as_of, "as_of")
        if not 0 <= self.confidence <= 100:
            raise ValueError("confidence must be between 0 and 100")
        if not -100 <= self.score <= 100:
            raise ValueError("score must be between -100 and 100")
        if not self.reasons:
            raise ValueError("market regime must be explainable")
        if not self.contributions:
            raise ValueError("market regime requires factor contributions")

    @property
    def primary_state(self) -> Regime:
        if self.state in {Regime.TRANSITION_TO_BULL, Regime.TRANSITION_TO_BEAR}:
            return Regime.SIDEWAYS
        return self.state

    @property
    def is_transition(self) -> bool:
        return self.state in {Regime.TRANSITION_TO_BULL, Regime.TRANSITION_TO_BEAR}


RegimeAssessment = MarketRegime
