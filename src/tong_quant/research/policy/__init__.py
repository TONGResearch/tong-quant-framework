from collections.abc import Mapping
from dataclasses import dataclass

from tong_quant.domain.enums import ResearchModuleName
from tong_quant.research.base import evidence_driven_assessment
from tong_quant.research.models import (
    PolicyAssessment,
    ResearchAssessment,
    ResearchContext,
)

POLICY_FIELDS = frozenset(
    {
        "regulatory_environment",
        "industrial_policy",
        "fiscal_policy",
        "monetary_policy",
        "geopolitical_factors",
    }
)


@dataclass(frozen=True, slots=True)
class PolicyResearchModule:
    module: ResearchModuleName = ResearchModuleName.POLICY
    dependencies: frozenset[ResearchModuleName] = frozenset()
    model_version: str = "policy-v0.5"

    def evaluate(
        self,
        context: ResearchContext,
        dependencies: Mapping[ResearchModuleName, ResearchAssessment],
    ) -> PolicyAssessment:
        assessment = evidence_driven_assessment(
            module=self.module,
            context=context,
            required_names=POLICY_FIELDS,
            model_version=self.model_version,
            dependencies=dependencies,
        )
        summaries = {
            name: _summary(context, name)
            for name in POLICY_FIELDS
        }
        return PolicyAssessment(
            assessment=assessment,
            regulatory_environment=summaries["regulatory_environment"],
            industrial_policy=summaries["industrial_policy"],
            fiscal_policy=summaries["fiscal_policy"],
            monetary_policy=summaries["monetary_policy"],
            geopolitical_factors=summaries["geopolitical_factors"],
        )


def _summary(context: ResearchContext, name: str) -> str:
    evidence = context.evidence_named(ResearchModuleName.POLICY, name)
    if evidence is None:
        return "Insufficient point-in-time evidence"
    return str(evidence.metadata.get("summary", evidence.value))


__all__ = ["PolicyResearchModule"]
