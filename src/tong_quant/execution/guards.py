from collections.abc import Iterable
from dataclasses import dataclass, replace
from typing import Protocol

from tong_quant.core.exceptions import ExecutionDisabledError
from tong_quant.domain.models import RiskDecision, Signal
from tong_quant.execution.models import Order

EXECUTION_DISABLED_MODES = frozenset({"disabled", "research", "paper"})
EXECUTION_ENABLED_MODES = frozenset({"semi_automatic", "automatic"})


@dataclass(frozen=True, slots=True)
class ExecutionReadinessContext:
    mode: str = "disabled"
    allow_live_orders: bool = False
    require_manual_approval: bool = True
    broker: str = ""
    risk_decision: RiskDecision | None = None
    validation_report_id: str = ""
    portfolio_proposal_id: str = ""
    risk_assessment_id: str = ""
    manual_approval_id: str = ""
    readiness_token: str = ""


@dataclass(frozen=True, slots=True)
class ExecutionReadinessReport:
    ready: bool
    reasons: tuple[str, ...]


class _OrderFactoryLike(Protocol):
    def create(self, signal: Signal, risk_decision: RiskDecision) -> Order: ...


class _BrokerLike(Protocol):
    broker_id: str

    def submit(self, order: Order) -> str: ...

    def reconcile(self) -> Iterable[str]: ...


@dataclass(frozen=True, slots=True)
class ExecutionReadinessGate:
    """Fail-closed readiness gate for all future execution entry points."""

    def evaluate(self, context: ExecutionReadinessContext) -> ExecutionReadinessReport:
        reasons: list[str] = []
        if context.mode in EXECUTION_DISABLED_MODES:
            reasons.append(f"execution mode is {context.mode}")
        if context.mode not in EXECUTION_ENABLED_MODES:
            reasons.append("execution mode is not execution-enabled")
        if not context.allow_live_orders:
            reasons.append("live order permission is disabled")
        if context.broker in {"", "paper"}:
            reasons.append("live broker is not configured")
        if context.risk_decision is None or not context.risk_decision.approved:
            reasons.append("approved RiskDecision is required")
        if not context.validation_report_id.strip():
            reasons.append("ValidationReport evidence is required")
        if not context.portfolio_proposal_id.strip():
            reasons.append("PortfolioProposal evidence is required")
        if not context.risk_assessment_id.strip():
            reasons.append("RiskAssessment evidence is required")
        if context.require_manual_approval and not context.manual_approval_id.strip():
            reasons.append("manual approval is required")
        if not context.readiness_token.strip():
            reasons.append("explicit execution readiness token is required")
        return ExecutionReadinessReport(ready=not reasons, reasons=tuple(reasons))

    def require_ready(self, context: ExecutionReadinessContext) -> None:
        report = self.evaluate(context)
        if not report.ready:
            raise ExecutionDisabledError("; ".join(report.reasons))


@dataclass(frozen=True, slots=True)
class ExecutionDisabledGuard:
    gate: ExecutionReadinessGate = ExecutionReadinessGate()
    context: ExecutionReadinessContext = ExecutionReadinessContext()

    def require_ready(self, context: ExecutionReadinessContext | None = None) -> None:
        self.gate.require_ready(self.context if context is None else context)

    def create_order(
        self,
        factory: _OrderFactoryLike,
        signal: Signal,
        risk_decision: RiskDecision,
    ) -> Order:
        context = replace(self.context, risk_decision=risk_decision)
        self.require_ready(context)
        return factory.create(signal, risk_decision)

    def submit_order(self, broker: _BrokerLike, order: Order) -> str:
        self.require_ready()
        return str(broker.submit(order))

    def wrap_order_factory(self, factory: _OrderFactoryLike) -> "GuardedOrderFactory":
        return GuardedOrderFactory(factory=factory, guard=self)

    def wrap_broker(self, broker: _BrokerLike) -> "GuardedBroker":
        return GuardedBroker(broker=broker, guard=self)


@dataclass(frozen=True, slots=True)
class GuardedOrderFactory:
    factory: _OrderFactoryLike
    guard: ExecutionDisabledGuard

    def create(self, signal: Signal, risk_decision: RiskDecision) -> Order:
        return self.guard.create_order(self.factory, signal, risk_decision)


@dataclass(frozen=True, slots=True)
class GuardedBroker:
    broker: _BrokerLike
    guard: ExecutionDisabledGuard

    @property
    def broker_id(self) -> str:
        return self.broker.broker_id

    def submit(self, order: Order) -> str:
        return self.guard.submit_order(self.broker, order)

    def reconcile(self) -> Iterable[str]:
        self.guard.require_ready()
        return self.broker.reconcile()


__all__ = [
    "ExecutionDisabledGuard",
    "ExecutionReadinessContext",
    "ExecutionReadinessGate",
    "ExecutionReadinessReport",
    "GuardedBroker",
    "GuardedOrderFactory",
]
