from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from tong_quant.domain.models import Instrument, Signal


class ValidationEngine(Protocol):
    def validate(
        self,
        signals: Sequence[Signal],
        instruments: Sequence[Instrument],
        start: datetime,
        end: datetime,
    ) -> object: ...
