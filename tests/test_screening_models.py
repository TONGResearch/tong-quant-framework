from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from tong_quant.domain.enums import Market, SecurityStatus
from tong_quant.domain.models import Instrument, InstrumentStatus
from tong_quant.screening.models import HardScreenObservation, OpportunityCandidate


def test_candidate_scores_are_independent() -> None:
    candidate = _candidate(urgency=90, confidence=40)

    assert candidate.urgency_score == 90
    assert candidate.confidence_score == 40


def test_hard_screen_observation_rejects_future_status() -> None:
    as_of = datetime(2026, 1, 2, tzinfo=UTC)
    candidate = _candidate(as_of=as_of)
    status = InstrumentStatus(
        candidate.instrument,
        effective_from=date(2026, 1, 1),
        status=SecurityStatus.LISTED,
        is_tradable=True,
        available_at=datetime(2026, 1, 3, tzinfo=UTC),
        source="test",
    )

    with pytest.raises(ValueError, match="future instrument status"):
        HardScreenObservation(
            candidate=candidate,
            as_of=as_of,
            available_at=as_of,
            status=status,
            data_quality_passed=True,
            average_daily_turnover=Decimal("1"),
            financial_health_score=50,
        )


def _candidate(
    *,
    urgency: float = 50,
    confidence: float = 60,
    as_of: datetime | None = None,
) -> OpportunityCandidate:
    timestamp = as_of or datetime(2026, 1, 2, tzinfo=UTC)
    return OpportunityCandidate(
        instrument=Instrument("600000", Market.CHINA_A, "Example"),
        discovery_source="discovery.policy",
        discovered_at=timestamp,
        available_at=timestamp,
        thesis="Policy support may improve long-term industry demand",
        evidence=("Policy document published",),
        urgency_score=urgency,
        confidence_score=confidence,
    )
