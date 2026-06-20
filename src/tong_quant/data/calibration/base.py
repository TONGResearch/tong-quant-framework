from typing import Protocol

from tong_quant.data.calibration.models import (
    CalibrationQuery,
    DatasetConfidenceAssessment,
    ProviderCalibrationResult,
    ProviderCalibrationSnapshot,
    ProviderConflict,
    ProviderConsistencyReport,
)


class ProviderCalibrationSource(Protocol):
    source_id: str

    def calibration_snapshot(
        self, query: CalibrationQuery
    ) -> ProviderCalibrationSnapshot: ...


class ProviderCalibrationRepository(Protocol):
    def save_provider_calibration_result(
        self, result: ProviderCalibrationResult
    ) -> None: ...

    def save_provider_consistency_report(
        self, report: ProviderConsistencyReport
    ) -> str: ...

    def save_provider_conflicts(self, conflicts: tuple[ProviderConflict, ...]) -> int: ...

    def save_dataset_confidence_assessment(
        self, assessment: DatasetConfidenceAssessment
    ) -> str: ...


__all__ = ["ProviderCalibrationRepository", "ProviderCalibrationSource"]
