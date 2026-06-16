from typing import Protocol

from tong_quant.domain.enums import ValidationModuleName
from tong_quant.validation.models import (
    ValidationModuleResult,
    ValidationReport,
    ValidationRequest,
    ValidationRun,
    ValidationSplit,
)
from tong_quant.validation.replay.models import HistoricalReplayResult, ReplayQuery


class ValidationModule(Protocol):
    module: ValidationModuleName

    def evaluate(
        self,
        request: ValidationRequest,
        splits: tuple[ValidationSplit, ...],
    ) -> ValidationModuleResult: ...


class ValidationReportBuilder(Protocol):
    def build(
        self,
        request: ValidationRequest,
        results: tuple[ValidationModuleResult, ...],
        splits: tuple[ValidationSplit, ...],
    ) -> ValidationReport: ...


class ValidationRepository(Protocol):
    def start_run(self, request: ValidationRequest) -> str: ...

    def save_run(self, run: ValidationRun) -> None: ...

    def fail_run(
        self,
        run_id: str,
        request: ValidationRequest,
        *,
        reason: str,
    ) -> None: ...


class HistoricalReplaySource(Protocol):
    def build(self, query: ReplayQuery) -> HistoricalReplayResult: ...


class ValidationApplication(Protocol):
    def run(self, request: ValidationRequest) -> ValidationRun: ...
