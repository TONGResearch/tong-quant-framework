from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from tong_quant.domain.enums import (
    Adjustment,
    AssetType,
    Market,
    Regime,
    SecurityStatus,
    SignalAction,
    SignalStage,
)

ALLOWED_SIGNAL_ACTIONS = {
    SignalStage.DISCOVERY: {
        SignalAction.INCLUDE,
        SignalAction.WATCH,
        SignalAction.RESEARCH,
    },
    SignalStage.SCREENING: {
        SignalAction.INCLUDE,
        SignalAction.EXCLUDE,
        SignalAction.WATCH,
        SignalAction.RESEARCH,
    },
    SignalStage.RESEARCH: {
        SignalAction.WATCH,
        SignalAction.RESEARCH,
    },
    SignalStage.STRATEGY: {
        SignalAction.WATCH,
        SignalAction.ENTER_LONG,
        SignalAction.EXIT_LONG,
        SignalAction.HOLD,
    },
    SignalStage.MARKET_REGIME: {SignalAction.WATCH},
    SignalStage.RISK: {SignalAction.HOLD, SignalAction.BLOCK},
    SignalStage.AI: {SignalAction.WATCH, SignalAction.RESEARCH},
    SignalStage.VALIDATION: {SignalAction.REVIEW},
}


def require_timezone(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class Instrument:
    symbol: str
    market: Market
    name: str
    asset_type: AssetType = AssetType.EQUITY
    currency: str = "CNY"
    lot_size: int = 1
    exchange: str | None = None
    industry: str | None = None
    listing_date: date | None = None
    delisting_date: date | None = None
    available_at: datetime | None = None
    source: str = ""

    def __post_init__(self) -> None:
        if self.lot_size <= 0:
            raise ValueError("lot_size must be positive")
        if self.available_at is not None:
            require_timezone(self.available_at, "available_at")


@dataclass(frozen=True, slots=True)
class Bar:
    instrument: Instrument
    timestamp: datetime
    available_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    turnover: Decimal | None = None
    adjustment: Adjustment = Adjustment.NONE
    is_suspended: bool = False
    source: str = ""
    ingested_at: datetime | None = None

    def __post_init__(self) -> None:
        require_timezone(self.timestamp, "timestamp")
        require_timezone(self.available_at, "available_at")
        if self.available_at < self.timestamp:
            raise ValueError("available_at cannot precede the observation timestamp")
        if not self.low <= min(self.open, self.close) <= max(self.open, self.close) <= self.high:
            raise ValueError("OHLC prices are inconsistent")
        if self.volume < 0:
            raise ValueError("volume cannot be negative")
        if self.turnover is not None and self.turnover < 0:
            raise ValueError("turnover cannot be negative")
        if self.ingested_at is not None:
            require_timezone(self.ingested_at, "ingested_at")


@dataclass(frozen=True, slots=True)
class TradingSession:
    market: Market
    trade_date: date
    is_open: bool
    available_at: datetime
    source: str

    def __post_init__(self) -> None:
        require_timezone(self.available_at, "available_at")


@dataclass(frozen=True, slots=True)
class FundamentalFact:
    instrument: Instrument
    metric: str
    period_end: date
    published_at: datetime
    available_at: datetime
    value: Decimal
    source: str
    period_start: date | None = None
    fiscal_period: str | None = None
    currency: str | None = None
    unit: str = "absolute"
    revision: int = 0

    def __post_init__(self) -> None:
        require_timezone(self.published_at, "published_at")
        require_timezone(self.available_at, "available_at")
        if self.available_at < self.published_at:
            raise ValueError("available_at cannot precede published_at")
        if self.period_start is not None and self.period_start > self.period_end:
            raise ValueError("period_start cannot follow period_end")
        if self.revision < 0:
            raise ValueError("revision cannot be negative")


@dataclass(frozen=True, slots=True)
class InstrumentStatus:
    instrument: Instrument
    effective_from: date
    status: SecurityStatus
    is_tradable: bool
    available_at: datetime
    source: str
    effective_to: date | None = None
    industry: str | None = None

    def __post_init__(self) -> None:
        require_timezone(self.available_at, "available_at")
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to cannot precede effective_from")
        if (
            self.status in {SecurityStatus.SUSPENDED, SecurityStatus.DELISTED}
            and self.is_tradable
        ):
            raise ValueError(f"{self.status.value} securities cannot be tradable")


@dataclass(frozen=True, slots=True)
class UniverseMembership:
    universe: str
    instrument: Instrument
    effective_from: date
    available_at: datetime
    source: str
    effective_to: date | None = None

    def __post_init__(self) -> None:
        require_timezone(self.available_at, "available_at")
        if not self.universe.strip():
            raise ValueError("universe must not be empty")
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to cannot precede effective_from")


@dataclass(frozen=True, slots=True)
class Event:
    instrument: Instrument | None
    event_type: str
    occurred_at: datetime
    published_at: datetime
    headline: str
    source: str
    attributes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_timezone(self.occurred_at, "occurred_at")
        require_timezone(self.published_at, "published_at")


@dataclass(frozen=True, slots=True)
class MarketSnapshot:
    as_of: datetime
    market: Market
    regime: Regime
    sentiment_score: float | None = None
    advancing_stocks: int | None = None

    def __post_init__(self) -> None:
        require_timezone(self.as_of, "as_of")


@dataclass(frozen=True, slots=True)
class Signal:
    source: str
    stage: SignalStage
    instrument: Instrument
    generated_at: datetime
    effective_at: datetime
    action: SignalAction
    strength: float
    reasons: tuple[str, ...]
    features: dict[str, float | int | str | bool | None] = field(default_factory=dict)
    invalidations: tuple[str, ...] = ()
    model_version: str = "v0"

    def __post_init__(self) -> None:
        require_timezone(self.generated_at, "generated_at")
        require_timezone(self.effective_at, "effective_at")
        if self.effective_at < self.generated_at:
            raise ValueError("effective_at cannot precede generated_at")
        if not 0 <= self.strength <= 1:
            raise ValueError("strength must be between 0 and 1")
        if not self.reasons:
            raise ValueError("every signal must be explainable")
        if self.action not in ALLOWED_SIGNAL_ACTIONS[self.stage]:
            raise ValueError(
                f"{self.stage.value} signals cannot use action {self.action.value}"
            )


@dataclass(frozen=True, slots=True)
class RiskDecision:
    approved: bool
    checked_at: datetime
    reasons: tuple[str, ...]
    adjusted_quantity: int | None = None

    def __post_init__(self) -> None:
        require_timezone(self.checked_at, "checked_at")
