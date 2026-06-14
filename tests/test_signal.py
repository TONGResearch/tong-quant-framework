from datetime import UTC, datetime

import pytest

from tong_quant.domain.enums import Market, SignalAction, SignalStage
from tong_quant.domain.models import Instrument, Signal


def test_universal_signal_is_explainable_and_time_aware() -> None:
    now = datetime(2026, 1, 2, tzinfo=UTC)
    signal = Signal(
        source="screening.survival",
        stage=SignalStage.SCREENING,
        instrument=Instrument("600000", Market.CHINA_A, "Example"),
        generated_at=now,
        effective_at=now,
        action=SignalAction.INCLUDE,
        strength=0.8,
        reasons=("cash flow quality passed",),
    )

    assert signal.stage is SignalStage.SCREENING


def test_signal_rejects_missing_explanation() -> None:
    now = datetime(2026, 1, 2, tzinfo=UTC)

    with pytest.raises(ValueError, match="explainable"):
        Signal(
            source="ai.news",
            stage=SignalStage.AI,
            instrument=Instrument("AAPL", Market.US, "Apple", currency="USD"),
            generated_at=now,
            effective_at=now,
            action=SignalAction.WATCH,
            strength=0.5,
            reasons=(),
        )
