from collections.abc import Iterable
from dataclasses import dataclass
from uuid import uuid4

from tong_quant.domain.enums import (
    ResearchModuleName,
    SignalAction,
    SignalStage,
)
from tong_quant.domain.models import Signal
from tong_quant.research.interfaces import (
    ResearchModule,
    ResearchReportBuilder,
    ResearchRepository,
)
from tong_quant.research.models import (
    PolicyAssessment,
    ResearchAssessment,
    ResearchRequest,
    ResearchRun,
)
from tong_quant.research.reporting import DefaultResearchReportBuilder


@dataclass(slots=True)
class ResearchEngine:
    modules: tuple[ResearchModule, ...]
    report_builder: ResearchReportBuilder = DefaultResearchReportBuilder()
    repository: ResearchRepository | None = None

    def __post_init__(self) -> None:
        names = [module.module for module in self.modules]
        if len(names) != len(set(names)):
            raise ValueError("research modules must have unique names")
        available = set(names)
        missing = {
            dependency
            for module in self.modules
            for dependency in module.dependencies
            if dependency not in available
        }
        if missing:
            joined = ", ".join(sorted(item.value for item in missing))
            raise ValueError(f"research module dependencies are missing: {joined}")

    def run(self, request: ResearchRequest) -> ResearchRun:
        run_id = (
            self.repository.start_run(request)
            if self.repository is not None
            else str(uuid4())
        )
        try:
            selected = self._resolve_modules(request.modules)
            completed: dict[ResearchModuleName, ResearchAssessment] = {}
            assessments: list[ResearchAssessment] = []
            policy_assessment: PolicyAssessment | None = None
            for module in selected:
                dependencies = {name: completed[name] for name in module.dependencies}
                output = module.evaluate(request.context, dependencies)
                if isinstance(output, PolicyAssessment):
                    policy_assessment = output
                    assessment = output.assessment
                else:
                    assessment = output
                completed[module.module] = assessment
                assessments.append(assessment)

            report = self.report_builder.build(
                request,
                tuple(assessments),
                policy_assessment,
            )
            signal = _research_signal(request, report)
            run = ResearchRun(
                run_id=run_id,
                request=request,
                status=report.status,
                started_at=request.context.as_of,
                completed_at=request.context.as_of,
                report=report,
                signal=signal,
            )
            if self.repository is not None:
                self.repository.save_run(run)
            return run
        except Exception as error:
            if self.repository is not None:
                self.repository.fail_run(run_id, request, reason=str(error))
            raise

    def _resolve_modules(
        self,
        requested: Iterable[ResearchModuleName],
    ) -> tuple[ResearchModule, ...]:
        by_name = {module.module: module for module in self.modules}
        ordered: list[ResearchModule] = []
        visiting: set[ResearchModuleName] = set()
        visited: set[ResearchModuleName] = set()

        def visit(name: ResearchModuleName) -> None:
            if name in visiting:
                raise ValueError(f"cyclic research dependency at {name.value}")
            if name in visited:
                return
            module = by_name.get(name)
            if module is None:
                raise ValueError(f"research module is unavailable: {name.value}")
            visiting.add(name)
            for dependency in sorted(module.dependencies, key=lambda item: item.value):
                visit(dependency)
            visiting.remove(name)
            visited.add(name)
            ordered.append(module)

        for name in requested:
            visit(name)
        return tuple(ordered)


def _research_signal(request: ResearchRequest, report: object) -> Signal:
    from tong_quant.research.models import ResearchReport

    if not isinstance(report, ResearchReport):
        raise TypeError("research signal requires a ResearchReport")
    regime = report.market_regime
    return Signal(
        source="research.engine",
        stage=SignalStage.RESEARCH,
        instrument=request.context.queue_entry.candidate.instrument,
        generated_at=report.generated_at,
        effective_at=report.generated_at,
        action=SignalAction.RESEARCH,
        strength=report.confidence.confidence / 100,
        reasons=report.key_findings[:5],
        features={
            "report_id": report.report_id,
            "report_status": report.status.value,
            "module_count": len(report.assessments),
            "market_regime": None if regime is None else regime.state.value,
            "informational_only": True,
        },
        invalidations=tuple(
            condition.description for condition in report.invalidation_conditions
        ),
        model_version=report.model_version,
    )


__all__ = ["ResearchEngine"]
