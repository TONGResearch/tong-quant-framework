from datetime import UTC, datetime

import pytest

from tong_quant.domain.enums import Market, Regime, SignalAction, SignalStage
from tong_quant.market_regime.china import ChinaMarketRegimeClassifier
from tong_quant.market_regime.global_market import GlobalMarketRegimeClassifier
from tong_quant.market_regime.models import MarketRegimeInput, RegimeMetric


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.8, Regime.BULL),
        (0.15, Regime.TRANSITION_TO_BULL),
        (0.0, Regime.SIDEWAYS),
        (-0.15, Regime.TRANSITION_TO_BEAR),
        (-0.8, Regime.BEAR),
    ],
)
def test_china_classifier_returns_explainable_state(
    value: float,
    expected: Regime,
) -> None:
    as_of = datetime(2025, 1, 2, tzinfo=UTC)
    inputs = MarketRegimeInput(
        market=Market.CHINA_A,
        as_of=as_of,
        metrics=tuple(
            RegimeMetric(name, value, as_of, "test")
            for name in ChinaMarketRegimeClassifier().required_metrics
        ),
        subject="China A-share market",
    )

    regime, signal = ChinaMarketRegimeClassifier().classify(inputs)

    assert regime.state is expected
    assert 0 <= regime.confidence <= 100
    assert len(regime.reasons) == 5
    assert signal.stage is SignalStage.MARKET_REGIME
    assert signal.features["regime"] == expected.value
    if expected in {Regime.TRANSITION_TO_BULL, Regime.TRANSITION_TO_BEAR}:
        assert regime.primary_state is Regime.SIDEWAYS
        assert regime.is_transition is True
        assert signal.action is SignalAction.WATCH


def test_global_classifier_requires_global_market() -> None:
    with pytest.raises(ValueError, match="ChinaMarketRegimeClassifier"):
        GlobalMarketRegimeClassifier(
            market=Market.CHINA_A,
            subject="China",
        )


def test_global_classifier_uses_all_required_factors() -> None:
    as_of = datetime(2025, 1, 2, tzinfo=UTC)
    classifier = GlobalMarketRegimeClassifier(Market.US, "US equity market")
    inputs = MarketRegimeInput(
        market=Market.US,
        as_of=as_of,
        metrics=(
            RegimeMetric("major_index_trend", 0.7, as_of, "test"),
            RegimeMetric("market_breadth", 0.5, as_of, "test"),
            RegimeMetric("volatility", 0.4, as_of, "test"),
            RegimeMetric("relative_strength", 0.6, as_of, "test"),
        ),
        subject="US equity market",
    )

    regime, _ = classifier.classify(inputs)

    assert regime.state is Regime.BULL
    assert {item.metric for item in regime.contributions} == classifier.required_metrics
