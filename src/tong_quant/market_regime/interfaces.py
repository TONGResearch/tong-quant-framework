from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Protocol

from tong_quant.domain.enums import Market
from tong_quant.domain.models import Bar, Signal
from tong_quant.market_regime.models import MarketRegime, MarketRegimeInput, RegimeMetric


class MarketRegimeClassifier(Protocol):
    source_id: str
    required_metrics: frozenset[str]

    def classify(self, inputs: MarketRegimeInput) -> tuple[MarketRegime, Signal]: ...


class MarketRegimeInputBuilder(Protocol):
    def build(
        self,
        *,
        market: Market,
        as_of: datetime,
        external_metrics: Mapping[str, RegimeMetric],
    ) -> MarketRegimeInput: ...


class TrendMetricCalculator(Protocol):
    def trend(self, bars: Sequence[Bar], *, name: str, as_of: datetime) -> RegimeMetric: ...
