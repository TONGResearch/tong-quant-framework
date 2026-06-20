import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

import pandas as pd

from tong_quant.domain.enums import (
    Adjustment,
    AssetType,
    AvailabilityPrecision,
    DataTrustLevel,
    HistoricalCoverageSubject,
    IngestionBatchStatus,
    LifecycleEventType,
    Market,
    PITReadinessClassification,
)
from tong_quant.domain.models import Instrument, require_timezone
from tong_quant.version import HISTORICAL_COVERAGE_VERSION, PIT_READINESS_VERSION


@dataclass(frozen=True, slots=True)
class RawDataset:
    dataset: str
    frame: pd.DataFrame
    retrieved_at: datetime
    source: str
    parameters: dict[str, Any]
    raw_data_hash: str = ""

    def __post_init__(self) -> None:
        require_timezone(self.retrieved_at, "retrieved_at")
        if self.raw_data_hash and len(self.raw_data_hash) != 64:
            raise ValueError("raw_data_hash must be a SHA-256 hex digest")

    def content_hash(self) -> str:
        if self.raw_data_hash:
            return self.raw_data_hash
        return dataframe_sha256(self.frame, self.parameters)


@dataclass(frozen=True, slots=True)
class DailyBarRequest:
    symbol: str
    start_date: str
    end_date: str
    asset_type: AssetType = AssetType.EQUITY
    market: Market = Market.CHINA_A
    adjustment: Adjustment = Adjustment.NONE


@dataclass(frozen=True, slots=True)
class IngestionResult:
    dataset: str
    received: int
    accepted: int
    rejected: int
    cached: bool
    batch_id: str = ""
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ProviderResponse:
    dataset: RawDataset
    cache_hit: bool


@dataclass(frozen=True, slots=True)
class IngestionBatch:
    batch_id: str
    provider: str
    dataset: str
    started_at: datetime
    status: IngestionBatchStatus
    raw_response_hash: str
    completed_at: datetime | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    failure_reason: str = ""
    retry_of: str | None = None

    def __post_init__(self) -> None:
        require_timezone(self.started_at, "started_at")
        if self.completed_at is not None:
            require_timezone(self.completed_at, "completed_at")
            if self.completed_at < self.started_at:
                raise ValueError("completed_at cannot precede started_at")
        if self.status is IngestionBatchStatus.FAILED and not self.failure_reason:
            raise ValueError("failed ingestion batches require a failure reason")


@dataclass(frozen=True, slots=True)
class RawDatasetFingerprint:
    dataset: str
    provider: str
    raw_data_hash: str
    retrieved_at: datetime
    parameters: dict[str, Any]
    row_count: int
    source: str

    def __post_init__(self) -> None:
        require_timezone(self.retrieved_at, "retrieved_at")
        if len(self.raw_data_hash) != 64:
            raise ValueError("raw_data_hash must be a SHA-256 hex digest")
        if self.row_count < 0:
            raise ValueError("row_count cannot be negative")


@dataclass(frozen=True, slots=True)
class DataAvailabilityWarning:
    dataset: str
    warning_code: str
    message: str
    trust_level: DataTrustLevel
    created_at: datetime
    batch_id: str = ""
    instrument_id: str = ""

    def __post_init__(self) -> None:
        require_timezone(self.created_at, "created_at")
        if not self.warning_code.strip() or not self.message.strip():
            raise ValueError("availability warnings require code and message")


@dataclass(frozen=True, slots=True)
class ProviderLimitation:
    provider: str
    dataset: str
    limitation_code: str
    description: str
    trust_level: DataTrustLevel
    documented_at: datetime

    def __post_init__(self) -> None:
        require_timezone(self.documented_at, "documented_at")
        if not self.provider.strip() or not self.dataset.strip():
            raise ValueError("provider limitations require provider and dataset")
        if not self.limitation_code.strip() or not self.description.strip():
            raise ValueError("provider limitations require code and description")


