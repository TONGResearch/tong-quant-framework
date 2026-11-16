"""Synthetic ingestion clocks exercise PIT guards, never provider trust or real coverage."""

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pytest

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.models import IngestionBatch
from tong_quant.data.providers.contracts import (
    ProviderArtifact,
    ProviderArtifactObservation,
    ProviderArtifactStatus,
    ProviderCapabilityStatus,
    ProviderDatasetCapability,
    ProviderDatasetRequest,
    ProviderEvidenceBatch,
    ProviderEvidenceRecord,
)
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import (
    AvailabilityPrecision,
    DataTrustLevel,
    IngestionBatchStatus,
    Market,
)

FIRST = datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo("America/New_York"), fold=0)
SECOND = FIRST.replace(fold=1)
CONTENT = b"Synthetic UTC evidence only"
DIGEST = sha256(CONTENT).hexdigest()
TABLES = (
    "ingestion_batches", "raw_dataset_fingerprints", "provider_evidence_records",
    "provider_artifacts", "provider_artifact_observations", "provider_limitations",
    "data_availability_warnings",
)


def _batch(retrieved_at=SECOND):
    record = ProviderEvidenceRecord(
        DIGEST, "synthetic", "utc_test", Market.US, "TEST", FIRST, retrieved_at,
        "synthetic", {"fixture": True}, DIGEST, AvailabilityPrecision.RETRIEVAL_TIME,
        DataTrustLevel.LOW, ("Synthetic fixture, not source qualification",),
    )
    artifact = ProviderArtifact(
        DIGEST, "synthetic", "utc_test", Market.US, "TEST", "synthetic", "synthetic",
        FIRST, retrieved_at, DIGEST, "text/plain", AvailabilityPrecision.RETRIEVAL_TIME,
        DataTrustLevel.LOW, CONTENT,
    )
    observation = ProviderArtifactObservation(
        DIGEST, "synthetic", "utc_test", Market.US, "TEST", "synthetic", "synthetic",
        FIRST, retrieved_at, ProviderArtifactStatus.CAPTURED, artifact.artifact_id, "",
    )
    return ProviderEvidenceBatch(
        "synthetic", "utc_test", Market.US, retrieved_at, "synthetic", {}, DIGEST, 1,
        (record,), (), (artifact,), (observation,),
    )


@dataclass
class _Adapter:
    batch: ProviderEvidenceBatch
    provider_id: str = "synthetic"
    fetched: bool = False

    def capabilities(self):
        return (ProviderDatasetCapability(
            self.provider_id, "utc_test", (Market.US,), ProviderCapabilityStatus.DEGRADED,
            DataTrustLevel.LOW, AvailabilityPrecision.RETRIEVAL_TIME, False, (), (),
        ),)

    def fetch(self, request):
        self.fetched = True
        return self.batch


@pytest.fixture
def foundation(tmp_path):
    store = SQLiteStore(tmp_path / "utc.sqlite3")
    store.initialize()
    return store, FileSystemArtifactStore(tmp_path / "artifacts")


@pytest.mark.parametrize("kind", ["available", "observed", "published", "artifact", "observation"])
@pytest.mark.parametrize("utc_cutoff", [False, True])
def test_future_fold_evidence_rejected_before_artifact_or_database_publication(
    foundation, kind, utc_cutoff,
):
    store, artifacts = foundation
    batch = _batch()
    if kind == "available":
        batch = replace(batch, records=(replace(batch.records[0], available_at=SECOND),))
    elif kind == "observed":
        batch = replace(batch, records=(replace(batch.records[0], observed_at=SECOND),))
    elif kind == "published":
        batch = replace(batch, records=(replace(
            batch.records[0], available_at=SECOND, published_at=SECOND),))
    elif kind == "artifact":
        batch = replace(batch, artifacts=(replace(batch.artifacts[0], published_at=SECOND),))
    else:
        batch = replace(batch, artifact_observations=(replace(
            batch.artifact_observations[0], published_at=SECOND),))
    request = ProviderDatasetRequest(
        "utc_test", Market.US, "TEST", FIRST.astimezone(UTC) if utc_cutoff else FIRST)
    canonical = Mock()
    with pytest.raises(ValueError, match="future"):
        ProviderNeutralIngestionService(
            store, artifact_store=artifacts, clock=lambda: SECOND,
        ).ingest(_Adapter(batch), request, write_canonical=canonical)
    canonical.assert_not_called()
    assert all(store.table_count(table) == 0 for table in TABLES)
    assert not artifacts.root.exists()


