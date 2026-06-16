from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, cast
from uuid import uuid4

from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.research.investment import investment_assessment_to_record
from tong_quant.research.models import InvestmentAssessment, ResearchRequest, ResearchRun


@dataclass(slots=True)
class SQLiteResearchRepository:
    store: SQLiteStore
    model_version: str = "research-run-v0.5"

    def start_run(self, request: ResearchRequest) -> str:
        run_id = str(uuid4())
        self.store.start_research_run(
            run_id=run_id,
            queue_id=request.context.queue_id,
            instrument=request.context.queue_entry.candidate.instrument,
            started_at=request.context.as_of,
            researcher=request.researcher,
            modules=tuple(module.value for module in request.modules),
            model_version=self.model_version,
        )
        return run_id

    def save_run(self, run: ResearchRun) -> None:
        all_evidence = {
            evidence.evidence_id: evidence
            for evidence in (
                *run.request.context.evidence,
                *(
                    evidence
                    for assessment in run.report.assessments
                    for evidence in assessment.evidence
                ),
            )
        }
        for evidence in all_evidence.values():
            self.store.save_research_evidence(
                run_id=run.run_id,
                evidence_id=evidence.evidence_id,
                module=evidence.module.value,
                name=evidence.name,
                value=evidence.value,
                observed_at=evidence.observed_at,
                available_at=evidence.available_at,
                source=evidence.source,
                quality=evidence.quality.value,
                source_reference=evidence.source_reference,
                calculation_version=evidence.calculation_version,
                input_hash=evidence.input_hash,
                metadata=dict(evidence.metadata),
            )
        report = run.report
        self.store.save_research_report(
            run_id=run.run_id,
            report_id=report.report_id,
            queue_id=report.queue_id,
            instrument_id_value=report.instrument_id,
            generated_at=report.generated_at,
            available_at=report.available_at,
            status=report.status,
            thesis=report.thesis,
            counter_thesis=report.counter_thesis,
            invalidation_conditions=[
                _jsonable(asdict(condition))
                for condition in report.invalidation_conditions
            ],
            confidence=_jsonable(asdict(report.confidence)),
            key_findings=report.key_findings,
            key_risks=report.key_risks,
            unresolved_questions=report.unresolved_questions,
            policy_assessment=(
                None
                if report.policy_assessment is None
                else _jsonable(asdict(report.policy_assessment))
            ),
            market_regime=(
                None
                if report.market_regime is None
                else _jsonable(asdict(report.market_regime))
            ),
            model_version=report.model_version,
        )
        for assessment in report.assessments:
            self.store.save_research_assessment(
                run_id=run.run_id,
                report_id=report.report_id,
                module=assessment.module.value,
                conclusion=assessment.conclusion.value,
                score=assessment.score,
                confidence=_jsonable(asdict(assessment.confidence)),
                evaluated_at=assessment.evaluated_at,
                available_at=assessment.available_at,
                findings=assessment.findings,
                risks=assessment.risks,
                limitations=assessment.limitations,
                evidence_ids=assessment.evidence_ids,
                features=_jsonable(assessment.features),
                model_version=assessment.model_version,
            )
        self.store.save_signal(run.signal)
        self.store.complete_research_run(
            run_id=run.run_id,
            queue_id=report.queue_id,
            status=run.status,
            completed_at=run.completed_at,
        )

    def fail_run(
        self,
        run_id: str,
        request: ResearchRequest,
        *,
        reason: str,
    ) -> None:
        self.store.fail_research_run(
            run_id=run_id,
            queue_id=request.context.queue_id,
            completed_at=request.context.as_of,
            reason=reason,
        )


@dataclass(slots=True)
class SQLiteInvestmentAssessmentRepository:
    store: SQLiteStore

    def save_assessment(self, assessment: InvestmentAssessment) -> str:
        record = investment_assessment_to_record(assessment)
        return self.store.save_investment_assessment(
            report_id=str(record["report_id"]),
            instrument_id_value=str(record["instrument_id"]),
            status=assessment.status,
            assessed_at=assessment.assessed_at,
            score=cast(float | None, record["score"]),
            confidence=cast(float | None, record["confidence"]),
            components=cast(list[dict[str, object]], record["components"]),
            reasons=assessment.reasons,
            limitations=assessment.limitations,
            market_regime=cast(dict[str, object] | None, record["market_regime"]),
            model_version=assessment.model_version,
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


__all__ = ["SQLiteInvestmentAssessmentRepository", "SQLiteResearchRepository"]