@dataclass(frozen=True, slots=True)
class PITReadinessAssessment:
    dataset: str
    assessed_at: datetime
    coverage_ratio: float
    trust_level: DataTrustLevel
    missing_critical_fields: tuple[str, ...]
    warnings: tuple[str, ...]
    ready_for_historical_replay: bool
    readiness_score: float
    classification: PITReadinessClassification
    score_components: dict[str, float]
    assumptions: tuple[str, ...]
    model_version: str = PIT_READINESS_VERSION

    def __post_init__(self) -> None:
        require_timezone(self.assessed_at, "assessed_at")
        if not 0 <= self.coverage_ratio <= 1:
            raise ValueError("coverage_ratio must be between zero and one")
        if not 0 <= self.readiness_score <= 100:
            raise ValueError("readiness_score must be between zero and 100")
        if any(not 0 <= value <= 100 for value in self.score_components.values()):
            raise ValueError("PIT readiness components must be between zero and 100")
        if self.ready_for_historical_replay != (
            self.classification is PITReadinessClassification.USABLE
        ):
            raise ValueError("PIT readiness boolean and classification disagree")
        if self.ready_for_historical_replay and (
            self.missing_critical_fields
            or self.trust_level
            in {DataTrustLevel.LOW, DataTrustLevel.UNKNOWN}
        ):
            raise ValueError("ready datasets cannot have critical gaps or weak trust")


@dataclass(frozen=True, slots=True)
class SecurityLifecycleEvent:
    instrument: Instrument
    event_type: LifecycleEventType
    effective_date: date
    available_at: datetime
    source: str
    source_reference: str = ""
    details: dict[str, str] = field(default_factory=dict)
    raw_data_hash: str = ""
    batch_id: str = ""
    provider_dataset: str = ""
    availability_precision: AvailabilityPrecision = AvailabilityPrecision.UNKNOWN
    trust_level: DataTrustLevel = DataTrustLevel.UNKNOWN

    def __post_init__(self) -> None:
        require_timezone(self.available_at, "lifecycle available_at")
        if self.raw_data_hash and len(self.raw_data_hash) < 16:
            raise ValueError("raw_data_hash is too short")


@dataclass(frozen=True, slots=True)
class FundamentalPublicationEvent:
    instrument: Instrument
    period_end: date
    report_type: str
    published_at: datetime
    available_at: datetime
    title: str
    revision: int
    source: str
    source_reference: str = ""
    raw_data_hash: str = ""
    batch_id: str = ""
    provider_dataset: str = ""
    availability_precision: AvailabilityPrecision = AvailabilityPrecision.UNKNOWN
    trust_level: DataTrustLevel = DataTrustLevel.UNKNOWN

    def __post_init__(self) -> None:
        require_timezone(self.published_at, "publication published_at")
        require_timezone(self.available_at, "publication available_at")
        if self.available_at < self.published_at:
            raise ValueError("publication available_at cannot precede published_at")
        if self.revision < 0:
            raise ValueError("publication revision cannot be negative")
        if not self.report_type.strip() or not self.title.strip():
            raise ValueError("publication report type and title are required")


@dataclass(frozen=True, slots=True)
class HistoricalCoverageAssessment:
    subject_type: HistoricalCoverageSubject
    subject_id: str
    dataset: str
    period_start: date
    period_end: date
    assessed_at: datetime
    confidence_score: float
    classification: PITReadinessClassification
    trust_level: DataTrustLevel
    score_components: dict[str, float]
    warnings: tuple[str, ...]
    assumptions: tuple[str, ...]
    model_version: str = HISTORICAL_COVERAGE_VERSION

    def __post_init__(self) -> None:
        require_timezone(self.assessed_at, "coverage assessed_at")
        if self.period_end < self.period_start:
            raise ValueError("coverage period_end cannot precede period_start")
        if not 0 <= self.confidence_score <= 100:
            raise ValueError("coverage confidence must be between zero and 100")
        if any(not 0 <= value <= 100 for value in self.score_components.values()):
            raise ValueError("coverage components must be between zero and 100")
        if self.classification is PITReadinessClassification.USABLE and (
            self.trust_level in {DataTrustLevel.LOW, DataTrustLevel.UNKNOWN}
        ):
            raise ValueError("usable historical coverage requires medium or better trust")


def dataframe_sha256(frame: pd.DataFrame, parameters: dict[str, Any]) -> str:
    payload = {
        "parameters": parameters,
        "frame": frame.to_json(orient="table", date_format="iso", force_ascii=True),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
