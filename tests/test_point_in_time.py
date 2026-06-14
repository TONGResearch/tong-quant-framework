from dataclasses import dataclass
from datetime import UTC, datetime

from tong_quant.data.point_in_time import visible_as_of


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
