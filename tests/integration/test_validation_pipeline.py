from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import (
    DecisionDisposition,
    Market,
    Regime,
    ResearchConclusion,
    ResearchModuleName,
    ResearchRunStatus,
    ThesisOutcomeStatus,
    ValidationModuleName,
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
from tong_quant.validation.portfolio_risk import PortfolioRiskValidationModule
from tong_quant.validation.repository import SQLiteValidationRepository
from tong_quant.validation.research_accuracy import (
    ResearchAccuracyValidationModule,
)

pytestmark = pytest.mark.integration


def test_validation_run_persists_reproducible_audit_chain(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "validation.sqlite3")
    store.initialize()
    instrument = Instrument(
        "600000",
        Market.CHINA_A,
        "Example",
        available_at=datetime(2024, 1, 1, tzinfo=UTC),
        source="test",
    )
    store.upsert_instruments([instrument])
    request = _request(instrument)
    engine = ValidationEngine(
        modules=(
            HistoricalValidationModule(),
            FactorContributionValidationModule(),
            ResearchAccuracyValidationModule(),
            DecisionJournalValidationModule(),
            PortfolioRiskValidationModule(),
        ),
        repository=SQLiteValidationRepository(store),
    )

    run = engine.run(request)

    assert run.report.reproducibility_manifest["database_schema_version"] == "0.7.0"
    assert store.table_count("validation_runs") == 1
    assert store.table_count("validation_oos_usage") == 1
    assert store.table_count("validation_splits") >= 1
    assert store.table_count("validation_observations") == 1
    assert store.table_count("validation_outcomes") == 1
    assert store.table_count("validation_outcome_definitions") == 1
    assert store.table_count("decision_journal") == 1
    assert store.table_count("validation_assessments") == 5
    assert store.table_count("validation_reports") == 1
    assert store.table_count("validation_factor_contributions") == 2
    assert store.table_count("validation_accuracy_history") == 1
    assert store.table_count("validation_integrity_checks") >= 1
    assert store.table_count("validation_portfolio_risk") == 4
    assert store.table_count("signals") == 1

    with pytest.raises(ValueError, match="usage limit"):
        engine.run(request)


def test_repository_rejects_schema_snapshot_mismatch(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "validation.sqlite3")
    store.initialize()
    request = _request(Instrument("600000", Market.CHINA_A, "Example"))
    snapshot = request.framework_snapshot
    mismatched = FrameworkSnapshot(
        git_commit=snapshot.git_commit,
        framework_version=snapshot.framework_version,
        configuration_hash=snapshot.configuration_hash,
        research_version=snapshot.research_version,
        validation_version=snapshot.validation_version,
        database_schema_version="0.5.0",
        captured_at=snapshot.captured_at,
    )
    changed = ValidationRequest(
        validation_id=request.validation_id,
        subject=request.subject,
        start_at=request.start_at,
        end_at=request.end_at,
        as_of=request.as_of,
        requested_at=request.requested_at,
        modules=request.modules,
        samples=request.samples,
        outcome_definitions=request.outcome_definitions,
        framework_snapshot=mismatched,
        walk_forward_policy=request.walk_forward_policy,
        out_of_sample_policy=request.out_of_sample_policy,
        minimum_observations=request.minimum_observations,
    )

    with pytest.raises(ValueError, match="schema version does not match"):
        SQLiteValidationRepository(store).start_run(changed)


def _request(instrument: Instrument) -> ValidationRequest:
    decision_at = datetime(2025, 6, 1, tzinfo=UTC)
    snapshot = FrameworkSnapshot(
        git_commit="f7e9f903019688bcc874e7c913dcd99fb852365a",
        framework_version="0.7.0",
        configuration_hash="a" * 64,
        research_version="research-engine-v0.5",
        validation_version="validation-engine-v0.6",
        database_schema_version="0.7.0",
        captured_at=datetime(2025, 1, 1, tzinfo=UTC),
    )
    report = _report(decision_at)
    outcome_at = decision_at + timedelta(days=120)
    sample = ValidationSample(
        sample_id="sample-1",
        instrument=instrument,
        research_report=report,
        decision_at=decision_at,
        research_expected_success=True,
        outcome=ValidationOutcome(
            outcome_id="outcome-1",
            definition_id="relative-outcome",
            subject_id="sample-1",
            observed_at=outcome_at,
            available_at=outcome_at + timedelta(days=1),
            value=5,
            benchmark_value=1,
            succeeded=True,
            thesis_status=ThesisOutcomeStatus.SUPPORTED,
            invalidation_triggered=False,
        ),
        factor_scores={"value": 80, "industry": 75},
        market_regime=Regime.BULL,
        decision=DecisionJournalEntry(
            decision_id="decision-1",
            research_report_id=report.report_id,
            decided_at=decision_at,
            available_at=decision_at,
            disposition=DecisionDisposition.ADVANCE,
            rationale=("Research was advanced for further validation",),
            confidence=75,
            decision_maker="integration-test",
            framework_snapshot_hash=snapshot.configuration_hash,
        ),
        portfolio_position=PortfolioResearchPosition(
            subject_id="sample-1",
            research_weight=0.2,
            country="China",
            industry="Banks",
            theme="Dividend",
            style="Value",
        ),
    )
    return ValidationRequest(
        validation_id="validation-integration",
        subject=instrument,
        start_at=datetime(2024, 1, 1, tzinfo=UTC),
        end_at=datetime(2025, 12, 31, tzinfo=UTC),
        as_of=datetime(2026, 1, 31, tzinfo=UTC),
        requested_at=datetime(2026, 2, 1, tzinfo=UTC),
        modules=(
            ValidationModuleName.HISTORICAL,
            ValidationModuleName.FACTOR_CONTRIBUTION,
            ValidationModuleName.RESEARCH_ACCURACY,
            ValidationModuleName.DECISION_JOURNAL,
            ValidationModuleName.PORTFOLIO_RISK,
        ),
        samples=(sample,),
        outcome_definitions=(
            OutcomeDefinition(
                outcome_id="relative-outcome",
                target_metric="relative_research_outcome",
                observation_horizon_days=120,
                success_operator=">",
                success_threshold=0,
                availability_lag_days=1,
                benchmark="CSI 300",
            ),
        ),
        framework_snapshot=snapshot,
        walk_forward_policy=WalkForwardPolicy(
            training_days=180,
            validation_days=60,
            step_days=60,
            embargo_days=10,
        ),
        out_of_sample_policy=OutOfSamplePolicy(
            development_end=date(2024, 12, 31),
            out_of_sample_start=date(2025, 1, 1),
            out_of_sample_end=date(2025, 12, 31),
            frozen_configuration_hash=snapshot.configuration_hash,
        ),
        minimum_observations=1,
    )


def _report(decision_at: datetime) -> ResearchReport:
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
        report_id="report-1",
        queue_id="queue-1",
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
