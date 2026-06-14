from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from tong_quant.domain.models import (
    Bar,
    Instrument,
    MarketSnapshot,
    RiskDecision,
    Signal,
)


class MarketDataProvider(Protocol):
    def instruments(self, as_of: datetime) -> Sequence[Instrument]: ...

    def bars(
        self,
        instrument: Instrument,
        start: datetime,
        end: datetime,
        *,
        as_of: datetime,
    ) -> Sequence[Bar]: ...


class OpportunityDiscovery(Protocol):
    source_id: str

    def discover(
        self,
        universe: Sequence[Instrument],
        snapshot: MarketSnapshot,
    ) -> Sequence[Signal]: ...


class Screener(Protocol):
    source_id: str

    def screen(
        self,
        candidates: Sequence[Instrument],
        snapshot: MarketSnapshot,
    ) -> Sequence[Signal]: ...


class SignalProducer(Protocol):
    source_id: str

    def evaluate(
        self,
        instrument: Instrument,
        bars: Sequence[Bar],
        snapshot: MarketSnapshot,
    ) -> Sequence[Signal]: ...


class RiskManager(Protocol):
    def evaluate_signals(
        self,
        signals: Sequence[Signal],
        snapshot: MarketSnapshot,
    ) -> RiskDecision: ...
