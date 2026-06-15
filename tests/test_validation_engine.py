from datetime import UTC, date, datetime, timedelta

import pytest

from tong_quant.domain.enums import (
    DecisionDisposition,
    Market,
    Regime,
    ResearchConclusion,
    ResearchModuleName,
    ResearchRunStatus,
    SignalAction,
    SignalStage,
    ThesisOutcomeStatus,
    ValidationModuleName,
    ValidationStatus,
)
from tong_quant.domain.models import Instrument
from tong_quant.research.models import (
    ConfidenceBreakdown,
    ResearchAssessment,
    ResearchReport,
    ThesisInvalidationCondition,
)
from tong_quant.validation.decision_journal import DecisionJournalValidationModule
from tong_quant.validation.engine import ValidationEngine
from tong_quant.validation.factor_contribution import (
    FactorContributionValidationModule,
)
from tong_quant.validation.historical import HistoricalValidationModule
from tong_quant.validation.market_regime import MarketRegimeValidationModule
from tong_quant.validation.models import (
    DecisionJournalEntry,
    FrameworkSnapshot,
    OutcomeDefinition,
    OutOfSamplePolicy,
    PortfolioResearchPosition,
    ValidationOutcome,
    ValidationRequest,
    ValidationSample,
    WalkForwardPolicy,
)
from tong_quant.validation.out_of_sample import OutOfSampleValidationModule
from tong_quant.validation.outcomes import OutcomeDefinitionRegistry
from tong_quant.validation.portfolio_risk import PortfolioRiskValidationModule
from tong_quant.validation.research_accuracy import (
    ResearchAccuracyValidationModule,
)
from tong_quant.validation.snapshot import stable_configuration_hash
from tong_quant.validation.splits import walk_forward_splits
from tong_quant.validation.thesis import ThesisValidationModule
from tong_quant.validation.walk_forward import WalkForwardValidationModule


def test_snapshot_hash_is_stable_and_records_required_versions() -> None:
    first = stable_configuration_hash({"b": 2, "a": 1})
    second = stable_configuration_hash({"a": 1, "b": 2})
    snapshot = _snapshot(first)

    assert first == second
    assert snapshot.git_commit == "f7e9f903019688bcc874e7c913dcd99fb852365a"
    assert snapshot.framework_version == "0.6.0"
    assert snapshot.database_schema_version == "0.6.0"


def test_outcome_registry_requires_pre_registered_definition() -> None:
    registry = OutcomeDefinitionRegistry((_definition(),))

    assert registry.evaluate("relative-outcome", 1.5) is True
    with pytest.raises(KeyError, match="unknown outcome"):
        registry.evaluate("chosen-after-results", 10)


def test_validation_request_rejects_future_outcome() -> None:
    request = _request()
    sample = request.samples[0]
    future_outcome = ValidationOutcome(
        outcome_id="future",
        definition_id=sample.outcome.definition_id,
        subject_id=sample.outcome.subject_id,
        observed_at=request.as_of + timedelta(days=1),
        available_at=request.as_of + timedelta(days=2),
        value=1,
        benchmark_value=0,
        succeeded=True,
        thesis_status=ThesisOutcomeStatus.SUPPORTED,
        invalidation_triggered=False,
    )
    future_sample = ValidationSample(
        sample_id="future",
        instrument=sample.instrument,
        research_report=sample.research_report,
        decision_at=sample.decision_at,
        research_expected_success=True,
        outcome=future_outcome,
        factor_scores={"value": 70},
    )

    with pytest.raises(ValueError, match="future outcome"):
        _request(samples=(future_sample,))


def test_walk_forward_splits_apply_embargo_and_freeze_configuration() -> None:
    policy = WalkForwardPolicy(
        training_days=100,
        validation_days=30,
        step_days=30,
        embargo_days=10,
    )
    splits = walk_forward_splits(
        date(2020, 1, 1),
        date(2021, 1, 1),
        policy,
        "config-hash",
    )

    training = splits[0]
    validation = splits[1]
    assert (validation.start_date - training.end_date).days == 11
    assert all(split.frozen_configuration_hash == "config-hash" for split in splits)


def test_decision_journal_tracks_research_and_decision_quality_independently() -> None:
    request = _request()
    result = DecisionJournalValidationModule().evaluate(request, ())
    summary = result.decision_summary

    assert summary is not None
    assert summary.research_correct_decision_correct == 1
    assert summary.research_correct_decision_wrong == 1
    assert summary.research_wrong_decision_correct == 1
    assert summary.research_wrong_decision_wrong == 1
    assert result.assessment.integrity_checks[0].passed is True


