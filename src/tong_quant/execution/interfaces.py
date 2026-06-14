from collections.abc import Iterable
from typing import Protocol

from tong_quant.domain.models import RiskDecision, Signal
from tong_quant.execution.models import Order


class OrderFactory(Protocol):
    def create(self, signal: Signal, risk_decision: RiskDecision) -> Order: ...


class Broker(Protocol):
    broker_id: str

    def submit(self, order: Order) -> str: ...

    def reconcile(self) -> Iterable[str]: ...
