from collections.abc import Sequence
from typing import Protocol

from tong_quant.domain.models import Instrument, MarketSnapshot, Signal


class ScreeningDimension(Protocol):
    source_id: str

    def evaluate(
        self,
        instruments: Sequence[Instrument],
        snapshot: MarketSnapshot,
    ) -> Sequence[Signal]: ...
