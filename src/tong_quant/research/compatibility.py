from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from tong_quant.domain.enums import ResearchRunStatus
from tong_quant.research.confidence import report_confidence_from_assessments
from tong_quant.research.models import (
    PolicyAssessment,
    ResearchAssessment,
    ResearchReport,
    ThesisInvalidationCondition,
)


@dataclass(frozen=True, slots=True)
class LegacyResearchOutcomeRecord:
    queue_id: str
    instrument_id: str
    completed_at: datetime
    available_at: datetime
    thesis: str
    risks: tuple[str, ...]
    confidence_score: float
    model_version: str = "legacy-screening-research-outcome"


AssessmentMapper = Callable[[LegacyResearchOutcomeRecord], tuple[ResearchAssessment, ...]]


@dataclass(frozen=True, slots=True)
class LegacyResearchOutcomeAdapter:
    assessment_mapper: AssessmentMapper
    model_version: str = "legacy-research-outcome-adapter-v0.6.1"

    def to_research_report(
        self,
        record: LegacyResearchOutcomeRecord,
        *,
        report_id: str,
        counter_thesis: str,
        invalidation_conditions: tuple[ThesisInvalidationCondition, ...],
        unresolved_questions: tuple[str, ...] = (),
        policy_assessment: PolicyAssessment | None = None,
    ) -> ResearchReport:
        if not counter_thesis.strip():
            raise ValueError("legacy migration requires an explicit counter thesis")
        if not invalidation_conditions:
            raise ValueError("legacy migration requires thesis invalidation conditions")
        assessments = self.assessment_mapper(record)
        if not assessments:
            raise ValueError("legacy migration requires mapped ResearchAssessment records")
        findings = tuple(
            finding
            for assessment in assessments
            for finding in assessment.findings
        )
        risks = tuple(
            risk
            for assessment in assessments
            for risk in assessment.risks
        ) or record.risks or ("Legacy research risk requires review",)
        return ResearchReport(
            report_id=report_id,
            queue_id=record.queue_id,
            instrument_id=record.instrument_id,
            generated_at=record.completed_at,
            available_at=record.available_at,
            status=ResearchRunStatus.COMPLETED,
            thesis=record.thesis,
            counter_thesis=counter_thesis,
            invalidation_conditions=invalidation_conditions,
            assessments=assessments,
            policy_assessment=policy_assessment,
            confidence=report_confidence_from_assessments(assessments),
            key_findings=findings,
            key_risks=risks,
            unresolved_questions=unresolved_questions,
            market_regime=None,
            model_version=self.model_version,
        )


__all__ = [
    "LegacyResearchOutcomeAdapter",
    "LegacyResearchOutcomeRecord",
]
