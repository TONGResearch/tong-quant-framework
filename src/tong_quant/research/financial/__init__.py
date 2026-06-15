from collections.abc import Mapping
from dataclasses import dataclass

from tong_quant.domain.enums import ResearchModuleName
from tong_quant.research.base import evidence_driven_assessment
from tong_quant.research.models import ResearchAssessment, ResearchContext

FINANCIAL_FIELDS = frozenset(
    {"revenue", "profit", "cash_flow", "debt", "roe", "roic"}
)


@dataclass(frozen=True, slots=True)
class FinancialResearchModule:
    module: ResearchModuleName = ResearchModuleName.FINANCIAL
    dependencies: frozenset[ResearchModuleName] = frozenset()
    model_version: str = "financial-v0.5"

    def evaluate(
        self,
        context: ResearchContext,
        dependencies: Mapping[ResearchModuleName, ResearchAssessment],
    ) -> ResearchAssessment:
        base = evidence_driven_assessment(
            module=self.module,
            context=context,
            required_names=FINANCIAL_FIELDS,
            model_version=self.model_version,
            dependencies=dependencies,
        )
        restated_metrics = tuple(
            metric
            for metric, facts in context.fundamentals.items()
            if any(fact.revision > 0 for fact in facts)
        )
        latest_values = {
            f"latest_{metric}": str(facts[-1].value)
            for metric, facts in context.fundamentals.items()
            if facts
        }
        findings = list(base.findings)
        risks = list(base.risks)
        if restated_metrics:
            findings.append(
                f"Restatement history detected for: {', '.join(sorted(restated_metrics))}"
            )
            risks.append("Historical financial statements include restated values")
        else:
            findings.append("No visible restatement was detected in supplied history")
        return ResearchAssessment(
            module=base.module,
            conclusion=base.conclusion,
            score=base.score,
            confidence=base.confidence,
            evaluated_at=base.evaluated_at,
            available_at=base.available_at,
            findings=tuple(findings),
            risks=tuple(risks),
            limitations=base.limitations,
            evidence_ids=base.evidence_ids,
            model_version=base.model_version,
            features={
                **base.features,
                **latest_values,
                "restatement_detected": bool(restated_metrics),
                "restated_metrics": ",".join(sorted(restated_metrics)),
            },
            evidence=base.evidence,
        )


__all__ = ["FinancialResearchModule"]
