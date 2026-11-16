"""Publish narrow reviewed issuer facts with their neutral evidence transaction."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.models import IngestionResult
from tong_quant.data.providers.contracts import (
    CNINFO_DISCLOSURES_DATASET,
    ProviderArtifact,
    ProviderDatasetRequest,
    ProviderEvidenceBatch,
)
from tong_quant.data.providers.reviewed_filings import (
    REVIEWED_FILING_DATASET,
    FilingExtractionReview,
    ReviewedFilingAdapter,
)
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import AssetType, AvailabilityPrecision, DataTrustLevel, Market
from tong_quant.domain.models import FundamentalFact, Instrument


@dataclass(frozen=True, slots=True)
class PreparedFilingExtraction:
    adapter: ReviewedFilingAdapter
    request: ProviderDatasetRequest
    batch: ProviderEvidenceBatch
    instrument: Instrument

    def facts(self, batch_id: str) -> tuple[FundamentalFact, ...]:
        return tuple(FundamentalFact(
            instrument=self.instrument, metric=str(record.payload["metric"]),
            period_end=date.fromisoformat(str(record.payload["period_end"])),
            period_start=(date.fromisoformat(str(record.payload["period_start"]))
                          if record.payload["period_start"] else None),
            # Retain the source claim, not a verified historical publication time.
            published_at=self.adapter.source.published_at, available_at=record.available_at,
            value=Decimal(str(record.payload["value"])), source=record.source_reference,
            currency=(str(record.payload["currency"]) if record.payload["currency"] is not None
                      else None),
            unit=str(record.payload["unit"]), revision=0, raw_data_hash=self.batch.raw_data_hash,
            batch_id=batch_id, provider_dataset=REVIEWED_FILING_DATASET,
            availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
            trust_level=record.trust_level,
        ) for record in self.batch.records)


def prepare_filing_extraction(
    store: SQLiteStore,
    artifacts: FileSystemArtifactStore,
    review: FilingExtractionReview,
    *,
    as_of: datetime,
) -> PreparedFilingExtraction:
    request = ProviderDatasetRequest(
        REVIEWED_FILING_DATASET, Market.CHINA_A, review.subject, as_of,
    )
    with store.read_snapshot():
        instrument = store.get_instrument(
            review.subject, Market.CHINA_A, AssetType.EQUITY, as_of=as_of,
        )
        if instrument is None:
            raise ValueError("reviewed filing requires existing visible instrument metadata")
        matches = [row for row in store.provider_artifact_history(
            provider="cninfo_direct", dataset=CNINFO_DISCLOSURES_DATASET, subject=review.subject,
        ) if row["artifact_id"] == review.filing_artifact_id
            and row["content_hash"] == review.filing_sha256
            and datetime.fromisoformat(row["retrieved_at"]) <= as_of]
        if not matches:
            raise ValueError("reviewed filing requires its registered source PDF capture")
        capture = min(matches, key=lambda row: (row["retrieved_at"], row["artifact_id"]))
        content = artifacts.read_content(
            review.filing_sha256, "application/pdf", max_bytes=50 * 1024 * 1024,
        )
        source = ProviderArtifact(
            artifact_id=capture["artifact_id"], provider=capture["provider"],
            dataset=capture["dataset"], market=Market(capture["market"]),
            subject=capture["subject"], source_identity=capture["source_identity"],
            source_reference=capture["source_reference"], content_hash=capture["content_hash"],
            published_at=datetime.fromisoformat(capture["published_at"]),
            retrieved_at=datetime.fromisoformat(capture["retrieved_at"]),
            media_type=capture["media_type"],
            availability_precision=AvailabilityPrecision(capture["availability_precision"]),
            trust_level=DataTrustLevel(capture["trust_level"]), content=content,
        )
        adapter = ReviewedFilingAdapter(review, source)
        batch = adapter.fetch(request)
    return PreparedFilingExtraction(adapter, request, batch, instrument)


def ingest_filing_extraction(
    store: SQLiteStore,
    artifacts: FileSystemArtifactStore,
    review: FilingExtractionReview,
    *,
    as_of: datetime,
) -> IngestionResult:
    prepared = prepare_filing_extraction(store, artifacts, review, as_of=as_of)

    def write_canonical(batch_id: str) -> None:
        store.upsert_fundamental_facts(prepared.facts(batch_id))

    return ProviderNeutralIngestionService(
        store, artifact_store=artifacts, clock=lambda: as_of,
    ).ingest(
        prepared.adapter, prepared.request,
        write_canonical=write_canonical,
    )
