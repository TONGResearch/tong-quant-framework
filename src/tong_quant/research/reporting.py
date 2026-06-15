from dataclasses import dataclass
from uuid import uuid4

from tong_quant.domain.enums import ResearchConclusion, ResearchRunStatus
from tong_quant.research.confidence import report_confidence_from_assessments
from tong_quant.research.models import (
    PolicyAssessment,
    ResearchAssessment,
    ResearchReport,
    ResearchRequest,
)
from tong_quant.screening.models import screening_instrument_id


@dataclass(frozen=True, slots=True)
class DefaultResearchReportBuilder:
    model_version: str = "research-report-v0.5"

    def build(
        self,
        request: ResearchRequest,
        assessments: tuple[ResearchAssessment, ...],
        policy_assessment: PolicyAssessment | None,
    ) -> ResearchReport:
        incomplete = any(
            item.conclusion is ResearchConclusion.INSUFFICIENT_DATA
            for item in assessments
        )
        findings = tuple(
            finding
            for assessment in assessments
            for finding in assessment.findings
        )
        risks = tuple(
            risk
            for assessment in assessments
            for risk in assessment.risks
        ) or ("Research uncertainty remains and requires validation",)
        as_of = request.context.as_of
        return ResearchReport(
            report_id=str(uuid4()),
            queue_id=request.context.queue_id,
            instrument_id=screening_instrument_id(
                request.context.queue_entry.candidate.instrument
            ),
            generated_at=as_of,
            available_at=as_of,
            status=(
                ResearchRunStatus.INCOMPLETE
                if incomplete
                else ResearchRunStatus.COMPLETED
            ),
            thesis=request.thesis,
            counter_thesis=request.counter_thesis,
            invalidation_conditions=request.invalidation_conditions,
            assessments=assessments,
            policy_assessment=policy_assessment,
            confidence=report_confidence_from_assessments(assessments),
            key_findings=findings,
            key_risks=risks,
            unresolved_questions=request.unresolved_questions,
            market_regime=request.context.market_regime,
            model_version=self.model_version,
        )


__all__ = ["DefaultResearchReportBuilder"]