def test_decision_journal_rejects_snapshot_mismatch() -> None:
    request = _request()
    sample = request.samples[0]
    decision = sample.decision
    assert decision is not None
    mismatched = DecisionJournalEntry(
        decision_id=decision.decision_id,
        research_report_id=decision.research_report_id,
        decided_at=decision.decided_at,
        available_at=decision.available_at,
        disposition=decision.disposition,
        rationale=decision.rationale,
        confidence=decision.confidence,
        decision_maker=decision.decision_maker,
        framework_snapshot_hash="wrong-snapshot-hash",
    )
    changed = ValidationSample(
        sample_id=sample.sample_id,
        instrument=sample.instrument,
        research_report=sample.research_report,
        decision_at=sample.decision_at,
        research_expected_success=sample.research_expected_success,
        outcome=sample.outcome,
        factor_scores=sample.factor_scores,
        market_regime=sample.market_regime,
        decision=mismatched,
        portfolio_position=sample.portfolio_position,
    )
    changed_request = _request(samples=(changed, *request.samples[1:]))

    result = DecisionJournalValidationModule().evaluate(changed_request, ())

    assert result.assessment.status is ValidationStatus.FAILED_INTEGRITY_CHECK


def test_portfolio_validation_measures_four_research_concentrations() -> None:
    request = _request()
    result = PortfolioRiskValidationModule(
        maximum_category_weight=0.50,
        maximum_hhi=0.40,
    ).evaluate(request, ())
    summary = result.portfolio_risk

    assert summary is not None
    assert {item.dimension for item in summary.concentrations} == {
        "industry",
        "country",
        "theme",
        "style",
    }
    assert any(item.breached for item in summary.concentrations)
    assert result.assessment.metrics["total_research_weight"] == pytest.approx(0.8)


def test_validation_engine_produces_review_signal_without_trade_decision() -> None:
    request = _request()
    engine = _engine()

    run = engine.run(request)

    assert run.signal.stage is SignalStage.VALIDATION
    assert run.signal.action is SignalAction.REVIEW
    assert run.signal.features["informational_only"] is True
    assert run.signal.features["creates_trade_decision"] is False
    assert len(run.report.assessments) == len(ValidationModuleName)
    assert run.report.reproducibility_manifest["git_commit"] == (
        request.framework_snapshot.git_commit
    )
    assert run.report.decision_summary is not None
    assert run.report.portfolio_risk is not None
    assert not hasattr(run, "order")


def test_factor_and_accuracy_results_remain_separate() -> None:
    request = _request()
    factor = FactorContributionValidationModule().evaluate(request, ())
    accuracy = ResearchAccuracyValidationModule().evaluate(request, ())

    assert factor.factor_contributions
    assert accuracy.accuracy is not None
    assert "accuracy" in accuracy.assessment.metrics
    assert factor.assessment.module is ValidationModuleName.FACTOR_CONTRIBUTION
    assert accuracy.assessment.module is ValidationModuleName.RESEARCH_ACCURACY


def _engine() -> ValidationEngine:
    return ValidationEngine(
        modules=(
            HistoricalValidationModule(),
            WalkForwardValidationModule(minimum_windows=1),
            OutOfSampleValidationModule(),
            MarketRegimeValidationModule(),
            ThesisValidationModule(),
            FactorContributionValidationModule(),
            ResearchAccuracyValidationModule(),
            DecisionJournalValidationModule(),
            PortfolioRiskValidationModule(),
        )
    )


def _request(
    *,
    samples: tuple[ValidationSample, ...] | None = None,
) -> ValidationRequest:
    snapshot = _snapshot(stable_configuration_hash({"validation": "test"}))
    return ValidationRequest(
        validation_id="validation-v0.6-test",
        subject=_instrument(),
        start_at=datetime(2020, 1, 1, tzinfo=UTC),
        end_at=datetime(2025, 12, 31, tzinfo=UTC),
        as_of=datetime(2026, 1, 31, tzinfo=UTC),
        requested_at=datetime(2026, 2, 1, tzinfo=UTC),
        modules=tuple(ValidationModuleName),
        samples=samples or _samples(snapshot),
        outcome_definitions=(_definition(),),
        framework_snapshot=snapshot,
        walk_forward_policy=WalkForwardPolicy(
            training_days=365,
            validation_days=180,
            step_days=180,
            embargo_days=20,
        ),
        out_of_sample_policy=OutOfSamplePolicy(
            development_end=date(2024, 12, 31),
            out_of_sample_start=date(2025, 1, 1),
            out_of_sample_end=date(2025, 12, 31),
            frozen_configuration_hash=snapshot.configuration_hash,
        ),
        minimum_observations=2,
    )


