from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC

from tong_quant.domain.enums import ResearchModuleName
from tong_quant.research.base import evidence_driven_assessment
from tong_quant.research.models import ResearchAssessment, ResearchContext
from tong_quant.version import FINANCIAL_RESEARCH_VERSION

FINANCIAL_FIELDS = frozenset(
    {"revenue", "profit", "cash_flow", "debt", "roe", "roic"}
)


@dataclass(frozen=True, slots=True)
class FinancialResearchModule:
    module: ResearchModuleName = ResearchModuleName.FINANCIAL
    dependencies: frozenset[ResearchModuleName] = frozenset()
    model_version: str = FINANCIAL_RESEARCH_VERSION

    def evaluate(
        self,
        context: ResearchContext,
        dependencies: Mapping[ResearchModuleName, ResearchAssessment],
    ) -> ResearchAssessment:
        context.validate()
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
        latest = {
            metric: max(
                facts,
                key=lambda fact: (
                    fact.period_end, fact.available_at, fact.revision, fact.published_at,
                    str(fact.value),
                ),
            )
            for metric, facts in sorted(context.fundamentals.items()) if facts
        }
        latest_values = {}
        for metric, fact in latest.items():
            latest_values.update({
                f"latest_{metric}": str(fact.value),
                f"latest_{metric}_period_end": fact.period_end.isoformat(),
                f"latest_{metric}_available_at": fact.available_at.astimezone(UTC).isoformat(),
                f"latest_{metric}_unit": fact.unit,
                f"latest_{metric}_currency": fact.currency,
                f"latest_{metric}_trust_level": fact.trust_level.value,
                f"latest_{metric}_availability_precision": fact.availability_precision.value,
            })
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
            available_at=max((
                base.available_at,
                *(fact.available_at for facts in context.fundamentals.values() for fact in facts),
            )),
            findings=tuple(findings),
            risks=tuple(risks),
            limitations=(
                *base.limitations,
                "No detected restatement is not proof of complete revision history; "
                "displayed fundamental values do not certify accounting semantics or trust",
            ),
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
