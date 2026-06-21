from datetime import UTC, datetime

from tong_quant.data.calibration import DatasetConfidenceAssessment
from tong_quant.data.readiness import (
    PITReadinessEvaluator,
    PITReadinessInput,
    apply_provider_confidence,
)
from tong_quant.domain.enums import DataTrustLevel, PITReadinessClassification


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
    assert high_coverage_low_trust.classification is PITReadinessClassification.UNSUITABLE
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
            availability_score=100,
            revision_score=100,
            continuity_score=100,
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
            availability_score=100,
            revision_score=100,
            continuity_score=100,
            provider_consistency_score=95,
        ),
        assessed_at=assessed_at,
    )

    assert assessment.ready_for_historical_replay is True
    assert assessment.classification is PITReadinessClassification.USABLE
    assert assessment.readiness_score >= 80


def test_pit_readiness_marks_partial_evidence_as_caution() -> None:
    assessment = PITReadinessEvaluator().evaluate(
        PITReadinessInput(
            dataset="security_lifecycle",
            expected_records=100,
            observed_records=75,
            trust_level=DataTrustLevel.MEDIUM,
            availability_score=60,
            revision_score=40,
            continuity_score=60,
        ),
        assessed_at=datetime(2026, 1, 2, tzinfo=UTC),
    )

    assert assessment.classification is PITReadinessClassification.CAUTION
    assert assessment.ready_for_historical_replay is False
    assert "secondary-provider consistency is unknown" in assessment.warnings


def test_critical_provider_conflict_caps_pit_readiness() -> None:
    readiness_input = PITReadinessInput(
        dataset="st_status",
        expected_records=100,
        observed_records=100,
        trust_level=DataTrustLevel.HIGH,
        availability_score=100,
        revision_score=100,
        continuity_score=100,
    )
    confidence = DatasetConfidenceAssessment(
        assessment_id="a" * 64,
        report_id="b" * 64,
        dataset="st_status",
        assessed_at=datetime(2026, 1, 1, tzinfo=UTC),
        confidence_score=79,
        trust_level=DataTrustLevel.LOW,
        component_scores={"provider_consistency": 90},
        conflict_count=1,
        critical_conflict_count=1,
        warnings=("status mismatch",),
    )

    assessment = PITReadinessEvaluator().evaluate(
        apply_provider_confidence(readiness_input, confidence),
        assessed_at=datetime(2026, 1, 2, tzinfo=UTC),
    )

    assert assessment.classification is PITReadinessClassification.CAUTION
    assert assessment.ready_for_historical_replay is False
    assert "prevent usable" in " ".join(assessment.warnings)


def test_required_provider_calibration_caps_unknown_consistency() -> None:
    assessment = PITReadinessEvaluator().evaluate(
        PITReadinessInput(
            dataset="universe_coverage",
            expected_records=100,
            observed_records=100,
            trust_level=DataTrustLevel.HIGH,
            availability_score=100,
            revision_score=100,
            continuity_score=100,
            provider_consistency_required=True,
        ),
        assessed_at=datetime(2026, 1, 2, tzinfo=UTC),
    )

    assert assessment.classification is PITReadinessClassification.CAUTION
    assert "required provider calibration is unavailable" in assessment.warnings