def _samples(snapshot: FrameworkSnapshot) -> tuple[ValidationSample, ...]:
    cases = (
        (
            datetime(2021, 6, 1, tzinfo=UTC),
            True,
            True,
            DecisionDisposition.ADVANCE,
            "Banks",
            "China",
            "Dividend",
            "Value",
        ),
        (
            datetime(2022, 6, 1, tzinfo=UTC),
            True,
            True,
            DecisionDisposition.REJECT,
            "Banks",
            "China",
            "Dividend",
            "Value",
        ),
        (
            datetime(2023, 6, 1, tzinfo=UTC),
            True,
            False,
            DecisionDisposition.REJECT,
            "Technology",
            "China",
            "AI",
            "Growth",
        ),
        (
            datetime(2025, 6, 1, tzinfo=UTC),
            False,
            True,
            DecisionDisposition.REJECT,
            "Technology",
            "US",
            "AI",
            "Growth",
        ),
    )
    samples = []
    for index, (
        decision_at,
        expected,
        succeeded,
        disposition,
        industry,
        country,
        theme,
        style,
    ) in enumerate(cases):
        report = _research_report(index, decision_at)
        outcome_at = decision_at + timedelta(days=120)
        outcome = ValidationOutcome(
            outcome_id=f"outcome-{index}",
            definition_id="relative-outcome",
            subject_id=f"sample-{index}",
            observed_at=outcome_at,
            available_at=outcome_at + timedelta(days=1),
            value=2 if succeeded else -2,
            benchmark_value=0,
            succeeded=succeeded,
            thesis_status=(
                ThesisOutcomeStatus.SUPPORTED
                if succeeded
                else ThesisOutcomeStatus.INVALIDATED
            ),
            invalidation_triggered=not succeeded,
        )
        samples.append(
            ValidationSample(
                sample_id=f"sample-{index}",
                instrument=_instrument(),
                research_report=report,
                decision_at=decision_at,
                research_expected_success=expected,
                outcome=outcome,
                factor_scores={
                    "value": 80 if succeeded else 30,
                    "industry": 75 if succeeded else 35,
                },
                market_regime=(
                    Regime.BULL if index % 2 == 0 else Regime.SIDEWAYS
                ),
                decision=DecisionJournalEntry(
                    decision_id=f"decision-{index}",
                    research_report_id=report.report_id,
                    decided_at=decision_at,
                    available_at=decision_at,
                    disposition=disposition,
                    rationale=("Documented validation test decision",),
                    confidence=70,
                    decision_maker="test",
                    framework_snapshot_hash=snapshot.configuration_hash,
                ),
                portfolio_position=PortfolioResearchPosition(
                    subject_id=f"sample-{index}",
                    research_weight=0.2,
                    country=country,
                    industry=industry,
                    theme=theme,
                    style=style,
                ),
            )
        )
    return tuple(samples)


def _research_report(index: int, decision_at: datetime) -> ResearchReport:
    confidence = ConfidenceBreakdown(
        evidence_quality=80,
        data_completeness=80,
        module_agreement=80,
        point_in_time_integrity=100,
        confidence=80,
    )
    assessment = ResearchAssessment(
        module=ResearchModuleName.VALUE,
        conclusion=ResearchConclusion.SUPPORTIVE,
        score=70,
        confidence=confidence,
        evaluated_at=decision_at - timedelta(days=1),
        available_at=decision_at - timedelta(days=1),
        findings=("Research finding",),
        risks=("Research risk",),
        limitations=(),
        evidence_ids=("evidence",),
        model_version="value-v0.5",
    )
    return ResearchReport(
        report_id=f"report-{index}",
        queue_id=f"queue-{index}",
        instrument_id="china_a:equity:600000",
        generated_at=decision_at - timedelta(days=1),
        available_at=decision_at - timedelta(days=1),
        status=ResearchRunStatus.COMPLETED,
        thesis="Demand may improve",
        counter_thesis="Demand may weaken",
        invalidation_conditions=(
            ThesisInvalidationCondition(
                condition_id="revenue",
                description="Revenue growth falls below zero",
                metric="revenue_growth",
                operator="<",
                threshold=0,
                observation_window="two quarters",
                rationale="Growth is required",
            ),
        ),
        assessments=(assessment,),
        policy_assessment=None,
        confidence=confidence,
        key_findings=("Research finding",),
        key_risks=("Research risk",),
        unresolved_questions=(),
        market_regime=None,
        model_version="research-engine-v0.5",
    )


def _definition() -> OutcomeDefinition:
    return OutcomeDefinition(
        outcome_id="relative-outcome",
        target_metric="relative_research_outcome",
        observation_horizon_days=120,
        success_operator=">",
        success_threshold=0,
        availability_lag_days=1,
        benchmark="CSI 300",
    )


def _snapshot(configuration_hash: str) -> FrameworkSnapshot:
    return FrameworkSnapshot(
        git_commit="f7e9f903019688bcc874e7c913dcd99fb852365a",
        framework_version="0.6.0",
        configuration_hash=configuration_hash,
        research_version="research-engine-v0.5",
        validation_version="validation-engine-v0.6",
        database_schema_version="0.6.0",
        captured_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _instrument() -> Instrument:
    return Instrument("600000", Market.CHINA_A, "Example")
