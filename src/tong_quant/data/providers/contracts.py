import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
from typing import Protocol

from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market
from tong_quant.domain.models import require_timezone
from tong_quant.version import PROVIDER_EVIDENCE_VERSION


class ProviderCapabilityStatus(StrEnum):
    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    NOT_TESTED = "not_tested"


class ProviderContractStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    DEFECT = "defect"


@dataclass(frozen=True, slots=True)
class ProviderDatasetRequest:
    dataset: str
    market: Market
    subject: str
    as_of: datetime
    parameters: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_timezone(self.as_of, "provider dataset request as_of")
        if not self.dataset.strip() or not self.subject.strip():
            raise ValueError("provider dataset request requires dataset and subject")


@dataclass(frozen=True, slots=True)
class EvidenceLimitation:
    code: str
    description: str
    trust_level: DataTrustLevel

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.description.strip():
            raise ValueError("evidence limitations require code and description")


@dataclass(frozen=True, slots=True)
class ProviderDatasetCapability:
    provider: str
    dataset: str
    markets: tuple[Market, ...]
    status: ProviderCapabilityStatus
    trust_level: DataTrustLevel
    availability_precision: AvailabilityPrecision
    historical_continuity: bool
    required_parameters: tuple[str, ...]
    limitations: tuple[EvidenceLimitation, ...]
    model_version: str = PROVIDER_EVIDENCE_VERSION

    def __post_init__(self) -> None:
        if not self.provider.strip() or not self.dataset.strip() or not self.markets:
            raise ValueError("provider capability requires provider, dataset, and markets")
        if self.status is ProviderCapabilityStatus.AVAILABLE and (
            self.trust_level is DataTrustLevel.UNKNOWN
        ):
            raise ValueError("available capability cannot have unknown trust")


@dataclass(frozen=True, slots=True)
class ProviderEvidenceRecord:
    evidence_id: str
    provider: str
    dataset: str
    market: Market
    subject: str
    available_at: datetime
    retrieved_at: datetime
    source_reference: str
    payload: dict[str, object]
    raw_data_hash: str
    availability_precision: AvailabilityPrecision
    trust_level: DataTrustLevel
    limitations: tuple[str, ...]
    observed_at: datetime | None = None
    published_at: datetime | None = None

    def __post_init__(self) -> None:
        require_timezone(self.available_at, "provider evidence available_at")
        require_timezone(self.retrieved_at, "provider evidence retrieved_at")
        if self.observed_at is not None:
            require_timezone(self.observed_at, "provider evidence observed_at")
        if self.published_at is not None:
            require_timezone(self.published_at, "provider evidence published_at")
        if self.available_at > self.retrieved_at:
            raise ValueError("provider evidence cannot be available after retrieval")
        if self.published_at is not None and self.available_at < self.published_at:
            raise ValueError("provider evidence cannot precede publication")
        if self.observed_at is not None and self.observed_at > self.retrieved_at:
            raise ValueError("provider evidence cannot observe future data")
        if len(self.evidence_id) != 64 or len(self.raw_data_hash) != 64:
            raise ValueError("provider evidence identifiers must be SHA-256 digests")
        if not self.provider.strip() or not self.dataset.strip() or not self.subject.strip():
            raise ValueError("provider evidence identity fields are required")
        json.dumps(self.payload, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class ProviderEvidenceBatch:
    provider: str
    dataset: str
    market: Market
    retrieved_at: datetime
    source: str
    parameters: dict[str, str]
    raw_data_hash: str
    raw_record_count: int
    records: tuple[ProviderEvidenceRecord, ...]
    limitations: tuple[EvidenceLimitation, ...]

    def __post_init__(self) -> None:
        require_timezone(self.retrieved_at, "provider evidence batch retrieved_at")
        if len(self.raw_data_hash) != 64:
            raise ValueError("provider evidence batch requires a SHA-256 raw hash")
        if self.raw_record_count < 0 or self.raw_record_count < len(self.records):
            raise ValueError("provider evidence batch record counts are invalid")
        for record in self.records:
            if (
                record.provider != self.provider
                or record.dataset != self.dataset
                or record.market != self.market
                or record.retrieved_at != self.retrieved_at
                or record.raw_data_hash != self.raw_data_hash
            ):
                raise ValueError("provider evidence record does not match its batch")


@dataclass(frozen=True, slots=True)
class ProviderContractCheck:
    check_id: str
    run_id: str
    provider: str
    dataset: str
    market: Market
    subject: str
    request_as_of: datetime
    status: ProviderContractStatus
    records_observed: int
    trust_level: DataTrustLevel
    availability_precision: AvailabilityPrecision
    latency_ms: float
    required_fields: tuple[str, ...]
    missing_fields: tuple[str, ...]
    limitations: tuple[str, ...]
    error_code: str
    checked_at: datetime

    def __post_init__(self) -> None:
        require_timezone(self.request_as_of, "provider contract request_as_of")
        require_timezone(self.checked_at, "provider contract checked_at")
        if self.records_observed < 0 or self.latency_ms < 0:
            raise ValueError("provider contract metrics cannot be negative")
        if not self.check_id.strip() or not self.run_id.strip():
            raise ValueError("provider contract check identity is required")
        if not self.provider.strip() or not self.dataset.strip() or not self.subject.strip():
            raise ValueError("provider contract check scope is required")


@dataclass(frozen=True, slots=True)
class ProviderContractRun:
    run_id: str
    started_at: datetime
    completed_at: datetime
    status: ProviderContractStatus
    checks: tuple[ProviderContractCheck, ...]
    implementation_version: str

    def __post_init__(self) -> None:
        require_timezone(self.started_at, "provider contract run started_at")
        require_timezone(self.completed_at, "provider contract run completed_at")
        if self.completed_at < self.started_at:
            raise ValueError("provider contract run cannot complete before it starts")
        if not self.run_id.strip() or not self.implementation_version.strip():
            raise ValueError("provider contract run identity and version are required")
        if any(check.run_id != self.run_id for check in self.checks):
            raise ValueError("provider contract checks must belong to their run")


class ProviderEvidenceAdapter(Protocol):
    provider_id: str

    def capabilities(self) -> tuple[ProviderDatasetCapability, ...]: ...

    def fetch(self, request: ProviderDatasetRequest) -> ProviderEvidenceBatch: ...


def provider_evidence_id(
    *,
    provider: str,
    dataset: str,
    market: Market,
    subject: str,
    available_at: datetime,
    source_reference: str,
    payload: dict[str, object],
) -> str:
    document = {
        "provider": provider,
        "dataset": dataset,
        "market": market.value,
        "subject": subject,
        "available_at": available_at.isoformat(),
        "source_reference": source_reference,
        "payload": payload,
    }
    encoded = json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


__all__ = [
    "EvidenceLimitation",
    "ProviderCapabilityStatus",
    "ProviderContractCheck",
    "ProviderContractRun",
    "ProviderContractStatus",
    "ProviderDatasetCapability",
    "ProviderDatasetRequest",
    "ProviderEvidenceAdapter",
    "ProviderEvidenceBatch",
    "ProviderEvidenceRecord",
    "provider_evidence_id",
]
