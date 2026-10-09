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


class ProviderArtifactStatus(StrEnum):
    CAPTURED = "captured"
    MISSING = "missing"
    UNAVAILABLE = "unavailable"


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
class ProviderArtifact:
    artifact_id: str
    provider: str
    dataset: str
    market: Market
    subject: str
    source_identity: str
    source_reference: str
    published_at: datetime
    retrieved_at: datetime
    content_hash: str
    media_type: str
    availability_precision: AvailabilityPrecision
    trust_level: DataTrustLevel
    content: bytes = field(repr=False, compare=False)
    model_version: str = PROVIDER_EVIDENCE_VERSION

    def __post_init__(self) -> None:
        require_timezone(self.published_at, "provider artifact published_at")
        require_timezone(self.retrieved_at, "provider artifact retrieved_at")
        if self.published_at > self.retrieved_at:
            raise ValueError("provider artifact cannot precede its publication")
        if len(self.artifact_id) != 64 or len(self.content_hash) != 64:
            raise ValueError("provider artifact identifiers must be SHA-256 digests")
        if not all(
            value.strip()
            for value in (
                self.provider,
                self.dataset,
                self.subject,
                self.source_identity,
                self.source_reference,
                self.media_type,
            )
        ):
            raise ValueError("provider artifact identity and media type are required")
        if not self.content:
            raise ValueError("captured provider artifacts cannot be empty")
        if sha256(self.content).hexdigest() != self.content_hash:
            raise ValueError("provider artifact content hash does not match its bytes")


@dataclass(frozen=True, slots=True)
class ProviderArtifactObservation:
    observation_id: str
    provider: str
    dataset: str
    market: Market
    subject: str
    source_identity: str
    source_reference: str
    published_at: datetime
    retrieved_at: datetime
    status: ProviderArtifactStatus
    artifact_id: str | None
    error_code: str
    related_source_identities: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_timezone(self.published_at, "provider artifact observation published_at")
        require_timezone(self.retrieved_at, "provider artifact observation retrieved_at")
        if self.published_at > self.retrieved_at:
            raise ValueError("artifact observation cannot precede publication")
        if len(self.observation_id) != 64:
            raise ValueError("artifact observation ID must be a SHA-256 digest")
        if self.artifact_id is not None and len(self.artifact_id) != 64:
            raise ValueError("artifact observation artifact ID must be a SHA-256 digest")
        if self.status is ProviderArtifactStatus.CAPTURED and self.artifact_id is None:
            raise ValueError("captured artifact observations require an artifact ID")
        if self.status is not ProviderArtifactStatus.CAPTURED and self.artifact_id:
            raise ValueError("uncaptured artifact observations cannot reference an artifact")
        if self.status is ProviderArtifactStatus.CAPTURED and self.error_code:
            raise ValueError("captured artifact observations cannot contain an error")
        if self.status is not ProviderArtifactStatus.CAPTURED and not self.error_code:
            raise ValueError("uncaptured artifact observations require an error code")
        if not all(
            value.strip()
            for value in (
                self.provider,
                self.dataset,
                self.subject,
                self.source_identity,
                self.source_reference,
            )
        ):
            raise ValueError("artifact observation identity is required")


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
    artifacts: tuple[ProviderArtifact, ...] = ()
    artifact_observations: tuple[ProviderArtifactObservation, ...] = ()

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
        artifacts = {artifact.artifact_id: artifact for artifact in self.artifacts}
        if len(artifacts) != len(self.artifacts):
            raise ValueError("provider evidence batch contains duplicate artifact IDs")
        for artifact in self.artifacts:
            if (
                artifact.provider != self.provider
                or artifact.dataset != self.dataset
                or artifact.market != self.market
                or artifact.retrieved_at != self.retrieved_at
            ):
                raise ValueError("provider artifact does not match its batch")
        for observation in self.artifact_observations:
            if (
                observation.provider != self.provider
                or observation.dataset != self.dataset
                or observation.market != self.market
                or observation.retrieved_at != self.retrieved_at
            ):
                raise ValueError("provider artifact observation does not match its batch")
            if (
                observation.artifact_id is not None
                and observation.artifact_id not in artifacts
            ):
                raise ValueError("captured observation must reference a batch artifact")


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
    @property
    def provider_id(self) -> str: ...

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


def provider_artifact_id(
    *,
    provider: str,
    dataset: str,
    market: Market,
    subject: str,
    source_identity: str,
    source_reference: str,
    content_hash: str,
) -> str:
    return _stable_identifier(
        {
            "provider": provider,
            "dataset": dataset,
            "market": market.value,
            "subject": subject,
            "source_identity": source_identity,
            "source_reference": source_reference,
            "content_hash": content_hash,
        }
    )


def provider_artifact_observation_id(
    *,
    provider: str,
    dataset: str,
    market: Market,
    subject: str,
    source_identity: str,
    source_reference: str,
    published_at: datetime,
    retrieved_at: datetime,
    status: ProviderArtifactStatus,
    artifact_id: str | None,
    error_code: str,
    related_source_identities: tuple[str, ...],
) -> str:
    return _stable_identifier(
        {
            "provider": provider,
            "dataset": dataset,
            "market": market.value,
            "subject": subject,
            "source_identity": source_identity,
            "source_reference": source_reference,
            "published_at": published_at.isoformat(),
            "retrieved_at": retrieved_at.isoformat(),
            "status": status.value,
            "artifact_id": artifact_id,
            "error_code": error_code,
            "related_source_identities": related_source_identities,
        }
    )


def _stable_identifier(document: dict[str, object]) -> str:
    encoded = json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest()


__all__ = [
    "EvidenceLimitation",
    "ProviderCapabilityStatus",
    "ProviderArtifact",
    "ProviderArtifactObservation",
    "ProviderArtifactStatus",
    "ProviderContractCheck",
    "ProviderContractRun",
    "ProviderContractStatus",
    "ProviderDatasetCapability",
    "ProviderDatasetRequest",
    "ProviderEvidenceAdapter",
    "ProviderEvidenceBatch",
    "ProviderEvidenceRecord",
    "provider_artifact_id",
    "provider_artifact_observation_id",
    "provider_evidence_id",
]
