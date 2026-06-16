from datetime import UTC, datetime

from tong_quant.data.readiness import PITReadinessEvaluator, PITReadinessInput
from tong_quant.domain.enums import DataTrustLevel


def test_pit_readiness_separates_coverage_from_trust() -> None:
    assessed_at = datetime(2026, 1, 2, tzinfo=UTC)
    evaluator = PITReadinessEvaluator(minimum_coverage_ratio=0.9)

    high_coverage_low_trust = evaluator.evaluate(
        PITReadinessInput(
            dataset="fundamentals",
            expected_records=100,
            observed_records=100,
            trust_level=DataTrustLevel.LOW,
        ),
        assessed_at=assessed_at,
    )

    assert high_coverage_low_trust.coverage_ratio == 1
    assert high_coverage_low_trust.trust_level is DataTrustLevel.LOW
    assert high_coverage_low_trust.ready_for_historical_replay is False
    assert "trust level low" in " ".join(high_coverage_low_trust.warnings)


def test_pit_readiness_blocks_missing_critical_fields() -> None:
    assessed_at = datetime(2026, 1, 2, tzinfo=UTC)
    evaluator = PITReadinessEvaluator()

    assessment = evaluator.evaluate(
        PITReadinessInput(
            dataset="corporate_actions",
            expected_records=10,
            observed_records=10,
            trust_level=DataTrustLevel.HIGH,
            missing_critical_fields=("available_at",),
        ),
        assessed_at=assessed_at,
    )

    assert assessment.ready_for_historical_replay is False
    assert assessment.missing_critical_fields == ("available_at",)


def test_pit_readiness_allows_replay_when_coverage_and_trust_pass() -> None:
    assessed_at = datetime(2026, 1, 2, tzinfo=UTC)

    assessment = PITReadinessEvaluator().evaluate(
        PITReadinessInput(
            dataset="universe_membership",
            expected_records=100,
            observed_records=98,
            trust_level=DataTrustLevel.HIGH,
        ),
        assessed_at=assessed_at,
    )

    assert assessment.ready_for_historical_replay is True