@pytest.mark.parametrize("kind", ["available", "published", "observed", "artifact", "observation"])
def test_provider_contracts_reject_reversed_actual_fold_chronology(kind):
    batch = _batch(FIRST)
    with pytest.raises(ValueError):
        if kind == "available":
            replace(batch.records[0], available_at=SECOND)
        elif kind == "published":
            replace(batch.records[0], published_at=SECOND)
        elif kind == "observed":
            replace(batch.records[0], observed_at=SECOND)
        elif kind == "artifact":
            replace(batch.artifacts[0], published_at=SECOND)
        else:
            replace(batch.artifact_observations[0], published_at=SECOND)


@pytest.mark.parametrize("kind", ["record", "artifact", "observation"])
def test_batch_retrieval_binding_distinguishes_actual_fold_instants(kind):
    batch = _batch()
    with pytest.raises(ValueError, match="does not match its batch"):
        if kind == "record":
            replace(batch, records=(replace(batch.records[0], retrieved_at=FIRST),))
        elif kind == "artifact":
            replace(batch, artifacts=(replace(batch.artifacts[0], retrieved_at=FIRST),))
        else:
            replace(batch, artifact_observations=(replace(
                batch.artifact_observations[0], retrieved_at=FIRST),))


@pytest.mark.parametrize("kind", ["record", "artifact", "observation"])
def test_batch_retrieval_binding_accepts_equivalent_utc_representation(kind):
    batch = _batch()
    if kind == "record":
        result = replace(batch, records=(replace(
            batch.records[0], retrieved_at=SECOND.astimezone(UTC)),))
    elif kind == "artifact":
        result = replace(batch, artifacts=(replace(
            batch.artifacts[0], retrieved_at=SECOND.astimezone(UTC)),))
    else:
        result = replace(batch, artifact_observations=(replace(
            batch.artifact_observations[0], retrieved_at=SECOND.astimezone(UTC)),))
    assert result.retrieved_at is SECOND


@pytest.mark.parametrize("kind", ["record", "artifact", "observation", "batch"])
def test_ingestion_revalidates_mutated_returned_contract_before_publication(foundation, kind):
    store, artifacts = foundation
    batch = _batch()
    target = {"record": batch.records[0], "artifact": batch.artifacts[0],
              "observation": batch.artifact_observations[0], "batch": batch}[kind]
    object.__setattr__(target, "retrieved_at", FIRST - timedelta(days=1))
    canonical = Mock()
    with pytest.raises(ValueError):
        ProviderNeutralIngestionService(
            store, artifact_store=artifacts, clock=lambda: SECOND,
        ).ingest(_Adapter(batch), ProviderDatasetRequest(
            "utc_test", Market.US, "TEST", SECOND), write_canonical=canonical)
    canonical.assert_not_called()
    assert all(store.table_count(table) == 0 for table in TABLES)
    assert not artifacts.root.exists()


def test_naive_completion_clock_fails_before_artifact_publication(foundation):
    store, artifacts = foundation
    with pytest.raises(ValueError, match="timezone"):
        ProviderNeutralIngestionService(
            store, artifact_store=artifacts, clock=lambda: SECOND.replace(tzinfo=None),
        ).ingest(_Adapter(_batch()), ProviderDatasetRequest("utc_test", Market.US, "TEST", SECOND))
    assert all(store.table_count(table) == 0 for table in TABLES)
    assert not artifacts.root.exists()


