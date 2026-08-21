import json
import math
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Protocol

from tong_quant.data.providers.contracts import ProviderContractStatus
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market
from tong_quant.domain.models import require_timezone
from tong_quant.version import PROVIDER_CONTRACT_BASELINE_VERSION


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True, order=True)
class ProviderBaselineScope:
    provider: str
    dataset: str
    market: Market
    subject: str

    def __post_init__(self) -> None:
        if not all(
            value.strip() for value in (self.provider, self.dataset, self.subject)
        ):
            raise ValueError("provider baseline scope fields are required")


@dataclass(frozen=True, slots=True)
class ProviderBaselineQuery:
    period_start: datetime
    period_end: datetime
    expected_interval_days: int
    scopes: tuple[ProviderBaselineScope, ...]

    def __post_init__(self) -> None:
        require_timezone(self.period_start, "provider baseline period_start")
        require_timezone(self.period_end, "provider baseline period_end")
        if self.period_end <= self.period_start:
            raise ValueError("provider baseline period_end must follow period_start")
        if self.expected_interval_days < 1:
            raise ValueError("provider baseline interval must be positive")
        if not self.scopes:
            raise ValueError("provider baseline requires at least one scope")
        if len(self.scopes) != len(set(self.scopes)):
            raise ValueError("provider baseline scopes must be unique")


@dataclass(frozen=True, slots=True)
class ProviderContractObservation:
    check_id: str
    run_id: str
    scope: ProviderBaselineScope
    request_as_of: datetime
    checked_at: datetime
    status: ProviderContractStatus
    records_observed: int
    trust_level: DataTrustLevel
    availability_precision: AvailabilityPrecision
    required_fields: tuple[str, ...]
    missing_fields: tuple[str, ...]
    limitations: tuple[str, ...]
    error_code: str
    implementation_version: str

    def __post_init__(self) -> None:
        require_timezone(self.request_as_of, "provider observation request_as_of")
        require_timezone(self.checked_at, "provider observation checked_at")
        if not self.check_id.strip() or not self.run_id.strip():
            raise ValueError("provider observation identity is required")
        if self.records_observed < 0:
            raise ValueError("provider observation record count cannot be negative")


@dataclass(frozen=True, slots=True)
class ProviderBaselineEntry:
    scope: ProviderBaselineScope
    expected_periods: int
    observed_periods: int
    observation_count: int
    successful_observations: int
    successful_observation_ratio: float
    field_coverage_ratio: float
    continuity_ratio: float
    field_coverage: tuple[tuple[str, float], ...]
    status_counts: tuple[tuple[str, int], ...]
    observed_trust_levels: tuple[str, ...]
    observed_availability_precisions: tuple[str, ...]
    missing_periods: tuple[datetime, ...]
    failed_check_ids: tuple[str, ...]
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.expected_periods < 1 or self.observed_periods < 0:
            raise ValueError("provider baseline period counts are invalid")
        if self.observation_count < 0 or self.successful_observations < 0:
            raise ValueError("provider baseline observation counts are invalid")
        for value in (
            self.successful_observation_ratio,
            self.field_coverage_ratio,
            self.continuity_ratio,
        ):
            if not 0 <= value <= 1:
                raise ValueError("provider baseline ratios must be between zero and one")


