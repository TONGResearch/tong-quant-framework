from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import pytest

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.providers.contracts import (
    ProviderArtifact,
    ProviderCapabilityStatus,
    ProviderDatasetCapability,
    ProviderDatasetRequest,
    ProviderEvidenceBatch,
    ProviderEvidenceRecord,
    provider_artifact_id,
    provider_evidence_id,
)
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market

NOW = datetime(2026, 10, 16, tzinfo=UTC)
CONTENT = b"synthetic evidence, not market data"
RAW_HASH = sha256(CONTENT).hexdigest()
LEVELS = (
    DataTrustLevel.UNKNOWN,
    DataTrustLevel.LOW,
    DataTrustLevel.MEDIUM,
    DataTrustLevel.HIGH,
    DataTrustLevel.VERIFIED,
)
TABLES = (
    "ingestion_batches",
    "raw_dataset_fingerprints",
    "provider_evidence_records",
    "provider_artifacts",
    "provider_artifact_observations",
    "provider_limitations",
    "data_availability_warnings",
)


@dataclass
class _Adapter:
    ceiling: DataTrustLevel
    level: DataTrustLevel
    kind: str
    capability_provider: str = "synthetic"
    provider_id: str = "synthetic"
    fetch_count: int = 0

    def capabilities(self) -> tuple[ProviderDatasetCapability, ...]:
        return (
            ProviderDatasetCapability(
                provider=self.capability_provider,
                dataset="trust_test",
                markets=(Market.CHINA_A,),
                status=ProviderCapabilityStatus.DEGRADED,
                trust_level=self.ceiling,
                availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
                historical_continuity=False,
                required_parameters=(),
                limitations=(),
            ),
        )

    def fetch(self, request: ProviderDatasetRequest) -> ProviderEvidenceBatch:
        self.fetch_count += 1
        payload: dict[str, object] = {"synthetic": True}
        record = ProviderEvidenceRecord(
            evidence_id=provider_evidence_id(
                provider=self.provider_id,
                dataset=request.dataset,
                market=request.market,
                subject=request.subject,
                available_at=NOW,
                source_reference="synthetic",
                payload=payload,
            ),
            provider=self.provider_id,
            dataset=request.dataset,
            market=request.market,
            subject=request.subject,
            available_at=NOW,
            retrieved_at=NOW,
            source_reference="synthetic",
            payload=payload,
            raw_data_hash=RAW_HASH,
            availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
            trust_level=self.level if self.kind == "record" else DataTrustLevel.UNKNOWN,
            limitations=("Synthetic fixture; not readiness evidence",),
        )
        artifact = ProviderArtifact(
            artifact_id=provider_artifact_id(
                provider=self.provider_id,
                dataset=request.dataset,
                market=request.market,
                subject=request.subject,
                source_identity="synthetic",
                source_reference="synthetic",
                content_hash=RAW_HASH,
            ),
            provider=self.provider_id,
            dataset=request.dataset,
            market=request.market,
            subject=request.subject,
            source_identity="synthetic",
            source_reference="synthetic",
            published_at=NOW,
            retrieved_at=NOW,
            content_hash=RAW_HASH,
            media_type="text/plain",
            availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
            trust_level=self.level,
            content=CONTENT,
        )
        return ProviderEvidenceBatch(
            provider=self.provider_id,
            dataset=request.dataset,
            market=request.market,
            retrieved_at=NOW,
            source="synthetic",
            parameters={},
            raw_data_hash=RAW_HASH,
            raw_record_count=1,
            records=(record,),
            limitations=(),
            artifacts=(artifact,) if self.kind == "artifact" else (),
        )


def _request() -> ProviderDatasetRequest:
    return ProviderDatasetRequest("trust_test", Market.CHINA_A, "TEST", NOW)


@pytest.mark.parametrize("ceiling", LEVELS)
@pytest.mark.parametrize("level", LEVELS)
@pytest.mark.parametrize("kind", ("record", "artifact"))
def test_trust_ceiling_covers_every_level_before_any_persistence(
    tmp_path: Path, ceiling: DataTrustLevel, level: DataTrustLevel, kind: str
) -> None:
    store = SQLiteStore(tmp_path / "evidence.sqlite3")
    store.initialize()
    artifact_root = tmp_path / "artifacts"
    service = ProviderNeutralIngestionService(
        store, clock=lambda: NOW, artifact_store=FileSystemArtifactStore(artifact_root)
    )
    adapter = _Adapter(ceiling, level, kind)

    if LEVELS.index(level) > LEVELS.index(ceiling):
        with pytest.raises(ValueError, match="above its capability trust"):
            service.ingest(adapter, _request())
        assert all(store.table_count(table) == 0 for table in TABLES)
        assert not artifact_root.exists()
    else:
        result = service.ingest(adapter, _request())
        assert result.accepted == 1
        records = store.provider_evidence_as_of(
            provider="synthetic",
            dataset="trust_test",
            market=Market.CHINA_A,
            subject="TEST",
            as_of=NOW,
        )
        assert records[0]["trust_level"] == (
            level.value if kind == "record" else DataTrustLevel.UNKNOWN.value
        )
        assert records[0]["availability_precision"] == "retrieval_time"
        assert "Synthetic fixture" in records[0]["limitations_json"]
        if kind == "artifact":
            with store._connect() as connection:
                saved = connection.execute("SELECT * FROM provider_artifacts").fetchone()
            assert saved["trust_level"] == level.value
            assert saved["availability_precision"] == "retrieval_time"
    assert adapter.fetch_count == 1


def test_capability_cannot_borrow_another_provider_identity(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "evidence.sqlite3")
    store.initialize()
    adapter = _Adapter(
        DataTrustLevel.HIGH, DataTrustLevel.HIGH, "record", capability_provider="other"
    )
    with pytest.raises(ValueError, match="capability has the wrong provider identity"):
        ProviderNeutralIngestionService(store, clock=lambda: NOW).ingest(adapter, _request())
    assert adapter.fetch_count == 0
    assert all(store.table_count(table) == 0 for table in TABLES)


def test_relaxed_pit_does_not_relax_the_trust_ceiling(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "evidence.sqlite3")
    store.initialize()
    adapter = _Adapter(DataTrustLevel.LOW, DataTrustLevel.HIGH, "record")
    with pytest.raises(ValueError, match="above its capability trust"):
        ProviderNeutralIngestionService(
            store, strict_point_in_time=False, clock=lambda: NOW
        ).ingest(adapter, _request())
    assert all(store.table_count(table) == 0 for table in TABLES)
