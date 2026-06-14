from datetime import UTC, datetime
from decimal import Decimal

import pytest

from tong_quant.domain.enums import Market
from tong_quant.domain.models import Bar, Instrument


def test_bar_rejects_naive_timestamp() -> None:
    instrument = Instrument(symbol="600000", market=Market.CHINA_A, name="Example")

    with pytest.raises(ValueError, match="timezone-aware"):
        Bar(
            instrument=instrument,
            timestamp=datetime(2026, 1, 2),
            available_at=datetime(2026, 1, 2, tzinfo=UTC),
            open=Decimal("10"),
            high=Decimal("11"),
            low=Decimal("9"),
            close=Decimal("10.5"),
            volume=Decimal("1000"),
        )


def test_bar_rejects_availability_before_observation() -> None:
    instrument = Instrument(symbol="600000", market=Market.CHINA_A, name="Example")

    with pytest.raises(ValueError, match="cannot precede"):
        Bar(
            instrument=instrument,
            timestamp=datetime(2026, 1, 3, tzinfo=UTC),
            available_at=datetime(2026, 1, 2, tzinfo=UTC),
            open=Decimal("10"),
            high=Decimal("11"),
            low=Decimal("9"),
            close=Decimal("10.5"),
            volume=Decimal("1000"),
        )
