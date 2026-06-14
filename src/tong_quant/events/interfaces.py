from collections.abc import Sequence
from typing import Protocol

from tong_quant.domain.models import Event, Signal


class EventAnalyzer(Protocol):
    source_id: str

    def evaluate(self, event: Event) -> Sequence[Signal]: ...
