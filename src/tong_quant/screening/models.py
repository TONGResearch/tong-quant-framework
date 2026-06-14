from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from tong_quant.domain.enums import (
    Market,
    ResearchQueueStatus,
    ScoreType,
    ScreeningDimensionName,
)
from tong_quant.domain.models import Instrument, InstrumentStatus, Signal, require_timezone
from tong_quant.market_regime.models import MarketRegime


def screening_instrument_id(instrument: Instrument) -> str:
    return f"{instrument.market.value}:{instrument.asset_type.value}:{instrument.symbol}"


def _require_score(name: str, value: float) -> None:
    if not 0 <= value <= 100:
        raise ValueError(f"{name} must be between 0 and 100")


@dataclass(frozen=True, slots=True)
class OpportunityCandidate:
    instrument: Instrument
    discovery_source: str
    discovered_at: datetime
    available_at: datetime
    thesis: str
    evidence: tuple[str, ...]
    urgency_score: float
    confidence_score: float
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_timezone(self.discovered_at, "discovered_at")
        require_timezone(self.available_at, "available_at")
        if self.available_at < self.discovered_at:
            raise ValueError("candidate available_at cannot precede discovered_at")
        if not self.thesis.strip():
            raise ValueError("candidate thesis must not be empty")
        if not self.evidence:
            raise ValueError("candidate requires discovery evidence")
        _require_score("urgency_score", self.urgency_score)
        _require_score("confidence_score", self.confidence_score)


@dataclass(frozen=True, slots=True)
class HardScreenObservation:
    candidate: OpportunityCandidate
    as_of: datetime
    available_at: datetime
    status: InstrumentStatus | None
    data_quality_passed: bool
    average_daily_turnover: Decimal | None = None
    financial_health_score: float | None = None
    risk_flags: frozenset[str] = frozenset()
    features: dict[str, float | int | str | bool | None] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_timezone(self.as_of, "as_of")
        require_timezone(self.available_at, "available_at")
        if self.available_at > self.as_of:
            raise ValueError("future hard-screen observations are not allowed")
        if self.candidate.available_at > self.as_of:
            raise ValueError("future discovery candidates are not allowed")
        if self.status is not None and self.status.available_at > self.as_of:
            raise ValueError("future instrument status is not allowed")
        if self.average_daily_turnover is not None and self.average_daily_turnover < 0:
            raise ValueError("average_daily_turnover cannot be negative")
        if self.financial_health_score is not None:
            _require_score("financial_health_score", self.financial_health_score)


@dataclass(frozen=True, slots=True)
class HardScreenResult:
    rule_id: str
    passed: bool
    evaluated_at: datetime
    available_at: datetime
    reasons: tuple[str, ...]
    features: dict[str, float | int | str | bool | None] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_timezone(self.evaluated_at, "evaluated_at")
        require_timezone(self.available_at, "available_at")
        if self.available_at > self.evaluated_at:
            raise ValueError("hard-screen result cannot use future data")
        if not self.reasons:
            raise ValueError("hard-screen result must be explainable")


@dataclass(frozen=True, slots=True)
class DimensionAssessment:
    dimension: ScreeningDimensionName
    score: float
    confidence: float
    evaluated_at: datetime
    available_at: datetime
    reasons: tuple[str, ...]
    source: str
    model_version: str
    features: dict[str, float | int | str | bool | None] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_score("dimension score", self.score)
        _require_score("dimension confidence", self.confidence)
        require_timezone(self.evaluated_at, "evaluated_at")
        require_timezone(self.available_at, "available_at")
        if self.available_at > self.evaluated_at:
            raise ValueError("dimension assessment cannot use future data")
        if not self.reasons:
            raise ValueError("dimension assessment must be explainable")


