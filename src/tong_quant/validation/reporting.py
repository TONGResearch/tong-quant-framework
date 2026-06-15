from dataclasses import dataclass
from uuid import uuid4

from tong_quant.domain.enums import (
    ValidationRunStatus,
    ValidationStatus,
)
from tong_quant.validation.models import (
    ValidationModuleResult,
    ValidationReport,
    ValidationRequest,
    ValidationSplit,
)

STATUS_PRIORITY = {
    ValidationStatus.RELIABLE: 0,
    ValidationStatus.CONDITIONALLY_RELIABLE: 1,
    ValidationStatus.INCONCLUSIVE: 2,
    ValidationStatus.UNRELIABLE: 3,
    ValidationStatus.FAILED_INTEGRITY_CHECK: 4,
}


@dataclass(frozen=True, slots=True)
class DefaultValidationReportBuilder:
    model_version: str = "validation-engine-v0.6"

    def build(
        self,
        request: ValidationRequest,
        results: tuple[ValidationModuleResult, ...],
        splits: tuple[ValidationSplit, ...],
    ) -> ValidationReport:
        assessments = tuple(result.assessment for result in results)
        aggregate = max(
            (item.status for item in assessments),
            key=STATUS_PRIORITY.__getitem__,
        )
        incomplete = aggregate in {
            ValidationStatus.INCONCLUSIVE,
            ValidationStatus.FAILED_INTEGRITY_CHECK,
        }
        snapshot = request.framework_snapshot
        return ValidationReport(
            report_id=str(uuid4()),
            validation_id=request.validation_id,
            generated_at=request.requested_at,
            status=(
                ValidationRunStatus.INCOMPLETE
                if incomplete
                else ValidationRunStatus.COMPLETED
            ),
            aggregate_status=aggregate,
            assessments=assessments,
            framework_snapshot=snapshot,
            splits=splits,
            factor_contributions=tuple(
                contribution
                for result in results
                for contribution in result.factor_contributions
            ),
            accuracy=next(
                (result.accuracy for result in results if result.accuracy is not None),
                None,
            ),
            decision_summary=next(
                (
                    result.decision_summary
                    for result in results
                    if result.decision_summary is not None
                ),
                None,
            ),
            portfolio_risk=next(
                (
                    result.portfolio_risk
                    for result in results
                    if result.portfolio_risk is not None
                ),
                None,
            ),
            known_limitations=tuple(
                limitation
                for assessment in assessments
                for limitation in assessment.limitations
            ),
            reproducibility_manifest={
                "git_commit": snapshot.git_commit,
                "framework_version": snapshot.framework_version,
                "configuration_hash": snapshot.configuration_hash,
                "research_version": snapshot.research_version,
                "validation_version": snapshot.validation_version,
                "database_schema_version": snapshot.database_schema_version,
            },
            model_version=self.model_version,
        )


__all__ = ["DefaultValidationReportBuilder"]
