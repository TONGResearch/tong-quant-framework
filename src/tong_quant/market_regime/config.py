from tong_quant.config.settings import RegimeModelSettings
from tong_quant.market_regime.scoring import RegimeScoringConfig


def scoring_config(settings: RegimeModelSettings) -> RegimeScoringConfig:
    return RegimeScoringConfig(
        weights=settings.weights,
        bull_threshold=settings.bull_threshold,
        bear_threshold=settings.bear_threshold,
        transition_bull_threshold=settings.transition_bull_threshold,
        transition_bear_threshold=settings.transition_bear_threshold,
        transition_min_agreement=settings.transition_min_agreement,
        model_version=settings.model_version,
    )
