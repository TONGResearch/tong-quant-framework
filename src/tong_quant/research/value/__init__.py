from collections.abc import Mapping
from dataclasses import dataclass

from tong_quant.domain.enums import ResearchModuleName
from tong_quant.research.base import evidence_driven_assessment
from tong_quant.research.models import ResearchAssessment, ResearchContext
from tong_quant.version import VALUE_RESEARCH_VERSION

VALUE_FIELDS = frozenset({"survival", "cycle", "valuation", "growth"})


@dataclass(frozen=True, slots=True)
class ValueResearchModule:
    module: ResearchModuleName = ResearchModuleName.VALUE
    dependencies: frozenset[ResearchModuleName] = frozenset(
        {
            ResearchModuleName.POLICY,
            ResearchModuleName.FINANCIAL,
            ResearchModuleName.INDUSTRY,
        }
    )
    model_version: str = VALUE_RESEARCH_VERSION

    def evaluate(
        self,
        context: ResearchContext,
        dependencies: Mapping[ResearchModuleName, ResearchAssessment],
    ) -> ResearchAssessment:
        return evidence_driven_assessment(
            module=self.module,
            context=context,
            required_names=VALUE_FIELDS,
            model_version=self.model_version,
            dependencies=dependencies,
        )


__all__ = ["ValueResearchModule"]
