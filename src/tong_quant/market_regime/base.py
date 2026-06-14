from dataclasses import dataclass

from tong_quant.domain.enums import SignalAction, SignalStage
from tong_quant.domain.models import Instrument, Signal
from tong_quant.market_regime.models import MarketRegime, MarketRegimeInput
from tong_quant.market_regime.scoring import RegimeScoringConfig, score_regime


@dataclass(frozen=True, slots=True)
class WeightedMarketRegimeClassifier:
    source_id: str
    required_metrics: frozenset[str]
    config: RegimeScoringConfig
    signal_instrument: Instrument

    def classify(self, inputs: MarketRegimeInput) -> tuple[MarketRegime, Signal]:
        if inputs.market is not self.signal_instrument.market:
            raise ValueError("regime input market does not match classifier instrument")
        missing = self.required_metrics.difference(metric.name for metric in inputs.metrics)
        if missing:
            raise ValueError(f"missing required metrics: {', '.join(sorted(missing))}")
        regime = score_regime(inputs, self.config)
        signal = Signal(
            source=self.source_id,
            stage=SignalStage.MARKET_REGIME,
            instrument=self.signal_instrument,
            generated_at=inputs.as_of,
            effective_at=inputs.as_of,
            action=SignalAction.WATCH,
            strength=regime.confidence / 100,
            reasons=regime.reasons,
            features={
                "regime": regime.state.value,
                "primary_regime": regime.primary_state.value,
                "is_transition": regime.is_transition,
                "regime_score": regime.score,
                "confidence": regime.confidence,
            },
            model_version=regime.model_version,
        )
        return regime, signal
