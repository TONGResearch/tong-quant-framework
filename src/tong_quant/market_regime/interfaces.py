from typing import Protocol

from tong_quant.domain.models import MarketSnapshot, Signal
from tong_quant.market_regime.models import RegimeAssessment


class MarketRegimeClassifier(Protocol):
    source_id: str

    def classify(self, snapshot: MarketSnapshot) -> tuple[RegimeAssessment, Signal]: ...
