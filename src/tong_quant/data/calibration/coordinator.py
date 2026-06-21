from dataclasses import dataclass
from datetime import datetime

from tong_quant.data.calibration.base import (
    ProviderCalibrationRepository,
    ProviderCalibrationSource,
)
from tong_quant.data.calibration.engine import ProviderCalibrationEngine
from tong_quant.data.calibration.models import (
    DEFAULT_CALIBRATION_FIELDS,
    CalibrationQuery,
    ProviderCalibrationResult,
    ProviderCalibrationSnapshot,
)


@dataclass(frozen=True, slots=True)
class ProviderCalibrationCoordinator:
    repository: ProviderCalibrationRepository
    engine: ProviderCalibrationEngine = ProviderCalibrationEngine()

    def run(
        self,
        primary: ProviderCalibrationSource,
        secondary: ProviderCalibrationSource,
        query: CalibrationQuery,
        *,
        fields: tuple[str, ...] | None = None,
    ) -> ProviderCalibrationResult:
        comparison_fields = fields or DEFAULT_CALIBRATION_FIELDS[query.dataset]
        primary_snapshot = primary.calibration_snapshot(query)
        secondary_snapshot = secondary.calibration_snapshot(query)
        return self.run_snapshots(
            primary_snapshot,
            secondary_snapshot,
            fields=comparison_fields,
            compared_at=query.as_of,
        )

    def run_snapshots(
        self,
        primary_snapshot: ProviderCalibrationSnapshot,
        secondary_snapshot: ProviderCalibrationSnapshot,
        *,
        fields: tuple[str, ...],
        compared_at: datetime,
    ) -> ProviderCalibrationResult:
        report = self.engine.compare(
            primary_snapshot,
            secondary_snapshot,
            fields=fields,
            compared_at=compared_at,
        )
        conflicts = self.engine.detect_conflicts(
            primary_snapshot,
            secondary_snapshot,
            report,
            fields=fields,
        )
        temporal_alignment = (
            100.0
            if primary_snapshot.as_of == secondary_snapshot.as_of == compared_at
            else 50.0
        )
        confidence = self.engine.assess_confidence(
            report,
            conflicts,
            temporal_alignment_score=temporal_alignment,
        )
        result = ProviderCalibrationResult(
            report=report,
            conflicts=conflicts,
            confidence=confidence,
        )
        self.repository.save_provider_calibration_result(result)
        return result


__all__ = ["ProviderCalibrationCoordinator"]
