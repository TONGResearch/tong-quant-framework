from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from tong_quant.domain.models import Signal, require_timezone


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"


@dataclass(frozen=True, slots=True)
class Order:
    signal: Signal
    side: OrderSide
    order_type: OrderType
    quantity: int
    created_at: datetime
    limit_price: Decimal | None = None
    order_id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        require_timezone(self.created_at, "created_at")
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.order_type is OrderType.LIMIT and self.limit_price is None:
            raise ValueError("limit orders require a limit price")
