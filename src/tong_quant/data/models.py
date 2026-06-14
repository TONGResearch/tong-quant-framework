from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pandas as pd

from tong_quant.domain.enums import Adjustment, AssetType, Market
from tong_quant.domain.models import require_timezone


@dataclass(frozen=True, slots=True)
class RawDataset:
    dataset: str
    frame: pd.DataFrame
    retrieved_at: datetime
    source: str
    parameters: dict[str, Any]

    def __post_init__(self) -> None:
        require_timezone(self.retrieved_at, "retrieved_at")


@dataclass(frozen=True, slots=True)
class DailyBarRequest:
    symbol: str
    start_date: str
    end_date: str
    asset_type: AssetType = AssetType.EQUITY
    market: Market = Market.CHINA_A
    adjustment: Adjustment = Adjustment.NONE


@dataclass(frozen=True, slots=True)
class IngestionResult:
    dataset: str
    received: int
    accepted: int
    rejected: int
    cached: bool


@dataclass(frozen=True, slots=True)
class ProviderResponse:
    dataset: RawDataset
    cache_hit: bool
