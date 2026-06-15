from dataclasses import dataclass

from tong_quant.domain.enums import DecisionDisposition, ValidationModuleName
from tong_quant.validation.base import assessment, sample_confidence
from tong_quant.validation.models import (
    DecisionValidationSummary,
    IntegrityCheck,
    ValidationModuleResult,
    ValidationRequest,
    ValidationSplit,
)


@dataclass(frozen=True, slots=True)
class DecisionJournalValidationModule:
    module: ValidationModuleName = ValidationModuleName.DECISION_JOURNAL
    model_version: str = "decision-journal-v0.6"

    def evaluate(
        self,
        request: ValidationRequest,
        splits: tuple[ValidationSplit, ...],
    ) -> ValidationModuleResult:
        del splits
        matrix = {
            (True, True): 0,
            (True, False): 0,
            (False, True): 0,
            (False, False): 0,
        }
        unresolved = 0
        evaluated = 0
        snapshot_mismatches: list[str] = []
        for sample in request.samples:
            if sample.decision is None or sample.outcome.succeeded is None:
                unresolved += 1
                continue
            if (
                sample.decision.framework_snapshot_hash
                != request.framework_snapshot.configuration_hash
            ):
                snapshot_mismatches.append(sample.decision.decision_id)
            decision_correct = _decision_correct(
                sample.decision.disposition,
                sample.outcome.succeeded,
            )
            if decision_correct is None:
                unresolved += 1
                continue
            research_correct = (
                sample.research_expected_success is sample.outcome.succeeded
            )
            matrix[(research_correct, decision_correct)] += 1
            evaluated += 1
        summary = DecisionValidationSummary(
            research_correct_decision_correct=matrix[(True, True)],
            research_correct_decision_wrong=matrix[(True, False)],
            research_wrong_decision_correct=matrix[(False, True)],
            research_wrong_decision_wrong=matrix[(False, False)],
            unresolved_decisions=unresolved,
        )
        decision_correct_count = matrix[(True, True)] + matrix[(False, True)]
        score = 100 * decision_correct_count / evaluated if evaluated else None
        checks = (
            IntegrityCheck(
                check_id="decision_framework_snapshot",
                passed=not snapshot_mismatches,
                checked_at=request.requested_at,
                reasons=(
                    ("All decisions reference the validation framework snapshot",)
                    if not snapshot_mismatches
                    else (
                        "Snapshot mismatch in decisions: "
                        + ", ".join(snapshot_mismatches),
                    )
                ),
            ),
        )
        return ValidationModuleResult(
            assessment=assessment(
                module=self.module,
                score=score,
                confidence=sample_confidence(
                    evaluated, request.minimum_observations
                ),
                sample_size=evaluated,
                evaluated_at=request.requested_at,
                metrics={
                    "research_correct_decision_correct": matrix[(True, True)],
                    "research_correct_decision_wrong": matrix[(True, False)],
                    "research_wrong_decision_correct": matrix[(False, True)],
                    "research_wrong_decision_wrong": matrix[(False, False)],
                    "unresolved_decisions": unresolved,
                },
                findings=(
                    "Research correctness and decision correctness were tracked independently",
                ),
                risks=(
                    "A correct decision can occur despite incorrect research "
                    "and must not validate the research",
                ),
                limitations=(
                    "Deferred and no-action decisions remain unresolved without "
                    "a registered decision outcome",
                ),
                checks=checks,
                model_version=self.model_version,
            ),
            decision_summary=summary,
        )


def _decision_correct(
    disposition: DecisionDisposition,
    outcome_succeeded: bool,
) -> bool | None:
    if disposition is DecisionDisposition.ADVANCE:
        return outcome_succeeded
    if disposition is DecisionDisposition.REJECT:
        return not outcome_succeeded
    return None


__all__ = ["DecisionJournalValidationModule"]