@dataclass(frozen=True, slots=True)
class ScoreComponent:
    name: str
    score: float
    confidence: float
    weight: float
    contribution: float
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_score("component score", self.score)
        _require_score("component confidence", self.confidence)
        if not 0 < self.weight <= 1:
            raise ValueError("component weight must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class CompositeScore:
    score_type: ScoreType
    score: float
    confidence: float
    calculated_at: datetime
    components: tuple[ScoreComponent, ...]
    reasons: tuple[str, ...]
    model_version: str

    def __post_init__(self) -> None:
        _require_score("composite score", self.score)
        _require_score("composite confidence", self.confidence)
        require_timezone(self.calculated_at, "calculated_at")
        if not self.components:
            raise ValueError("composite score requires components")
        if not self.reasons:
            raise ValueError("composite score must be explainable")


@dataclass(frozen=True, slots=True)
class ResearchQueueEntry:
    candidate: OpportunityCandidate
    admitted_at: datetime
    priority_score: float
    urgency_score: float
    confidence_score: float
    research_score: CompositeScore
    hard_screen_results: tuple[HardScreenResult, ...]
    status: ResearchQueueStatus = ResearchQueueStatus.PENDING
    assigned_to: str | None = None

    def __post_init__(self) -> None:
        require_timezone(self.admitted_at, "admitted_at")
        _require_score("priority_score", self.priority_score)
        _require_score("urgency_score", self.urgency_score)
        _require_score("confidence_score", self.confidence_score)
        if self.research_score.score_type is not ScoreType.RESEARCH:
            raise ValueError("research queue requires a Research Score")
        if not self.hard_screen_results or not all(
            result.passed for result in self.hard_screen_results
        ):
            raise ValueError("only candidates passing all hard screens enter the queue")


@dataclass(frozen=True, slots=True)
class ResearchOutcome:
    queue_entry: ResearchQueueEntry
    completed_at: datetime
    available_at: datetime
    thesis: str
    risks: tuple[str, ...]
    assessments: tuple[DimensionAssessment, ...]
    confidence_score: float

    def __post_init__(self) -> None:
        require_timezone(self.completed_at, "completed_at")
        require_timezone(self.available_at, "available_at")
        if self.available_at < self.completed_at:
            raise ValueError("research available_at cannot precede completed_at")
        if not self.thesis.strip():
            raise ValueError("research thesis must not be empty")
        _require_score("research confidence_score", self.confidence_score)


@dataclass(frozen=True, slots=True)
class ScreeningRequest:
    market: Market
    as_of: datetime
    observations: tuple[HardScreenObservation, ...]
    assessments: dict[str, tuple[DimensionAssessment, ...]]

    def __post_init__(self) -> None:
        require_timezone(self.as_of, "as_of")
        for observation in self.observations:
            if observation.as_of != self.as_of:
                raise ValueError("all observations must share the request as_of")
            if observation.candidate.instrument.market is not self.market:
                raise ValueError("candidate market does not match screening request")


@dataclass(frozen=True, slots=True)
class ScreeningOutcome:
    candidate: OpportunityCandidate
    accepted: bool
    hard_screen_results: tuple[HardScreenResult, ...]
    dimension_assessments: tuple[DimensionAssessment, ...]
    queue_entry: ResearchQueueEntry | None
    signal: Signal


@dataclass(frozen=True, slots=True)
class Watchlist:
    market: Market
    as_of: datetime
    candidates: tuple[OpportunityCandidate, ...]

    def __post_init__(self) -> None:
        require_timezone(self.as_of, "as_of")
        if any(candidate.instrument.market is not self.market for candidate in self.candidates):
            raise ValueError("watchlist candidates must belong to one market")


@dataclass(frozen=True, slots=True)
class ScreeningRun:
    market: Market
    as_of: datetime
    outcomes: tuple[ScreeningOutcome, ...]
    watchlist: Watchlist
    research_queue: tuple[ResearchQueueEntry, ...]

    def __post_init__(self) -> None:
        require_timezone(self.as_of, "as_of")
        if self.watchlist.market is not self.market or self.watchlist.as_of != self.as_of:
            raise ValueError("watchlist does not match screening run")


@dataclass(frozen=True, slots=True)
class InvestmentAssessment:
    research: ResearchOutcome
    investment_score: CompositeScore
    market_regime: MarketRegime | None

    def __post_init__(self) -> None:
        if self.investment_score.score_type is not ScoreType.INVESTMENT:
            raise ValueError("investment assessment requires an Investment Score")
