from collections.abc import Sequence
from datetime import datetime

from tong_quant.domain.models import Bar, Instrument


class TushareProvider:
    """Future Tushare adapter boundary."""

    def instruments(self, as_of: datetime) -> Sequence[Instrument]:
        del as_of
        raise NotImplementedError("Tushare integration is not enabled")

    def bars(
        self,
        instrument: Instrument,
        start: datetime,
        end: datetime,
        *,
        as_of: datetime,
    ) -> Sequence[Bar]:
        del instrument, start, end, as_of
        raise NotImplementedError("Tushare integration is not enabled")
