from collections.abc import Iterable
from datetime import datetime
from typing import Protocol


class AvailableRecord(Protocol):
    available_at: datetime


def visible_as_of[T: AvailableRecord](records: Iterable[T], as_of: datetime) -> list[T]:
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of must be timezone-aware")
    return [record for record in records if record.available_at <= as_of]