@dataclass(frozen=True, slots=True)
class ProviderBaselineManifest:
    manifest_id: str
    baseline_hash: str
    input_hash: str
    query: ProviderBaselineQuery
    entries: tuple[ProviderBaselineEntry, ...]
    observation_ids: tuple[str, ...]
    generated_at: datetime
    implementation_version: str = PROVIDER_CONTRACT_BASELINE_VERSION

    def __post_init__(self) -> None:
        require_timezone(self.generated_at, "provider baseline generated_at")
        if any(len(value) != 64 for value in (self.manifest_id, self.baseline_hash)):
            raise ValueError("provider baseline identity must be a SHA-256 digest")
        if len(self.input_hash) != 64:
            raise ValueError("provider baseline input hash must be a SHA-256 digest")
        if self.manifest_id != self.baseline_hash:
            raise ValueError("provider baseline manifest is content-addressed")
        if len(self.observation_ids) != len(set(self.observation_ids)):
            raise ValueError("provider baseline observation references must be unique")
        if tuple(entry.scope for entry in self.entries) != tuple(
            sorted(self.query.scopes)
        ):
            raise ValueError("provider baseline entries must match sorted query scopes")
        expected_hash = _stable_hash(
            _baseline_content(
                query=self.query,
                entries=self.entries,
                observation_ids=self.observation_ids,
                input_hash=self.input_hash,
                implementation_version=self.implementation_version,
            )
        )
        if self.baseline_hash != expected_hash:
            raise ValueError("provider baseline hash does not match manifest content")


class ProviderBaselineRepository(Protocol):
    def provider_contract_observations(
        self,
        query: ProviderBaselineQuery,
    ) -> tuple[ProviderContractObservation, ...]: ...

    def save_provider_baseline(self, manifest: ProviderBaselineManifest) -> str: ...


@dataclass(slots=True)
class ProviderBaselineBuilder:
    repository: ProviderBaselineRepository
    clock: Callable[[], datetime] = _utc_now

    def build(self, query: ProviderBaselineQuery) -> ProviderBaselineManifest:
        observations = tuple(
            sorted(
                self.repository.provider_contract_observations(query),
                key=lambda item: (item.scope, item.checked_at, item.check_id),
            )
        )
        allowed_scopes = set(query.scopes)
        if any(item.scope not in allowed_scopes for item in observations):
            raise ValueError("provider baseline repository returned an unexpected scope")
        if any(
            not query.period_start <= item.checked_at <= query.period_end
            for item in observations
        ):
            raise ValueError("provider baseline repository returned an out-of-range check")

        input_hash = _stable_hash(
            [_observation_document(observation) for observation in observations]
        )
        by_scope: dict[ProviderBaselineScope, list[ProviderContractObservation]] = (
            defaultdict(list)
        )
        for observation in observations:
            by_scope[observation.scope].append(observation)
        entries = tuple(
            _entry_for(query, scope, tuple(by_scope[scope]))
            for scope in sorted(query.scopes)
        )
        observation_ids = tuple(sorted(item.check_id for item in observations))
        content = _baseline_content(
            query=query,
            entries=entries,
            observation_ids=observation_ids,
            input_hash=input_hash,
            implementation_version=PROVIDER_CONTRACT_BASELINE_VERSION,
        )
        baseline_hash = _stable_hash(content)
        manifest = ProviderBaselineManifest(
            manifest_id=baseline_hash,
            baseline_hash=baseline_hash,
            input_hash=input_hash,
            query=query,
            entries=entries,
            observation_ids=observation_ids,
            generated_at=self.clock(),
        )
        self.repository.save_provider_baseline(manifest)
        return manifest


def provider_baseline_json(manifest: ProviderBaselineManifest) -> dict[str, object]:
    return {
        "manifest_id": manifest.manifest_id,
        "baseline_hash": manifest.baseline_hash,
        "input_hash": manifest.input_hash,
        "implementation_version": manifest.implementation_version,
        "query": _query_document(manifest.query),
        "entries": [_entry_document(entry) for entry in manifest.entries],
        "observation_ids": list(manifest.observation_ids),
        "trust_policy": (
            "Contract history reports observed trust only and never promotes provider "
            "trust or PIT readiness."
        ),
    }


def serialize_provider_baseline(manifest: ProviderBaselineManifest) -> str:
    return json.dumps(provider_baseline_json(manifest), indent=2, sort_keys=True)


