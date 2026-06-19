from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from hashlib import sha256
from typing import Any
from uuid import uuid4

from tong_quant.data.storage.sqlite import SQLiteStore, instrument_id
from tong_quant.validation.models import ValidationRequest, ValidationRun


@dataclass(slots=True)
class SQLiteValidationRepository:
    store: SQLiteStore
    model_version: str = "validation-run-v0.6"

    def start_run(self, request: ValidationRequest) -> str:
        if request.framework_snapshot.database_schema_version != self.store.schema_version():
            raise ValueError("framework snapshot database schema version does not match")
        run_id = str(uuid4())
        self.store.start_validation_run(
            run_id=run_id,
            validation_id=request.validation_id,
            subject_id=instrument_id(request.subject),
            started_at=request.requested_at,
            framework_snapshot=_jsonable(asdict(request.framework_snapshot)),
            model_version=self.model_version,
            oos_key=_oos_key(request),
            oos_configuration_hash=(
                request.out_of_sample_policy.frozen_configuration_hash
            ),
            oos_start_date=request.out_of_sample_policy.out_of_sample_start,
            oos_end_date=request.out_of_sample_policy.out_of_sample_end,
            oos_maximum_uses=request.out_of_sample_policy.maximum_uses,
        )
        return run_id

    def save_run(self, run: ValidationRun) -> None:
        with self.store.transaction():
            self._save_run(run)

    def _save_run(self, run: ValidationRun) -> None:
        request = run.request
        report = run.report
        for definition in request.outcome_definitions:
            self.store.save_validation_outcome_definition(
                run_id=run.run_id,
                outcome_id=definition.outcome_id,
                target_metric=definition.target_metric,
                observation_horizon_days=definition.observation_horizon_days,
                success_operator=definition.success_operator,
                success_threshold=definition.success_threshold,
                availability_lag_days=definition.availability_lag_days,
                benchmark=definition.benchmark,
                version=definition.version,
            )
        for split in report.splits:
            self.store.save_validation_split(
                run_id=run.run_id,
                split_id=split.split_id,
                kind=split.kind.value,
                start_date=split.start_date,
                end_date=split.end_date,
                frozen_configuration_hash=split.frozen_configuration_hash,
                sequence=split.sequence,
            )
        for sample in request.samples:
            position = sample.portfolio_position
            self.store.save_validation_observation(
                run_id=run.run_id,
                sample_id=sample.sample_id,
                instrument_id_value=instrument_id(sample.instrument),
                research_report_id=sample.research_report.report_id,
                decision_at=sample.decision_at,
                research_expected_success=sample.research_expected_success,
                market_regime=(
                    None
                    if sample.market_regime is None
                    else sample.market_regime.value
                ),
                factor_scores=sample.factor_scores,
                portfolio_position=(
                    None if position is None else _jsonable(asdict(position))
                ),
            )
            outcome = sample.outcome
            self.store.save_validation_outcome(
                run_id=run.run_id,
                outcome_id=outcome.outcome_id,
                definition_id=outcome.definition_id,
                subject_id=outcome.subject_id,
                observed_at=outcome.observed_at,
                available_at=outcome.available_at,
                value=outcome.value,
                benchmark_value=outcome.benchmark_value,
                succeeded=outcome.succeeded,
                thesis_status=outcome.thesis_status.value,
                invalidation_triggered=outcome.invalidation_triggered,
                metadata=_jsonable(outcome.metadata),
            )
            decision = sample.decision
            if decision is not None:
                self.store.save_decision_journal_entry(
                    decision_id=decision.decision_id,
                    run_id=run.run_id,
                    research_report_id=decision.research_report_id,
                    decided_at=decision.decided_at,
                    available_at=decision.available_at,
                    disposition=decision.disposition.value,
                    rationale=decision.rationale,
                    confidence=decision.confidence,
                    decision_maker=decision.decision_maker,
                    framework_snapshot_hash=decision.framework_snapshot_hash,
                )
        self.store.save_validation_report(
            run_id=run.run_id,
            report_id=report.report_id,
            validation_id=report.validation_id,
            generated_at=report.generated_at,
            status=report.status.value,
            aggregate_status=report.aggregate_status.value,
            framework_snapshot=_jsonable(asdict(report.framework_snapshot)),
            known_limitations=report.known_limitations,
            reproducibility_manifest=report.reproducibility_manifest,
            decision_summary=(
                None
                if report.decision_summary is None
                else _jsonable(asdict(report.decision_summary))
            ),
            portfolio_risk=(
                None
                if report.portfolio_risk is None
                else _jsonable(asdict(report.portfolio_risk))
            ),
            model_version=report.model_version,
        )
        for assessment in report.assessments:
            self.store.save_validation_assessment(
                run_id=run.run_id,
                report_id=report.report_id,
                module=assessment.module.value,
                status=assessment.status.value,
                score=assessment.score,
                confidence=assessment.confidence,
                sample_size=assessment.sample_size,
                evaluated_at=assessment.evaluated_at,
                metrics=_jsonable(assessment.metrics),
                findings=assessment.findings,
                risks=assessment.risks,
                limitations=assessment.limitations,
                model_version=assessment.model_version,
            )
            for check in assessment.integrity_checks:
                self.store.save_validation_integrity_check(
                    run_id=run.run_id,
                    report_id=report.report_id,
                    module=assessment.module.value,
                    check_id=check.check_id,
                    passed=check.passed,
                    checked_at=check.checked_at,
                    reasons=check.reasons,
                )
        for contribution in report.factor_contributions:
            self.store.save_validation_factor_contribution(
                run_id=run.run_id,
                report_id=report.report_id,
                factor=contribution.factor,
                sample_size=contribution.sample_size,
                success_score_gap=contribution.success_score_gap,
                ablation_brier_delta=contribution.ablation_brier_delta,
                stable=contribution.stable,
            )
        if report.accuracy is not None:
            accuracy = report.accuracy
            self.store.save_validation_accuracy(
                run_id=run.run_id,
                report_id=report.report_id,
                sample_size=accuracy.sample_size,
                accuracy=accuracy.accuracy,
                brier_score=accuracy.brier_score,
                calibration_error=accuracy.calibration_error,
                high_confidence_failure_rate=accuracy.high_confidence_failure_rate,
                recorded_at=report.generated_at,
            )
        if report.portfolio_risk is not None:
            for concentration in report.portfolio_risk.concentrations:
                self.store.save_validation_portfolio_risk(
                    run_id=run.run_id,
                    report_id=report.report_id,
                    dimension=concentration.dimension,
                    total_weight=report.portfolio_risk.total_weight,
                    maximum_weight=concentration.maximum_weight,
                    hhi=concentration.hhi,
                    category_weights=concentration.category_weights,
                    breached=concentration.breached,
                )
        self.store.save_signal(run.signal)
        self.store.complete_validation_run(
            run_id=run.run_id,
            status=report.status,
            completed_at=run.completed_at,
        )

    def fail_run(
        self,
        run_id: str,
        request: ValidationRequest,
        *,
        reason: str,
    ) -> None:
        self.store.fail_validation_run(
            run_id=run_id,
            completed_at=request.requested_at,
            reason=reason,
        )


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _oos_key(request: ValidationRequest) -> str:
    policy = request.out_of_sample_policy
    payload = "|".join(
        (
            policy.frozen_configuration_hash,
            policy.out_of_sample_start.isoformat(),
            policy.out_of_sample_end.isoformat(),
            request.subject.market.value,
            request.subject.symbol,
        )
    )
    return sha256(payload.encode("utf-8")).hexdigest()


__all__ = ["SQLiteValidationRepository"]
