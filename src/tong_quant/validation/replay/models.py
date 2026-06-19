from dataclasses import dataclass, field
from datetime import datetime

from tong_quant.domain.enums import DataTrustLevel, Market
from tong_quant.domain.models import Instrument, require_timezone
from tong_quant.validation.models import OutcomeDefinition, ValidationSample
from tong_quant.version import (
    FRAMEWORK_VERSION,
    HISTORICAL_REPLAY_VERSION,
    REPLAY_CONFIDENCE_VERSION,
)


def _require_percentage(name: str, value: float) -> None:
    if not 0 <= value <= 100:
        raise ValueError(f"{name} must be between 0 and 100")


@dataclass(frozen=True, slots=True)
class ReplayConfidence:
    data_trust_score: float
    pit_readiness_score: float
    missing_data_score: float
    provider_limitation_score: float
    confidence: float
    reasons: tuple[str, ...]
    model_version: str = REPLAY_CONFIDENCE_VERSION

    def __post_init__(self) -> None:
        for name, value in (
            ("data_trust_score", self.data_trust_score),
            ("pit_readiness_score", self.pit_readiness_score),
            ("missing_data_score", self.missing_data_score),
            ("provider_limitation_score", self.provider_limitation_score),
            ("confidence", self.confidence),
        ):
            _require_percentage(name, value)
        if not self.reasons:
            raise ValueError("ReplayConfidence must explain its score")


@dataclass(frozen=True, slots=True)
class ReplayQuery:
    subject_type: str
    market: Market
    universe: str | None
    decision_as_of: datetime
    outcome_as_of: datetime
    required_inputs: tuple[str, ...]
    outcome_definitions: tuple[OutcomeDefinition, ...]
    symbols: tuple[str, ...] = ()
    minimum_trust_level: DataTrustLevel = DataTrustLevel.MEDIUM
    provider_limitation_datasets: tuple[str, ...] = ()
    include_incomplete_samples: bool = True
    configuration_hash: str = ""
    framework_version: str = FRAMEWORK_VERSION
    git_commit: str = "unknown"

    def __post_init__(self) -> None:
        require_timezone(self.decision_as_of, "decision_as_of")
        require_timezone(self.outcome_as_of, "outcome_as_of")
        if self.outcome_as_of < self.decision_as_of:
            raise ValueError("outcome_as_of cannot precede decision_as_of")
        if self.subject_type not in {"instrument", "universe"}:
            raise ValueError("subject_type must be instrument or universe")
        if self.subject_type == "instrument" and not self.symbols:
            raise ValueError("instrument replay requires symbols")
        if self.subject_type == "universe" and not self.universe:
            raise ValueError("universe replay requires a universe")
        if not self.required_inputs:
            raise ValueError("ReplayQuery requires required_inputs")
        if not self.outcome_definitions:
            raise ValueError("ReplayQuery requires outcome_definitions")


@dataclass(frozen=True, slots=True)
class ReplayManifest:
    manifest_id: str
    query_hash: str
    input_hashes: dict[str, str]
    dataset_versions: dict[str, str]
    schema_version: str
    framework_version: str
    configuration_hash: str
    git_commit: str
    data_trust_summary: dict[str, int]
    provider_limitations: tuple[str, ...]
    missing_data_warnings: tuple[str, ...]
    replay_confidence: ReplayConfidence
    generated_at: datetime
    model_version: str = HISTORICAL_REPLAY_VERSION

    def __post_init__(self) -> None:
        require_timezone(self.generated_at, "generated_at")
        if not self.manifest_id.strip() or len(self.query_hash) != 64:
            raise ValueError("ReplayManifest requires an id and query hash")
        if any(len(value) != 64 for value in self.input_hashes.values()):
            raise ValueError("manifest input hashes must be SHA-256 hex digests")


@dataclass(frozen=True, slots=True)
class ReplayValidationSample:
    sample_id: str
    instrument: Instrument
    decision_as_of: datetime
    outcome_as_of: datetime
    decision_context: dict[str, object]
    outcome_context: dict[str, object]
    evidence_references: tuple[str, ...]
    missing_data_flags: tuple[str, ...]
    replay_hash: str
    replay_confidence: ReplayConfidence
    validation_sample: ValidationSample | None = None
    provider_limitations: tuple[str, ...] = ()
    data_trust_summary: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_timezone(self.decision_as_of, "decision_as_of")
        require_timezone(self.outcome_as_of, "outcome_as_of")
        if not self.sample_id.strip() or len(self.replay_hash) != 64:
            raise ValueError("ReplayValidationSample requires id and replay hash")
        if self.outcome_as_of < self.decision_as_of:
            raise ValueError("sample outcome_as_of cannot precede decision_as_of")
        if self.validation_sample is not None:
            if self.validation_sample.decision_at != self.decision_as_of:
                raise ValueError("validation sample decision time differs from replay sample")
            if self.validation_sample.sample_id != self.sample_id:
                raise ValueError("validation sample id differs from replay sample id")

    @property
    def is_complete(self) -> bool:
        blocking_flags = tuple(
            flag for flag in self.missing_data_flags if flag.endswith("_missing")
        )
        return self.validation_sample is not None and not blocking_flags


@dataclass(frozen=True, slots=True)
class HistoricalReplayResult:
    query: ReplayQuery
    manifest: ReplayManifest
    samples: tuple[ReplayValidationSample, ...]

    @property
    def complete_validation_samples(self) -> tuple[ValidationSample, ...]:
        return tuple(
            sample.validation_sample
            for sample in self.samples
            if sample.validation_sample is not None and sample.is_complete
        )


__all__ = [
    "HistoricalReplayResult",
    "ReplayConfidence",
    "ReplayManifest",
    "ReplayQuery",
    "ReplayValidationSample",
]
