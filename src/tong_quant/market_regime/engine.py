from dataclasses import dataclass

from tong_quant.domain.models import Signal
from tong_quant.market_regime.interfaces import MarketRegimeClassifier
from tong_quant.market_regime.models import MarketRegime, MarketRegimeInput


@dataclass(frozen=True, slots=True)
class MarketRegimeEngine:
    """Pure orchestration boundary suitable for historical replay and live research."""

    classifier: MarketRegimeClassifier

    def evaluate(self, inputs: MarketRegimeInput) -> tuple[MarketRegime, Signal]:
        return self.classifier.classify(inputs)
