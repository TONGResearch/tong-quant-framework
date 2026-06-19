from collections.abc import Iterable
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from tong_quant.core.exceptions import ExecutionDisabledError
from tong_quant.domain.enums import Market, SignalAction, SignalStage
from tong_quant.domain.models import Instrument, RiskDecision, Signal
from tong_quant.execution import (
    ExecutionDisabledGuard,
    ExecutionReadinessContext,
    ExecutionReadinessGate,
    Order,
    OrderSide,
    OrderType,
)


def test_execution_readiness_gate_fails_closed_by_default() -> None:
    report = ExecutionReadinessGate().evaluate(ExecutionReadinessContext())

    assert report.ready is False
    assert "execution mode is disabled" in report.reasons
    assert "live order permission is disabled" in report.reasons


def test_guard_blocks_order_factory_until_readiness_is_explicit() -> None:
    factory = _FakeOrderFactory()
    guard = ExecutionDisabledGuard()

    with pytest.raises(ExecutionDisabledError, match="execution mode is disabled"):
        guard.wrap_order_factory(factory).create(_signal(), _risk_decision(approved=True))

    assert factory.created == 0


def test_guard_allows_factory_and_broker_only_after_full_readiness() -> None:
    risk_decision = _risk_decision(approved=True)
    context = ExecutionReadinessContext(
        mode="semi_automatic",
        allow_live_orders=True,
        require_manual_approval=True,
        broker="qmt",
        risk_decision=risk_decision,
        validation_report_id="validation-1",
        portfolio_proposal_id="proposal-1",
        risk_assessment_id="risk-1",
        manual_approval_id="approval-1",
        readiness_token="ready-1",
    )
    guard = ExecutionDisabledGuard(context=context)
    factory = _FakeOrderFactory()
    broker = _FakeBroker()

    order = guard.wrap_order_factory(factory).create(_signal(), risk_decision)
    receipt = guard.wrap_broker(broker).submit(order)

    assert factory.created == 1
    assert receipt == "accepted"
    assert broker.submitted == 1


def test_gate_rejects_unapproved_risk_decision_even_with_live_mode() -> None:
    context = ExecutionReadinessContext(
        mode="automatic",
        allow_live_orders=True,
        require_manual_approval=False,
        broker="ibkr",
        risk_decision=_risk_decision(approved=False),
        validation_report_id="validation-1",
        portfolio_proposal_id="proposal-1",
        risk_assessment_id="risk-1",
        readiness_token="ready-1",
    )

    with pytest.raises(ExecutionDisabledError, match="approved RiskDecision"):
        ExecutionReadinessGate().require_ready(context)


class _FakeOrderFactory:
    def __init__(self) -> None:
        self.created = 0

    def create(self, signal: Signal, risk_decision: RiskDecision) -> Order:
        del risk_decision
        self.created += 1
        return Order(
            signal=signal,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=100,
            created_at=datetime(2026, 1, 2, tzinfo=UTC),
            limit_price=Decimal("10.00"),
        )


class _FakeBroker:
    broker_id = "qmt"

    def __init__(self) -> None:
        self.submitted = 0

    def submit(self, order: Order) -> str:
        del order
        self.submitted += 1
        return "accepted"

    def reconcile(self) -> Iterable[str]:
        return ()


def _signal() -> Signal:
    return Signal(
        source="test",
        stage=SignalStage.VALIDATION,
        instrument=Instrument(
            symbol="600000",
            market=Market.CHINA_A,
            name="Instrument 600000",
            available_at=datetime(2026, 1, 1, tzinfo=UTC),
            source="test",
        ),
        generated_at=datetime(2026, 1, 2, tzinfo=UTC),
        effective_at=datetime(2026, 1, 2, tzinfo=UTC),
        action=SignalAction.REVIEW,
        strength=0.5,
        reasons=("validation review",),
    )


def _risk_decision(*, approved: bool) -> RiskDecision:
    return RiskDecision(
        approved=approved,
        checked_at=datetime(2026, 1, 2, tzinfo=UTC),
        reasons=("risk checked",),
    )
