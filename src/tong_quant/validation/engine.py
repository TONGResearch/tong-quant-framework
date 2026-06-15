from dataclasses import dataclass
from uuid import uuid4

from tong_quant.domain.enums import (
    SignalAction,
    SignalStage,
    ValidationModuleName,
)
from tong_quant.domain.models import Signal
from tong_quant.validation.interfaces import (
    ValidationModule,
    ValidationReportBuilder,
    ValidationRepository,
)
from tong_quant.validation.models import ValidationRequest, ValidationRun
from tong_quant.validation.reporting import DefaultValidationReportBuilder
from tong_quant.validation.splits import out_of_sample_split, walk_forward_splits


@dataclass(slots=True)
class ValidationEngine:
    modules: tuple[ValidationModule, ...]
    report_builder: ValidationReportBuilder = DefaultValidationReportBuilder()
    repository: ValidationRepository | None = None

    def __post_init__(self) -> None:
        names = [module.module for module in self.modules]
        if len(names) != len(set(names)):
            raise ValueError("validation modules must have unique names")

    def run(self, request: ValidationRequest) -> ValidationRun:
        run_id = (
            self.repository.start_run(request)
            if self.repository is not None
            else str(uuid4())
        )
        try:
            splits = (
                *walk_forward_splits(
                    request.start_at.date(),
                    request.end_at.date(),
                    request.walk_forward_policy,
                    request.framework_snapshot.configuration_hash,
                ),
                out_of_sample_split(request.out_of_sample_policy),
            )
            by_name = {module.module: module for module in self.modules}
            results = tuple(
                by_name[name].evaluate(request, splits)
                for name in request.modules
                if name in by_name
            )
            missing = set(request.modules) - set(by_name)
            if missing:
                names = ", ".join(sorted(item.value for item in missing))
                raise ValueError(f"validation modules are unavailable: {names}")
            report = self.report_builder.build(request, results, splits)
            run = ValidationRun(
                run_id=run_id,
                request=request,
                report=report,
                signal=_validation_signal(request, report),
                started_at=request.requested_at,
                completed_at=request.requested_at,
            )
            if self.repository is not None:
                self.repository.save_run(run)
            return run
        except Exception as error:
            if self.repository is not None:
                self.repository.fail_run(run_id, request, reason=str(error))
            raise


def _validation_signal(request: ValidationRequest, report: object) -> Signal:
    from tong_quant.validation.models import ValidationReport

    if not isinstance(report, ValidationReport):
        raise TypeError("validation signal requires a ValidationReport")
    confidence = (
        sum(item.confidence for item in report.assessments)
        / len(report.assessments)
        / 100
    )
    return Signal(
        source="validation.engine",
        stage=SignalStage.VALIDATION,
        instrument=request.subject,
        generated_at=report.generated_at,
        effective_at=report.generated_at,
        action=SignalAction.REVIEW,
        strength=confidence,
        reasons=tuple(
            f"{item.module.value}: {item.status.value}"
            for item in report.assessments
        ),
        features={
            "validation_report_id": report.report_id,
            "aggregate_status": report.aggregate_status.value,
            "assessment_count": len(report.assessments),
            "informational_only": True,
            "creates_trade_decision": False,
        },
        model_version=report.model_version,
    )


def default_module_names() -> tuple[ValidationModuleName, ...]:
    return tuple(ValidationModuleName)


__all__ = ["ValidationEngine", "default_module_names"]
