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


class MemoizedCalibrationSource:
    def __init__(self, source: ProviderCalibrationSource) -> None:
        self.source_id = source.source_id
        self._source = source
        self._snapshots: dict[
            tuple[str, str, tuple[tuple[str, str], ...]],
            ProviderCalibrationSnapshot,
        ] = {}
        self._errors: dict[
            tuple[str, str, tuple[tuple[str, str], ...]],
            Exception,
        ] = {}

    def calibration_snapshot(
        self,
        query: CalibrationQuery,
    ) -> ProviderCalibrationSnapshot:
        key = (
            query.dataset.value,
            query.as_of.isoformat(),
            tuple(sorted(query.parameters.items())),
        )
        if key in self._snapshots:
            return self._snapshots[key]
        if key in self._errors:
            raise self._errors[key]
        try:
            snapshot = self._source.calibration_snapshot(query)
        except Exception as error:
            self._errors[key] = error
            raise
        self._snapshots[key] = snapshot
        return snapshot


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


__all__ = [
    "MemoizedCalibrationSource",
    "ProviderCalibrationRepository",
    "ProviderCalibrationSource",
]
