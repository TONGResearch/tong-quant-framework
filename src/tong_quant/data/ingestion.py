from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from tong_quant.core.exceptions import DataProviderError
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
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import DataTrustLevel, IngestionBatchStatus


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class ProviderNeutralIngestionService:
    store: SQLiteStore
    strict_point_in_time: bool = True
    clock: Callable[[], datetime] = _utc_now

    def ingest(
        self,
        adapter: ProviderEvidenceAdapter,
        request: ProviderDatasetRequest,
    ) -> IngestionResult:
        capability = _resolve_capability(adapter, request)
        if capability.status is ProviderCapabilityStatus.UNAVAILABLE:
            raise DataProviderError(
                f"provider {adapter.provider_id} dataset {request.dataset} is unavailable"
            )
        batch = adapter.fetch(request)
        self._validate_batch(adapter, request, capability, batch)

        batch_id = str(uuid4())
        completed_at = self.clock()
        if completed_at < batch.retrieved_at:
            raise ValueError("ingestion completion cannot precede provider retrieval")
        warnings = tuple(limitation.description for limitation in batch.limitations)
        if not batch.records:
            warnings = (*warnings, "Provider response produced no normalized evidence")

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
            self.store.save_provider_evidence_records(batch.records, batch_id=batch_id)
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
                    evidence_time is not None and evidence_time > request.as_of
                    for evidence_time in evidence_times
                ):
                    raise ValueError("provider evidence contains future event data")
        if capability.trust_level is not DataTrustLevel.VERIFIED and any(
            record.trust_level is DataTrustLevel.VERIFIED for record in batch.records
        ):
            raise ValueError("adapter cannot promote evidence above its capability trust")


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
    missing = tuple(
        parameter
        for parameter in capability.required_parameters
        if not request.parameters.get(parameter, "").strip()
    )
    if missing:
        raise ValueError(f"provider request is missing parameters: {', '.join(missing)}")
    return capability


__all__ = ["ProviderNeutralIngestionService"]
