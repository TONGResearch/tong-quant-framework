from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC

from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.domain.enums import Market, ResearchModuleName
from tong_quant.research.base import insufficient_assessment
from tong_quant.research.financial.comparisons import financial_comparisons
from tong_quant.research.financial.document_bank import (
    BankDocumentInputPlan,
    bank_document_input_coverage,
)
from tong_quant.research.financial.document_freshness import (
    DocumentFreshnessPolicy,
    review_document_freshness,
)
from tong_quant.research.financial.inputs import BankInputPolicy, assess_bank_inputs
from tong_quant.research.financial.market_value import (
    MarketValueMatchingPolicy,
    market_value_diagnostics,
)
from tong_quant.research.financial.native_pairs import review_income_changes
from tong_quant.research.financial.native_review import review_native_financials
from tong_quant.research.financial.nonfinancial import (
    NonfinancialDiagnosticStatus,
    nonfinancial_diagnostics,
)
from tong_quant.research.financial.nonfinancial_inputs import (
    NonfinancialInputPolicy,
    assess_nonfinancial_inputs,
)
from tong_quant.research.financial.ratio_arithmetic import (
    RatioArithmeticPlan,
    review_ratio_arithmetic,
)
from tong_quant.research.financial.ratio_questions import review_ratio_questions
from tong_quant.research.financial.trailing import (
    TrailingEditionReview,
    trailing_financial_diagnostics,
)
from tong_quant.research.financial.valuation import valuation_basis_diagnostics
from tong_quant.research.models import ResearchAssessment, ResearchContext, ResearchValue
from tong_quant.version import FINANCIAL_RESEARCH_VERSION

FINANCIAL_FIELDS = frozenset(
    {"revenue", "profit", "cash_flow", "debt", "roe", "roic"}
)


