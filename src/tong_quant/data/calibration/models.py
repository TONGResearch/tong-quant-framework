from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from tong_quant.domain.enums import DataTrustLevel
from tong_quant.domain.models import require_timezone
from tong_quant.version import (
    DATASET_CONFIDENCE_VERSION,
    PROVIDER_CALIBRATION_VERSION,
    PROVIDER_CONFLICT_VERSION,
)

CalibrationValue = str | int | float | bool | None


class CalibrationDataset(StrEnum):
    SECURITY_LIFECYCLE = "security_lifecycle"
    ST_STATUS = "st_status"
    SUSPENSION_STATUS = "suspension_status"
    DELISTING_RECORDS = "delisting_records"
    FINANCIAL_PUBLICATION_DATES = "financial_publication_dates"
    FUNDAMENTAL_REVISIONS = "fundamental_revisions"
    CORPORATE_ACTIONS = "corporate_actions"
    UNIVERSE_COVERAGE = "universe_coverage"
    CSI300_MEMBERSHIP = "csi300_membership"
    CSI500_MEMBERSHIP = "csi500_membership"
    CSI1000_MEMBERSHIP = "csi1000_membership"


DEFAULT_CALIBRATION_FIELDS: dict[CalibrationDataset, tuple[str, ...]] = {
    CalibrationDataset.SECURITY_LIFECYCLE: ("event_type", "effective_date"),
    CalibrationDataset.ST_STATUS: ("is_st", "effective_date"),
    CalibrationDataset.SUSPENSION_STATUS: ("event_type", "effective_date"),
    CalibrationDataset.DELISTING_RECORDS: ("delist_date",),
    CalibrationDataset.FINANCIAL_PUBLICATION_DATES: ("actual_date",),
    CalibrationDataset.FUNDAMENTAL_REVISIONS: (
        "published_at",
        "report_type",
        "update_flag",
    ),
    CalibrationDataset.CORPORATE_ACTIONS: (
        "effective_date",
        "cash_dividend",
        "stock_dividend",
    ),
    CalibrationDataset.UNIVERSE_COVERAGE: ("listed",),
    CalibrationDataset.CSI300_MEMBERSHIP: ("member",),
    CalibrationDataset.CSI500_MEMBERSHIP: ("member",),
    CalibrationDataset.CSI1000_MEMBERSHIP: ("member",),
}


class ProviderConflictType(StrEnum):
    MISSING_PRIMARY = "missing_primary"
    MISSING_SECONDARY = "missing_secondary"
    VALUE_MISMATCH = "value_mismatch"


class ProviderConflictSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class CalibrationQuery:
    dataset: CalibrationDataset
    as_of: datetime
    parameters: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_timezone(self.as_of, "calibration query as_of")


@dataclass(frozen=True, slots=True)
class CalibrationRecord:
    key: str
    fields: dict[str, CalibrationValue]

    def __post_init__(self) -> None:
        if not self.key.strip():
            raise ValueError("calibration record key must not be empty")


@dataclass(frozen=True, slots=True)
class ProviderCalibrationSnapshot:
    provider: str
    dataset: str
    as_of: datetime
    records: tuple[CalibrationRecord, ...]
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_timezone(self.as_of, "calibration snapshot as_of")
        if not self.provider.strip() or not self.dataset.strip():
            raise ValueError("calibration snapshot requires provider and dataset")
        keys = [record.key for record in self.records]
        if len(keys) != len(set(keys)):
            raise ValueError("calibration snapshot record keys must be unique")


@dataclass(frozen=True, slots=True)
class ProviderConsistencyReport:
    report_id: str
    dataset: str
    primary_provider: str
    secondary_provider: str
    compared_at: datetime
    primary_count: int
    secondary_count: int
    matched_count: int
    primary_only_count: int
    secondary_only_count: int
    key_overlap_score: float
    field_match_scores: dict[str, float]
    consistency_score: float
    trust_level: DataTrustLevel
    limitations: tuple[str, ...]
    comparison_hash: str
    model_version: str = PROVIDER_CALIBRATION_VERSION

    def __post_init__(self) -> None:
        require_timezone(self.compared_at, "provider comparison compared_at")
        counts = (
            self.primary_count,
            self.secondary_count,
            self.matched_count,
            self.primary_only_count,
            self.secondary_only_count,
        )
        if min(counts) < 0:
            raise ValueError("provider comparison counts cannot be negative")
        scores = (
            self.key_overlap_score,
            self.consistency_score,
            *self.field_match_scores.values(),
        )
        if any(not 0 <= score <= 100 for score in scores):
            raise ValueError("provider comparison scores must be between zero and 100")
        if len(self.comparison_hash) != 64:
            raise ValueError("comparison_hash must be a SHA-256 digest")


@dataclass(frozen=True, slots=True)
class ProviderConflict:
    conflict_id: str
    conflict_fingerprint: str
    report_id: str
    dataset: str
    record_key: str
    field_name: str
    conflict_type: ProviderConflictType
    primary_provider: str
    secondary_provider: str
    primary_value: CalibrationValue
    secondary_value: CalibrationValue
    severity: ProviderConflictSeverity
    detected_at: datetime
    model_version: str = PROVIDER_CONFLICT_VERSION

    def __post_init__(self) -> None:
        require_timezone(self.detected_at, "provider conflict detected_at")
        if len(self.conflict_id) != 64 or len(self.conflict_fingerprint) != 64:
            raise ValueError("provider conflict identifiers must be SHA-256 digests")


@dataclass(frozen=True, slots=True)
class DatasetConfidenceAssessment:
    assessment_id: str
    report_id: str
    dataset: str
    assessed_at: datetime
    confidence_score: float
    trust_level: DataTrustLevel
    component_scores: dict[str, float]
    conflict_count: int
    critical_conflict_count: int
    warnings: tuple[str, ...]
    model_version: str = DATASET_CONFIDENCE_VERSION

    def __post_init__(self) -> None:
        require_timezone(self.assessed_at, "dataset confidence assessed_at")
        if not 0 <= self.confidence_score <= 100:
            raise ValueError("dataset confidence must be between zero and 100")
        if any(not 0 <= score <= 100 for score in self.component_scores.values()):
            raise ValueError("dataset confidence components must be between zero and 100")
        if self.conflict_count < 0 or self.critical_conflict_count < 0:
            raise ValueError("dataset confidence conflict counts cannot be negative")
        if self.critical_conflict_count > self.conflict_count:
            raise ValueError("critical conflicts cannot exceed total conflicts")


@dataclass(frozen=True, slots=True)
class ProviderCalibrationResult:
    report: ProviderConsistencyReport
    conflicts: tuple[ProviderConflict, ...]
    confidence: DatasetConfidenceAssessment


__all__ = [
    "CalibrationDataset",
    "CalibrationQuery",
    "CalibrationRecord",
    "CalibrationValue",
    "DatasetConfidenceAssessment",
    "DEFAULT_CALIBRATION_FIELDS",
    "ProviderCalibrationSnapshot",
    "ProviderCalibrationResult",
    "ProviderConflict",
    "ProviderConflictSeverity",
    "ProviderConflictType",
    "ProviderConsistencyReport",
]