def test_actual_completion_cannot_precede_retrieval_with_equal_local_clock(foundation):
    store, artifacts = foundation
    with pytest.raises(ValueError, match="completion cannot precede"):
        ProviderNeutralIngestionService(
            store, artifact_store=artifacts, clock=lambda: FIRST,
        ).ingest(_Adapter(_batch()), ProviderDatasetRequest("utc_test", Market.US, "TEST", SECOND))
    assert all(store.table_count(table) == 0 for table in TABLES)
    assert not artifacts.root.exists()


def test_later_actual_completion_with_earlier_wall_clock_is_valid(foundation):
    store, artifacts = foundation
    retrieved = FIRST.replace(minute=45)
    completed = SECOND.replace(minute=15)
    batch = _batch(retrieved)
    result = ProviderNeutralIngestionService(
        store, artifact_store=artifacts, clock=lambda: completed,
    ).ingest(_Adapter(batch), ProviderDatasetRequest("utc_test", Market.US, "TEST", completed))
    assert result.accepted == 1
    assert store.table_count("provider_artifacts") == 1
    assert store.table_count("provider_evidence_records") == 1
    with store._connect() as connection:
        row = connection.execute(
            "SELECT started_at, completed_at FROM ingestion_batches").fetchone()
    assert datetime.fromisoformat(row["completed_at"]) > datetime.fromisoformat(row["started_at"])


def test_ingestion_batch_model_rejects_earlier_actual_completion():
    with pytest.raises(ValueError, match="completed_at cannot precede"):
        IngestionBatch("synthetic", "synthetic", "utc_test", SECOND,
                       IngestionBatchStatus.COMPLETED, DIGEST, completed_at=FIRST)


def test_relaxed_pit_preserves_visible_limits_without_claiming_historical_safety(foundation):
    store, artifacts = foundation
    batch = _batch()
    batch = replace(batch, records=(replace(batch.records[0], available_at=SECOND),))
    result = ProviderNeutralIngestionService(
        store, strict_point_in_time=False, artifact_store=artifacts, clock=lambda: SECOND,
    ).ingest(_Adapter(batch), ProviderDatasetRequest("utc_test", Market.US, "TEST", FIRST))
    assert result.accepted == 1
    assert store.provider_evidence_as_of(provider="synthetic", dataset="utc_test",
        market=Market.US, subject="TEST", as_of=FIRST) == []


def test_relaxed_pit_cannot_disable_contract_chronology_or_publish_files(foundation):
    store, artifacts = foundation
    batch = _batch()
    object.__setattr__(batch.records[0], "available_at",
                       SECOND.astimezone(UTC) + timedelta(seconds=1))
    with pytest.raises(ValueError, match="available after retrieval"):
        ProviderNeutralIngestionService(
            store, strict_point_in_time=False, artifact_store=artifacts, clock=lambda: SECOND,
        ).ingest(_Adapter(batch), ProviderDatasetRequest("utc_test", Market.US, "TEST", SECOND))
    assert all(store.table_count(table) == 0 for table in TABLES)
    assert not artifacts.root.exists()


def test_mutated_naive_request_is_rejected_before_provider_fetch(foundation):
    store, artifacts = foundation
    request = ProviderDatasetRequest("utc_test", Market.US, "TEST", SECOND)
    object.__setattr__(request, "as_of", SECOND.replace(tzinfo=None))
    adapter = _Adapter(_batch())
    with pytest.raises(ValueError, match="timezone"):
        ProviderNeutralIngestionService(
            store, artifact_store=artifacts, clock=lambda: SECOND,
        ).ingest(adapter, request)
    assert not adapter.fetched
    assert all(store.table_count(table) == 0 for table in TABLES)
    assert not artifacts.root.exists()