@dataclass(frozen=True, slots=True)
class FinancialResearchModule:
    module: ResearchModuleName = ResearchModuleName.FINANCIAL
    dependencies: frozenset[ResearchModuleName] = frozenset()
    model_version: str = FINANCIAL_RESEARCH_VERSION
    bank_input_policy: BankInputPolicy = field(default_factory=BankInputPolicy)
    trailing_edition_reviews: tuple[TrailingEditionReview, ...] = ()
    market_value_policy: MarketValueMatchingPolicy = field(
        default_factory=MarketValueMatchingPolicy)
    nonfinancial_input_policy: NonfinancialInputPolicy = field(
        default_factory=NonfinancialInputPolicy)
    bank_document_input_plan: BankDocumentInputPlan | None = None
    manual_income_change_pairs: tuple[str, ...] = ()
    manual_ratio_row_keys: tuple[str, ...] = ()
    ratio_arithmetic_plan: RatioArithmeticPlan | None = None
    document_freshness_policy: DocumentFreshnessPolicy = field(
        default_factory=DocumentFreshnessPolicy)

    def evaluate(
        self,
        context: ResearchContext,
        dependencies: Mapping[ResearchModuleName, ResearchAssessment],
    ) -> ResearchAssessment:
        context.validate()
        if self.ratio_arithmetic_plan is not None and (
            context.reviewed_document_inputs is None or context.reviewed_ratio_inputs is None
        ):
            raise ValueError("ratio arithmetic requires both monetary and ratio receipts")
        if self.manual_ratio_row_keys and context.reviewed_ratio_inputs is None:
            raise ValueError("configured ratio questions require a reviewed ratio receipt")
        if context.reviewed_document_inputs is None and (
            self.bank_document_input_plan is not None or self.manual_income_change_pairs
        ):
            raise ValueError("configured manual financial diagnostics require a reviewed receipt")
        # No financial scoring policy is admitted yet, including evidence-only inputs.
        base = insufficient_assessment(
            module=self.module, evidence=(), required_names=FINANCIAL_FIELDS,
            as_of=context.as_of, model_version=self.model_version,
            limitations=(
                "No source-bound sector financial scoring policy has been admitted; "
                "facts, receipts and numeric evidence remain diagnostic, not scoring authority",
            ),
        )
        base = replace(
            base, confidence=replace(base.confidence, confidence=0.0),
            available_at=max((
                *(item.available_at for item in context.evidence_for(self.module)),
                *(fact.available_at for facts in context.fundamentals.values()
                  for fact in facts),
            ), default=context.as_of, key=lambda value: value.astimezone(UTC)),
            evidence=context.evidence_for(self.module),
            evidence_ids=tuple(item.evidence_id for item in context.evidence_for(self.module)),
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
                    fact.period_end, fact.available_at.astimezone(UTC), fact.revision,
                    fact.published_at.astimezone(UTC),
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
        input_features: dict[str, ResearchValue] = {}
        if context.financial_inputs is not None:
            inputs = context.financial_inputs
            input_features.update({
                "financial_input_hash": inputs.input_hash,
                "source_binding_complete": inputs.source_binding_complete,
                "missing_financial_metrics": ",".join(inputs.missing_metrics),
                "financial_sector_profile": inputs.sector_profile,
                "financial_reporting_scope": inputs.reporting_scope,
            })
            if inputs.sector_profile == "bank":
                input_features["bank_scoring_policy_qualified"] = False
                risks.append("Bank-specific financial scoring policy has not been qualified")
                if inputs.market is Market.CHINA_A:
                    bank = assess_bank_inputs(inputs, self.bank_input_policy)
                    input_features.update({
                        "bank_input_assessment_hash": str(bank.document()["assessment_hash"]),
                        "bank_input_policy_hash": bank.policy_hash,
                        "bank_target_period_basis": bank.target_period_basis,
                        "bank_input_missing_metrics": ",".join(
                            check.metric for check in bank.checks
                            if check.status.value == "missing"),
                    })
                    for check in bank.checks:
                        input_features.update({
                            f"bank_{check.metric}_input_status": check.status.value,
                            f"bank_{check.metric}_freshness": check.freshness.value,
                            f"bank_{check.metric}_report_age_days": check.report_age_days,
                        })
                    risks.append("Bank input/freshness diagnostics do not qualify research")
                else:
                    input_features["bank_input_policy_scope"] = "unsupported_market"
            if inputs.market is Market.CHINA_A and inputs.sector_profile == "nonfinancial":
                checklist = assess_nonfinancial_inputs(inputs, self.nonfinancial_input_policy)
                input_features.update({
                    "nonfinancial_input_assessment_hash": str(checklist["assessment_hash"]),
                    "nonfinancial_input_policy_hash": str(checklist["policy_hash"]),
                    "nonfinancial_input_assessment_json": financial_input_json(checklist),
                })
                for diagnostic in nonfinancial_diagnostics(inputs):
                    prefix = f"nonfinancial_{diagnostic.name}"
                    input_features.update({
                        f"{prefix}_status": diagnostic.status.value,
                        f"{prefix}_value": (str(diagnostic.value)
                                            if diagnostic.value is not None else None),
                        f"{prefix}_unit": diagnostic.unit,
                        f"{prefix}_hash": str(diagnostic.document()["diagnostic_hash"]),
                    })
                    if diagnostic.status is NonfinancialDiagnosticStatus.INCONSISTENT:
                        risks.append(f"Nonfinancial arithmetic inconsistency: {diagnostic.name}")
                risks.append("Cash/balance diagnostics are not debt clearance or financial scoring")
                for basis in valuation_basis_diagnostics(inputs):
                    prefix = f"valuation_{basis.name}"
                    input_features.update({
                        f"{prefix}_status": basis.status.value,
                        f"{prefix}_hash": str(basis.document()["diagnostic_hash"]),
                    })
                risks.append("Valuation denominators do not qualify valuation or financial scores")
                for trailing in trailing_financial_diagnostics(
                    inputs, self.trailing_edition_reviews,
                ):
                    prefix = f"trailing_{trailing.metric}"
                    input_features.update({
                        f"{prefix}_status": trailing.status.value,
                        f"{prefix}_value": (str(trailing.value)
                                             if trailing.value is not None else None),
                        f"{prefix}_review_hash": trailing.review_hash,
                        f"{prefix}_hash": str(trailing.document()["diagnostic_hash"]),
                    })
                risks.append(
                    "Trailing arithmetic does not qualify valuation, comparability or scoring")
            for comparison in financial_comparisons(inputs):
                prefix = f"{comparison.metric}_descriptive_comparison"
                input_features.update({
                    f"{prefix}_kind": comparison.kind,
                    f"{prefix}_status": comparison.status.value,
                    f"{prefix}_amount_change": (
                        str(comparison.amount_change) if comparison.amount_change is not None
                        else None
                    ),
                    f"{prefix}_percent": (
                        str(comparison.change_percent) if comparison.change_percent is not None
                        else None
                    ),
                    f"{prefix}_hash": str(comparison.document()["comparison_hash"]),
                })
            for entry in inputs.inspections:
                # These are period-tagged diagnostics, not eligibility or trade signals.
                if latest.get(entry.fact.metric) != entry.fact:
                    continue
                prefix = f"latest_{entry.fact.metric}"
                input_features.update({
                    f"{prefix}_source_binding": entry.status.value,
                    f"{prefix}_reporting_scope": entry.reporting_scope,
                    f"{prefix}_sector_profile": entry.sector_profile,
                    f"{prefix}_audit_status": entry.audit_status,
                    f"{prefix}_filing_sha256": entry.filing_sha256,
                    f"{prefix}_measurement_basis": entry.measurement_basis,
                })
        if context.market_value_inputs is not None:
            matching = market_value_diagnostics(
                context.market_value_inputs, context.bars, self.market_value_policy)
            input_features.update({
                "market_value_input_hash": context.market_value_inputs.input_hash,
                "market_value_diagnostic_hash": str(matching["diagnostic_hash"]),
                "market_value_bar_input_hash": str(matching["bar_input_hash"]),
                "market_value_policy_hash": str(matching["matching_policy_hash"]),
                "market_value_matching_json": financial_input_json(matching),
                "market_value_status": str(matching["status"]),
                "market_value_freshness": str(matching["freshness"]),
                "market_value_bar_status": str(matching["bar_status"]),
                "market_value_arithmetic_consistency": str(matching["arithmetic_consistency"]),
                "market_value_evidence_id": str(matching.get("evidence_id") or ""),
                "market_value_quote_freshness": str(matching["quote_freshness"]),
                "market_value_capture_freshness": str(matching["capture_freshness"]),
                "market_value_bar_freshness": str(matching["bar_freshness"]),
                "market_value_valuation_authorized": False,
            })
            risks.append("Market-value matching and age limits do not qualify financial scoring")
        input_features["financial_scoring_authorized"] = False
        input_features["sec_period_input_present"] = context.sec_period_inputs is not None
        if context.sec_period_inputs is not None:
            sec = context.sec_period_inputs
            receipt = sec.document()
            input_features.update({
                "sec_period_binding_hash": sec.binding_hash,
                "sec_period_binding_version": sec.model_version,
                "sec_period_input_hash": str(receipt["input_hash"]),
                "sec_period_receipt_json": sec.receipt_json,
                "sec_period_source_input_hash": str(receipt["source_input_hash"]),
                "sec_period_source_status": str(receipt["source_status"]),
                "sec_period_status": str(receipt["status"]),
                "sec_period_requested_symbol": sec.symbol,
                "sec_period_requested_sector": sec.sector_profile,
                "sec_period_check_count": len(receipt["checks"]),
                "sec_period_unsupported_fact_count": receipt["unsupported_fact_occurrence_count"],
                "sec_period_sector_policy": "NOT_ADMITTED",
                "sec_period_issuer_to_instrument_verified": False,
                "sec_period_scoring_authorized": False,
            })
            findings.append("Exact SEC contexts retained without accounting/sector admission")
            risks.extend((
                "SEC period receipt binding is not independent source/equity-identity verification",
                "Unresolved contexts, fiscal/consolidation/revision definitions remain unqualified",
            ))
        input_features["native_financial_input_present"] = (
            context.native_financial_inputs is not None)
        if context.native_financial_inputs is not None:
            native = context.native_financial_inputs
            receipt = native.document()
            review = review_native_financials(
                receipt, subject=context.queue_entry.candidate.instrument.symbol,
                market=context.queue_entry.candidate.instrument.market, as_of=context.as_of,
                sector_profile=native.sector_profile,
            )
            input_features.update({
                "native_financial_input_hash": str(receipt["input_hash"]),
                "native_financial_receipt_json": native.receipt_json,
                "native_financial_review_json": financial_input_json(review),
                "native_financial_review_hash": str(review["review_hash"]),
                "native_financial_source_status": str(receipt["status"]),
                "native_financial_source_bound": receipt["source_bound"] is True,
                "native_financial_review_status": str(review["status"]),
                "native_financial_requested_sector": native.sector_profile,
                "native_financial_sector_policy": "NOT_ADMITTED",
                "native_financial_trust_ceiling": "LOW",
                "native_financial_availability_precision": "retrieval_time",
            })
            findings.append("Native financial capture status retained as unqualified context")
            risks.extend((
                "Native receipt binding is not independent authentication or PIT qualification",
                "Native periods, publication history and sector accounting remain unqualified",
            ))
        input_features["financial_input_binding_present"] = context.financial_inputs is not None
        if context.reviewed_document_inputs is not None:
            reviewed = context.reviewed_document_inputs
            receipt = reviewed.document()
            input_features.update({
                "reviewed_document_input_hash": str(receipt["input_hash"]),
                "reviewed_document_receipt_json": reviewed.receipt_json,
                "reviewed_document_status": str(receipt["status"]),
                "reviewed_document_source_bound": receipt["source_bound"] is True,
                "reviewed_document_requested_sector": reviewed.sector_profile,
                "reviewed_document_sector_policy": "NOT_ADMITTED",
                "reviewed_document_row_count": len(receipt["observations"]),
                "reviewed_document_trust_ceiling": "LOW",
                "reviewed_document_availability_precision": "retrieval_time",
                "reviewed_document_scoring_authorized": False,
            })
            findings.append("Manual filing observations retained as unqualified context")
            risks.extend((
                "Manual annotations and source pins do not establish independent accounting truth",
                "Requested sector, publication, revisions and sector policy remain unqualified",
            ))
            if self.bank_document_input_plan is not None:
                coverage = bank_document_input_coverage(reviewed, self.bank_document_input_plan)
                input_features.update({
                    "bank_document_plan_hash": self.bank_document_input_plan.plan_hash,
                    "bank_document_input_status": str(coverage["status"]),
                    "bank_document_assessment_hash": str(coverage["assessment_hash"]),
                    "bank_document_input_json": financial_input_json(coverage),
                })
            if self.manual_income_change_pairs:
                changes = review_income_changes(reviewed, pairs=self.manual_income_change_pairs)
                input_features.update({"manual_income_changes_hash": str(changes["review_hash"]),
                    "manual_income_changes_json": financial_input_json(changes)})
        if context.reviewed_ratio_inputs is not None:
            ratios = context.reviewed_ratio_inputs
            receipt = ratios.document()
            input_features.update({
                "reviewed_ratio_input_hash": str(receipt["input_hash"]),
                "reviewed_ratio_receipt_json": ratios.receipt_json,
                "reviewed_ratio_status": str(receipt["status"]),
                "reviewed_ratio_source_bound": receipt["source_bound"] is True,
                "reviewed_ratio_requested_sector": ratios.sector_profile,
                "reviewed_ratio_sector_policy": "NOT_ADMITTED",
                "reviewed_ratio_row_count": len(receipt["observations"]),
                "reviewed_ratio_trust_ceiling": "LOW",
                "reviewed_ratio_availability_precision": "retrieval_time",
                "reviewed_ratio_scoring_authorized": False,
            })
            if self.manual_ratio_row_keys:
                questions = review_ratio_questions(ratios, row_keys=self.manual_ratio_row_keys)
                input_features.update({
                    "reviewed_ratio_questions_json": financial_input_json(questions),
                    "reviewed_ratio_questions_hash": str(questions["review_hash"]),
                })
            findings.append("Original percentage evidence retained without metric equivalence")
            risks.extend((
                "Original percentages do not qualify definitions, denominators or regulatory scope",
                "Ratio receipt binding is not independent verification, source or sector admission",
            ))
        if (self.ratio_arithmetic_plan is not None and context.reviewed_document_inputs is not None
                and context.reviewed_ratio_inputs is not None):
            arithmetic = review_ratio_arithmetic(context.reviewed_document_inputs,
                context.reviewed_ratio_inputs, self.ratio_arithmetic_plan)
            input_features.update({
                "ratio_arithmetic_plan_hash": self.ratio_arithmetic_plan.plan_hash,
                "ratio_arithmetic_json": financial_input_json(arithmetic),
                "ratio_arithmetic_hash": str(arithmetic["review_hash"]),
            })
            risks.append("Ratio arithmetic agreement does not qualify formula, scope or rounding")
        if context.supplemental_ratio_inputs:
            # Preserve document boundaries; primary questions/equations never search supplements.
            receipts = sorted(
                (snapshot.document() for snapshot in context.supplemental_ratio_inputs),
                key=lambda receipt: str(receipt["document_url"]))
            input_features.update({
                "supplemental_ratio_receipts_json": financial_input_json(receipts),
                "supplemental_ratio_document_count": len(receipts),
                "supplemental_ratio_requested_sector": context.supplemental_ratio_inputs[
                    0].sector_profile,
                "supplemental_ratio_sector_policy": "NOT_ADMITTED",
                "supplemental_ratio_aggregation_authorized": False,
                "supplemental_ratio_scoring_authorized": False,
            })
            findings.append("Separate original ratio documents retained without merging metrics")
            risks.extend((
                "Supplemental document periods, definitions and regulatory perimeters may differ",
                "Supplemental evidence cannot fill primary gaps or qualify financial scoring",
            ))
        reviewed_inputs = (
            *((context.reviewed_document_inputs,) if context.reviewed_document_inputs else ()),
            *((context.reviewed_ratio_inputs,) if context.reviewed_ratio_inputs else ()),
            *sorted(context.supplemental_ratio_inputs,
                    key=lambda snapshot: str(snapshot.document()["document_url"])),
        )
        if reviewed_inputs:
            freshness = [review_document_freshness(snapshot, self.document_freshness_policy)
                         for snapshot in reviewed_inputs]
            input_features.update({
                "reviewed_source_freshness_json": financial_input_json(freshness),
                "reviewed_source_freshness_policy_hash": self.document_freshness_policy.policy_hash,
            })
            risks.append("Document ages cannot prove latest filings, source quality or scoring")
        risks.append("No admitted financial scoring policy; supplied annotations are not scores")
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
                *((context.financial_inputs.as_of,) if context.financial_inputs else ()),
                *((context.market_value_inputs.as_of,) if context.market_value_inputs else ()),
                # Receipt observations and failure states are known only at their read cutoff.
                *(snapshot.as_of for snapshot in (context.native_financial_inputs,
                    context.reviewed_document_inputs, context.reviewed_ratio_inputs,
                    context.sec_period_inputs,
                    *context.supplemental_ratio_inputs)
                    if snapshot is not None),
                *(fact.available_at for facts in context.fundamentals.values() for fact in facts),
            ), key=lambda value: value.astimezone(UTC)),
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
                **input_features,
                "restatement_detected": bool(restated_metrics),
                "restated_metrics": ",".join(sorted(restated_metrics)),
            },
            evidence=base.evidence,
        )


__all__ = ["FinancialResearchModule"]
