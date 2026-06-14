from dataclasses import dataclass
from datetime import datetime

from tong_quant.domain.enums import Market, Regime
from tong_quant.domain.models import require_timezone


@dataclass(frozen=True, slots=True)
class RegimeAssessment:
    market: Market
    as_of: datetime
    regime: Regime
    confidence: float
    reasons: tuple[str, ...]
    model_version: str = "v0"

    def __post_init__(self) -> None:
        require_timezone(self.as_of, "as_of")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if not self.reasons:
            raise ValueError("market regime must be explainable")
