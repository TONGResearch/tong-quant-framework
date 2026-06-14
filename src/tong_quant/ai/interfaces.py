from collections.abc import Sequence
from typing import Protocol

from tong_quant.domain.models import Event, Instrument, Signal


class AIAnalyzer(Protocol):
    source_id: str

    def analyze(
        self,
        instrument: Instrument,
        evidence: Sequence[Event],
    ) -> Sequence[Signal]: ...
