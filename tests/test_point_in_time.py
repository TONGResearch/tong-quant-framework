from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from tong_quant.data.point_in_time import visible_as_of
from tong_quant.domain.enums import Market, SecurityStatus
from tong_quant.domain.models import FundamentalFact, Instrument, InstrumentStatus


@dataclass(frozen=True)
class Record:
    available_at: datetime
    value: int


def test_future_records_are_hidden() -> None:
    records = [
        Record(datetime(2026, 1, 1, tzinfo=UTC), 1),
        Record(datetime(2026, 1, 3, tzinfo=UTC), 2),
    ]

    visible = visible_as_of(records, datetime(2026, 1, 2, tzinfo=UTC))

    assert [record.value for record in visible] == [1]


def test_fundamental_availability_cannot_precede_publication() -> None:
    instrument = Instrument("600000", Market.CHINA_A, "Example")

    try:
        FundamentalFact(
            instrument=instrument,
            metric="profit",
            period_end=date(2025, 12, 31),
            published_at=datetime(2026, 3, 31, tzinfo=UTC),
            available_at=datetime(2026, 3, 30, tzinfo=UTC),
            value=Decimal("1"),
            source="test",
        )
    except ValueError as error:
        assert "cannot precede published_at" in str(error)
    else:
        raise AssertionError("future-leaking fundamental fact should fail")


def test_non_tradable_status_is_enforced() -> None:
    instrument = Instrument("600000", Market.CHINA_A, "Example")

    try:
        InstrumentStatus(
            instrument=instrument,
            effective_from=date(2026, 1, 1),
            status=SecurityStatus.DELISTED,
            is_tradable=True,
            available_at=datetime(2026, 1, 1, tzinfo=UTC),
            source="test",
        )
    except ValueError as error:
        assert "cannot be tradable" in str(error)
    else:
        raise AssertionError("delisted security should not be tradable")
