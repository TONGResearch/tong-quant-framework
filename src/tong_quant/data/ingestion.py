import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import ClassVar
from uuid import uuid4

from tong_quant.core.exceptions import DataProviderError
from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.artifacts import ProviderArtifactStore, StoredProviderArtifact
from tong_quant.data.models import (
    DataAvailabilityWarning,
    IngestionBatch,
    IngestionResult,
    ProviderLimitation,
    RawDatasetFingerprint,
)
from tong_quant.data.providers.contracts import (
    ProviderCapabilityStatus,
    ProviderDatasetCapability,
    ProviderDatasetRequest,
    ProviderEvidenceAdapter,
    ProviderEvidenceBatch,
)
from tong_quant.data.refresh_attempts import RefreshLease
from tong_quant.data.storage.refresh import SQLiteRefreshRepository
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import DataTrustLevel, IngestionBatchStatus
from tong_quant.domain.models import require_timezone
from tong_quant.version import PROVIDER_INGESTION_PRIVACY_VERSION, PROVIDER_INGESTION_TIMING_VERSION


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class ProviderNeutralIngestionService:
    timing_version: ClassVar[str] = PROVIDER_INGESTION_TIMING_VERSION
    privacy_version: ClassVar[str] = PROVIDER_INGESTION_PRIVACY_VERSION
    store: SQLiteStore
    strict_point_in_time: bool = True
    clock: Callable[[], datetime] = _utc_now
    artifact_store: ProviderArtifactStore | None = None

    def ingest(
        self,
        adapter: ProviderEvidenceAdapter,
        request: ProviderDatasetRequest,
        *,
        write_canonical: Callable[[str], None] | None = None,
        refresh_lease: RefreshLease | None = None,
    ) -> IngestionResult:
        request.__post_init__()
        refresh = (None if refresh_lease is None
                   else SQLiteRefreshRepository(self.store, clock=self.clock))
        if refresh is not None and refresh_lease is not None:
            refresh.validate_live_lease(refresh_lease)
        capability = _resolve_capability(adapter, request)
        if capability.status is ProviderCapabilityStatus.UNAVAILABLE:
            raise DataProviderError(
                f"provider {adapter.provider_id} dataset {request.dataset} is unavailable"
            )
        batch = adapter.fetch(request)
        self._validate_batch(adapter, request, capability, batch)
        _privacy_preflight(batch)
        if refresh is not None and refresh_lease is not None:
            refresh.validate_retention(refresh_lease, request, batch)

        batch_id = str(uuid4())
        completed_at = self.clock()
        require_timezone(completed_at, "ingestion completion")
        if completed_at.astimezone(UTC) < batch.retrieved_at.astimezone(UTC):
            raise ValueError("ingestion completion cannot precede provider retrieval")
        stored_artifacts = self._store_artifacts(batch)
        warnings = tuple(limitation.description for limitation in batch.limitations)
        if not batch.records:
            warnings = (*warnings, "Provider response produced no normalized evidence")

        try:
            with self.store.transaction():
                self.store.save_ingestion_batch(
                    IngestionBatch(
                        batch_id=batch_id,
                        provider=batch.provider,
                        dataset=batch.dataset,
                        started_at=batch.retrieved_at,
                        completed_at=completed_at,
                        status=IngestionBatchStatus.COMPLETED,
                        parameters=batch.parameters,
                        raw_response_hash=batch.raw_data_hash,
                    )
                )
                self.store.save_raw_dataset_fingerprint(
                    RawDatasetFingerprint(
                        dataset=batch.dataset,
                        provider=batch.provider,
                        raw_data_hash=batch.raw_data_hash,
                        retrieved_at=batch.retrieved_at,
                        parameters=batch.parameters,
                        row_count=batch.raw_record_count,
                        source=batch.source,
                    )
                )
                self.store.save_provider_evidence_records(
                    batch.records,
                    batch_id=batch_id,
                )
                self.store.save_provider_artifacts(
                    stored_artifacts,
                    batch_id=batch_id,
                )
                self.store.save_provider_artifact_observations(
                    batch.artifact_observations,
                    batch_id=batch_id,
                )
                if write_canonical is not None:
                    # Canonical rows and their evidence must commit or roll back together.
                    write_canonical(batch_id)
                for limitation in batch.limitations:
                    self.store.save_provider_limitation(
                        ProviderLimitation(
                            provider=batch.provider,
                            dataset=batch.dataset,
                            limitation_code=limitation.code,
                            description=limitation.description,
                            trust_level=limitation.trust_level,
                            documented_at=completed_at,
                        )
                    )
                    self.store.save_data_availability_warning(
                        DataAvailabilityWarning(
                            batch_id=batch_id,
                            dataset=batch.dataset,
                            warning_code=limitation.code,
                            message=limitation.description,
                            trust_level=limitation.trust_level,
                            created_at=completed_at,
                        )
                    )
                if not batch.records:
                    self.store.save_data_availability_warning(
                        DataAvailabilityWarning(
                            batch_id=batch_id,
                            dataset=batch.dataset,
                            warning_code="no_normalized_evidence",
                            message="Provider response produced no normalized evidence",
                            trust_level=DataTrustLevel.UNKNOWN,
                            created_at=completed_at,
                        )
                    )
                if refresh is not None and refresh_lease is not None:
                    refresh.attach_ingestion(refresh_lease, request, batch, batch_id)
        except Exception:
            self._discard_created_artifacts(stored_artifacts)
            raise

        return IngestionResult(
            dataset=batch.dataset,
            received=batch.raw_record_count,
            accepted=len(batch.records),
            rejected=max(batch.raw_record_count - len(batch.records), 0),
            cached=False,
            batch_id=batch_id,
            warnings=warnings,
        )

    def _validate_batch(
        self,
        adapter: ProviderEvidenceAdapter,
        request: ProviderDatasetRequest,
        capability: ProviderDatasetCapability,
        batch: ProviderEvidenceBatch,
    ) -> None:
        request.__post_init__()
        batch.__post_init__()
        if batch.provider != adapter.provider_id:
            raise ValueError("provider evidence batch has the wrong provider identity")
        if batch.dataset != request.dataset or batch.market != request.market:
            raise ValueError("provider evidence batch does not match its request")
        if self.strict_point_in_time:
            for record in batch.records:
                evidence_times = (
                    record.available_at,
                    record.observed_at,
                    record.published_at,
                )
                if any(
                    evidence_time is not None
                    and evidence_time.astimezone(UTC) > request.as_of.astimezone(UTC)
                    for evidence_time in evidence_times
                ):
                    raise ValueError("provider evidence contains future event data")
        for record in batch.records:
            _require_trust_ceiling(record.trust_level, capability.trust_level)
        for artifact in batch.artifacts:
            _require_trust_ceiling(artifact.trust_level, capability.trust_level)
        if self.strict_point_in_time and any(
            artifact.published_at.astimezone(UTC) > request.as_of.astimezone(UTC)
            for artifact in batch.artifacts
        ):
            raise ValueError("provider artifacts contain future publication data")
        if self.strict_point_in_time and any(
            observation.published_at.astimezone(UTC) > request.as_of.astimezone(UTC)
            for observation in batch.artifact_observations
        ):
            raise ValueError("artifact observations contain future publication data")

    def _store_artifacts(
        self,
        batch: ProviderEvidenceBatch,
    ) -> tuple[StoredProviderArtifact, ...]:
        if not batch.artifacts:
            return ()
        if self.artifact_store is None:
            raise ValueError("provider artifact ingestion requires an artifact store")
        stored: list[StoredProviderArtifact] = []
        try:
            for artifact in batch.artifacts:
                stored.append(self.artifact_store.put(artifact))
        except Exception:
            self._discard_created_artifacts(tuple(stored))
            raise
        return tuple(stored)

    def _discard_created_artifacts(
        self,
        stored: tuple[StoredProviderArtifact, ...],
    ) -> None:
        if self.artifact_store is None:
            return
        for artifact in reversed(stored):
            self.artifact_store.discard(artifact)


