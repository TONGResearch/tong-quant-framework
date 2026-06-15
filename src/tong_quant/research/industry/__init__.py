from collections.abc import Mapping
from dataclasses import dataclass

from tong_quant.domain.enums import ResearchModuleName
from tong_quant.research.base import evidence_driven_assessment
from tong_quant.research.models import ResearchAssessment, ResearchContext

INDUSTRY_FIELDS = frozenset(
    {
        "industry_trend",
        "industry_heat",
        "industry_cycle",
        "relative_strength",
    }
)


@dataclass(frozen=True, slots=True)
class IndustryResearchModule:
    module: ResearchModuleName = ResearchModuleName.INDUSTRY
    dependencies: frozenset[ResearchModuleName] = frozenset(
        {ResearchModuleName.POLICY}
    )
    model_version: str = "industry-v0.5"

    def evaluate(
        self,
        context: ResearchContext,
        dependencies: Mapping[ResearchModuleName, ResearchAssessment],
    ) -> ResearchAssessment:
        return evidence_driven_assessment(
            module=self.module,
            context=context,
            required_names=INDUSTRY_FIELDS,
            model_version=self.model_version,
            dependencies=dependencies,
        )


__all__ = ["IndustryResearchModule"]
