from dataclasses import dataclass, field, replace
from uuid import uuid4

from tong_quant.domain.enums import ResearchConclusion, ResearchRunStatus
from tong_quant.research.conditions import ResearchConditionPolicy, research_condition_features
from tong_quant.research.confidence import report_confidence_from_assessments
from tong_quant.research.models import (
    PolicyAssessment,
    ResearchAssessment,
    ResearchReport,
    ResearchRequest,
)
from tong_quant.research.thesis_bindings import (
    ThesisReportBindingPlan,
    thesis_report_binding_features,
)
from tong_quant.research.timing import require_assessment_cutoff
from tong_quant.screening.models import screening_instrument_id
from tong_quant.version import RESEARCH_REPORT_VERSION, RESEARCH_THESIS_REPORT_VERSION


@dataclass(frozen=True, slots=True)
class DefaultResearchReportBuilder:
    model_version: str = RESEARCH_REPORT_VERSION
    condition_policy: ResearchConditionPolicy = field(default_factory=ResearchConditionPolicy)
    thesis_binding_plan: ThesisReportBindingPlan | None = None

    def __post_init__(self) -> None:
        if self.thesis_binding_plan is not None and self.model_version != RESEARCH_REPORT_VERSION:
            raise ValueError("thesis binding reports require the registered prospective version")

    def build(
        self,
        request: ResearchRequest,
        assessments: tuple[ResearchAssessment, ...],
        policy_assessment: PolicyAssessment | None,
    ) -> ResearchReport:
        request.context.validate()
        require_assessment_cutoff(
            (*assessments, *((policy_assessment.assessment,) if policy_assessment else ())),
            as_of=request.context.as_of,
        )
        thesis_features = None
        if self.thesis_binding_plan is not None:
            self.__post_init__()
            if not assessments:
                raise ValueError("thesis binding reports require module assessments")
            if any(any(name.startswith("thesis_binding_") for name in item.features)
                   for item in (*assessments, *((policy_assessment.assessment,)
                                               if policy_assessment else ()))):
                raise ValueError("thesis binding reports require unannotated module assessments")
            thesis_features = thesis_report_binding_features(self.thesis_binding_plan, request)
        if request.condition_style is not None:
            if not assessments:
                raise ValueError("condition-aware reports require module assessments")
            condition_features = research_condition_features(
                request, assessments, policy=self.condition_policy,
            )
            first = assessments[0]
            assessments = (replace(
                first, features={**first.features, **condition_features},
                findings=(*first.findings, f"Research conditions: "
                          f"{condition_features['condition_review_state']} (not a trade decision)"),
            ), *assessments[1:])
            if (policy_assessment is not None
                    and policy_assessment.assessment.module is first.module):
                policy_assessment = replace(policy_assessment, assessment=assessments[0])
        if thesis_features is not None:
            first = assessments[0]
            assessments = (replace(first, features={**first.features, **thesis_features},
                findings=(*first.findings,
                          "Thesis evidence declarations are not evaluated or source-qualified")),
                *assessments[1:])
            if (policy_assessment is not None
                    and policy_assessment.assessment.module is first.module):
                policy_assessment = replace(policy_assessment, assessment=assessments[0])
        incomplete = thesis_features is not None or any(
            item.conclusion is ResearchConclusion.INSUFFICIENT_DATA
            for item in assessments
        )
        if request.condition_style is not None and (
            assessments[0].features["condition_review_state"] in {"DATA_BLOCKED", "SCREEN_REJECTED"}
        ):
            incomplete = True
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
            unresolved_questions=(*request.unresolved_questions,
                "Thesis source qualification and outcome evaluation remain incomplete")
            if thesis_features is not None else request.unresolved_questions,
            market_regime=request.context.market_regime,
            model_version=RESEARCH_THESIS_REPORT_VERSION if thesis_features is not None
            else self.model_version,
        )


__all__ = ["DefaultResearchReportBuilder"]