def _privacy_preflight(batch: ProviderEvidenceBatch) -> None:
    """Reject known credential forms before publishing non-deletable source bytes."""
    try:
        reject_sensitive_structure(asdict(batch), path="provider_batch")
        for artifact in batch.artifacts:
            media_type = artifact.media_type.partition(";")[0].strip().lower()
            if media_type == "application/json" or media_type.endswith("+json"):
                decoded = json.loads(artifact.content, object_pairs_hook=_screen_json_pairs)
                reject_sensitive_structure(decoded, path="provider_artifact.json")
                continue
            try:
                text = artifact.content.decode("utf-8-sig")
            except UnicodeError:
                if media_type.startswith("text/") or "xml" in media_type:
                    raise ValueError("unsupported text encoding") from None
                # Opaque binary originals are not certified credential-free by this scan.
                continue
            reject_sensitive_structure(text, path="provider_artifact.content")
            if text.lstrip().startswith(("{", "[")):
                decoded = json.loads(text, object_pairs_hook=_screen_json_pairs)
                reject_sensitive_structure(decoded, path="provider_artifact.json")
    except (ValueError, UnicodeError, RecursionError):
        # Do not propagate source values, JSON fragments or attacker-controlled key paths.
        raise ValueError("provider batch failed credential privacy preflight") from None


def _screen_json_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    for key, value in pairs:
        # Check every occurrence before duplicate JSON keys can discard earlier values.
        reject_sensitive_structure({key: value}, path="provider_artifact.json")
    return dict(pairs)


def _resolve_capability(
    adapter: ProviderEvidenceAdapter,
    request: ProviderDatasetRequest,
) -> ProviderDatasetCapability:
    matches = tuple(
        capability
        for capability in adapter.capabilities()
        if capability.dataset == request.dataset and request.market in capability.markets
    )
    if len(matches) != 1:
        raise ValueError(
            f"provider {adapter.provider_id} must declare exactly one capability for "
            f"{request.dataset}/{request.market.value}"
        )
    capability = matches[0]
    if capability.provider != adapter.provider_id:
        raise ValueError("provider capability has the wrong provider identity")
    missing = tuple(
        parameter
        for parameter in capability.required_parameters
        if not request.parameters.get(parameter, "").strip()
    )
    if missing:
        raise ValueError(f"provider request is missing parameters: {', '.join(missing)}")
    return capability


def _require_trust_ceiling(level: DataTrustLevel, ceiling: DataTrustLevel) -> None:
    # Trust is ordered; availability precision is a separate, non-ranked concept.
    levels = (
        DataTrustLevel.UNKNOWN,
        DataTrustLevel.LOW,
        DataTrustLevel.MEDIUM,
        DataTrustLevel.HIGH,
        DataTrustLevel.VERIFIED,
    )
    if levels.index(level) > levels.index(ceiling):
        raise ValueError("adapter cannot promote evidence above its capability trust")


__all__ = ["ProviderNeutralIngestionService"]
