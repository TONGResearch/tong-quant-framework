from collections.abc import Mapping
from typing import Protocol

from tong_quant.domain.enums import ResearchModuleName
from tong_quant.research.models import (
    PolicyAssessment,
    ResearchAssessment,
    ResearchContext,
    ResearchReport,
    ResearchRequest,
    ResearchRun,
)

ModuleOutput = ResearchAssessment | PolicyAssessment


class ResearchModule(Protocol):
    module: ResearchModuleName
    dependencies: frozenset[ResearchModuleName]

    def evaluate(
        self,
        context: ResearchContext,
        dependencies: Mapping[ResearchModuleName, ResearchAssessment],
    ) -> ModuleOutput: ...


class ResearchReportBuilder(Protocol):
    def build(
        self,
        request: ResearchRequest,
        assessments: tuple[ResearchAssessment, ...],
        policy_assessment: PolicyAssessment | None,
    ) -> ResearchReport: ...


class ResearchRepository(Protocol):
    def start_run(self, request: ResearchRequest) -> str: ...

    def save_run(self, run: ResearchRun) -> None: ...

    def fail_run(
        self,
        run_id: str,
        request: ResearchRequest,
        *,
        reason: str,
    ) -> None: ...


class ResearchApplication(Protocol):
    def run(self, request: ResearchRequest) -> ResearchRun: ...