def render_provider_baseline_markdown(manifest: ProviderBaselineManifest) -> str:
    lines = [
        "# Longitudinal Provider Baseline",
        "",
        f"- Period: `{manifest.query.period_start.isoformat()}` to "
        f"`{manifest.query.period_end.isoformat()}`",
        f"- Expected interval: `{manifest.query.expected_interval_days} days`",
        f"- Baseline hash: `{manifest.baseline_hash}`",
        f"- Input hash: `{manifest.input_hash}`",
        f"- Version: `{manifest.implementation_version}`",
        "",
        "| Provider | Dataset | Market | Subject | Checks | Success | "
        "Field coverage | Continuity | Missing periods |",
        "|---|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for entry in manifest.entries:
        lines.append(
            f"| {entry.scope.provider} | {entry.scope.dataset} | "
            f"{entry.scope.market.value} | {entry.scope.subject} | "
            f"{entry.observation_count} | "
            f"{entry.successful_observation_ratio:.1%} | "
            f"{entry.field_coverage_ratio:.1%} | {entry.continuity_ratio:.1%} | "
            f"{len(entry.missing_periods)} |"
        )
    lines.extend(
        [
            "",
            "## Visible Gaps And Failures",
            "",
        ]
    )
    for entry in manifest.entries:
        missing = ", ".join(item.isoformat() for item in entry.missing_periods) or "none"
        failed = ", ".join(entry.failed_check_ids) or "none"
        lines.extend(
            [
                f"### {entry.scope.provider} / {entry.scope.dataset} / "
                f"{entry.scope.market.value} / {entry.scope.subject}",
                "",
                f"- Missing periods: `{missing}`",
                f"- Failed checks: `{failed}`",
                f"- Status counts: `{dict(entry.status_counts)}`",
                f"- Observed trust levels: `{list(entry.observed_trust_levels)}`",
                f"- Observed availability precision: "
                f"`{list(entry.observed_availability_precisions)}`",
                "",
            ]
        )
    lines.extend(
        [
            "Contract history reports observed trust only. It does not upgrade provider "
            "trust, historical continuity, or PIT readiness.",
            "",
        ]
    )
    return "\n".join(lines)


def _entry_for(
    query: ProviderBaselineQuery,
    scope: ProviderBaselineScope,
    observations: tuple[ProviderContractObservation, ...],
) -> ProviderBaselineEntry:
    interval = timedelta(days=query.expected_interval_days)
    expected_periods = max(
        1,
        math.ceil((query.period_end - query.period_start) / interval),
    )
    observed_indexes = {
        min(
            int((observation.checked_at - query.period_start) // interval),
            expected_periods - 1,
        )
        for observation in observations
    }
    missing_periods = tuple(
        query.period_start + index * interval
        for index in range(expected_periods)
        if index not in observed_indexes
    )
    successful = tuple(
        observation
        for observation in observations
        if observation.status
        in {ProviderContractStatus.HEALTHY, ProviderContractStatus.DEGRADED}
        and observation.records_observed > 0
    )
    all_fields = tuple(
        sorted({field for item in observations for field in item.required_fields})
    )
    field_coverage = tuple(
        (
            field,
            _ratio(
                sum(
                    item.records_observed > 0 and field not in item.missing_fields
                    for item in observations
                ),
                len(observations),
            ),
        )
        for field in all_fields
    )
    field_coverage_ratio = (
        _ratio(sum(value for _, value in field_coverage), len(field_coverage))
        if field_coverage
        else 0.0
    )
    status_counts = Counter(item.status.value for item in observations)
    failed = tuple(
        item.check_id
        for item in observations
        if item.status in {ProviderContractStatus.UNAVAILABLE, ProviderContractStatus.DEFECT}
        or item.records_observed == 0
    )
    limitations = tuple(
        sorted({limitation for item in observations for limitation in item.limitations})
    )
    return ProviderBaselineEntry(
        scope=scope,
        expected_periods=expected_periods,
        observed_periods=len(observed_indexes),
        observation_count=len(observations),
        successful_observations=len(successful),
        successful_observation_ratio=_ratio(len(successful), len(observations)),
        field_coverage_ratio=field_coverage_ratio,
        continuity_ratio=_ratio(len(observed_indexes), expected_periods),
        field_coverage=field_coverage,
        status_counts=tuple(sorted(status_counts.items())),
        observed_trust_levels=tuple(
            sorted({item.trust_level.value for item in observations})
        ),
        observed_availability_precisions=tuple(
            sorted({item.availability_precision.value for item in observations})
        ),
        missing_periods=missing_periods,
        failed_check_ids=failed,
        limitations=limitations,
    )


def _query_document(query: ProviderBaselineQuery) -> dict[str, object]:
    return {
        "period_start": query.period_start.isoformat(),
        "period_end": query.period_end.isoformat(),
        "expected_interval_days": query.expected_interval_days,
        "scopes": [_scope_document(scope) for scope in sorted(query.scopes)],
    }


def _baseline_content(
    *,
    query: ProviderBaselineQuery,
    entries: tuple[ProviderBaselineEntry, ...],
    observation_ids: tuple[str, ...],
    input_hash: str,
    implementation_version: str,
) -> dict[str, object]:
    return {
        "implementation_version": implementation_version,
        "input_hash": input_hash,
        "query": _query_document(query),
        "entries": [_entry_document(entry) for entry in entries],
        "observation_ids": list(observation_ids),
    }


def _scope_document(scope: ProviderBaselineScope) -> dict[str, str]:
    return {
        "provider": scope.provider,
        "dataset": scope.dataset,
        "market": scope.market.value,
        "subject": scope.subject,
    }


def _observation_document(observation: ProviderContractObservation) -> dict[str, object]:
    return {
        "check_id": observation.check_id,
        "run_id": observation.run_id,
        "scope": _scope_document(observation.scope),
        "request_as_of": observation.request_as_of.isoformat(),
        "checked_at": observation.checked_at.isoformat(),
        "status": observation.status.value,
        "records_observed": observation.records_observed,
        "trust_level": observation.trust_level.value,
        "availability_precision": observation.availability_precision.value,
        "required_fields": list(observation.required_fields),
        "missing_fields": list(observation.missing_fields),
        "limitations": list(observation.limitations),
        "error_code": observation.error_code,
        "implementation_version": observation.implementation_version,
    }


def _entry_document(entry: ProviderBaselineEntry) -> dict[str, object]:
    return {
        "scope": _scope_document(entry.scope),
        "expected_periods": entry.expected_periods,
        "observed_periods": entry.observed_periods,
        "observation_count": entry.observation_count,
        "successful_observations": entry.successful_observations,
        "successful_observation_ratio": entry.successful_observation_ratio,
        "field_coverage_ratio": entry.field_coverage_ratio,
        "continuity_ratio": entry.continuity_ratio,
        "field_coverage": dict(entry.field_coverage),
        "status_counts": dict(entry.status_counts),
        "observed_trust_levels": list(entry.observed_trust_levels),
        "observed_availability_precisions": list(
            entry.observed_availability_precisions
        ),
        "missing_periods": [item.isoformat() for item in entry.missing_periods],
        "failed_check_ids": list(entry.failed_check_ids),
        "limitations": list(entry.limitations),
    }


def _ratio(numerator: int | float, denominator: int | float) -> float:
    return 0.0 if denominator == 0 else round(float(numerator / denominator), 6)


def _stable_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


__all__ = [
    "ProviderBaselineBuilder",
    "ProviderBaselineEntry",
    "ProviderBaselineManifest",
    "ProviderBaselineQuery",
    "ProviderBaselineRepository",
    "ProviderBaselineScope",
    "ProviderContractObservation",
    "provider_baseline_json",
    "render_provider_baseline_markdown",
    "serialize_provider_baseline",
]
