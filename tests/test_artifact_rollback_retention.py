"""Synthetic shared-byte races; no real original files, provider calls or readiness admission."""

import subprocess
import sys
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from hashlib import sha256
from unittest.mock import Mock

import pytest

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.providers.contracts import (
    EvidenceLimitation,
    ProviderArtifact,
    ProviderCapabilityStatus,
    ProviderDatasetCapability,
    ProviderDatasetRequest,
    ProviderEvidenceBatch,
    ProviderEvidenceRecord,
)
from tong_quant.data.storage.artifact_audit import audit_provider_artifacts
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market
from tong_quant.version import ARTIFACT_STORAGE_VERSION

NOW = datetime(2026, 11, 4, tzinfo=UTC)
CONTENT = b"Synthetic shared original; not issuer evidence"
DIGEST = sha256(CONTENT).hexdigest()


def _artifact(content=CONTENT, media_type="text/plain"):
    digest = sha256(content).hexdigest()
    return ProviderArtifact(
        digest,
        "synthetic",
        "rollback_test",
        Market.US,
        "TEST",
        "synthetic",
        "synthetic",
        NOW,
        NOW,
        digest,
        media_type,
        AvailabilityPrecision.RETRIEVAL_TIME,
        DataTrustLevel.LOW,
        content,
    )


@dataclass
class _Captured:
    artifact: ProviderArtifact
    provider_id: str = "synthetic"

    def capabilities(self):
        return (
            ProviderDatasetCapability(
                "synthetic",
                "rollback_test",
                (Market.US,),
                ProviderCapabilityStatus.DEGRADED,
                DataTrustLevel.LOW,
                AvailabilityPrecision.RETRIEVAL_TIME,
                False,
                (),
                (),
            ),
        )

    def fetch(self, request):
        return ProviderEvidenceBatch(
            "synthetic",
            "rollback_test",
            Market.US,
            NOW,
            "synthetic",
            {},
            self.artifact.content_hash,
            0,
            (),
            (),
            (self.artifact,),
        )


def _ingest(store, artifacts, artifact=None):
    return ProviderNeutralIngestionService(
        store, artifact_store=artifacts, clock=lambda: NOW
    ).ingest(
        _Captured(artifact or _artifact()),
        ProviderDatasetRequest("rollback_test", Market.US, "TEST", NOW),
    )


@pytest.mark.parametrize("location", [
    "parameters", "batch_source", "payload", "record_source", "record_limitations",
    "batch_limitations", "artifact_source", "json", "duplicate_json", "text", "bad_json",
    "bom_object", "bom_array", "bom_duplicate",
])
def test_privacy_failure_precedes_every_artifact_put_and_all_database_writes(tmp_path, location):
    marker = "synthetic-privacy-marker"
    artifact = _artifact()
    batch = _Captured(artifact).fetch(None)
    record = ProviderEvidenceRecord(
        "a" * 64, batch.provider, batch.dataset, batch.market, "TEST", NOW, NOW,
        "synthetic", {}, batch.raw_data_hash, AvailabilityPrecision.RETRIEVAL_TIME,
        DataTrustLevel.LOW, (),
    )
    if location == "parameters":
        batch = replace(batch, parameters={"api_key": marker})
    elif location == "batch_source":
        batch = replace(batch, source=f"token={marker}")
    elif location == "batch_limitations":
        batch = replace(batch, limitations=(
            EvidenceLimitation("synthetic", f"password={marker}", DataTrustLevel.LOW),
        ))
    elif location in {"payload", "record_source", "record_limitations"}:
        if location == "payload":
            record = replace(record, payload={"nested": {"api_key": marker}})
        elif location == "record_source":
            record = replace(record, source_reference=f"https://example.test/?token={marker}")
        else:
            record = replace(record, limitations=(f"secret={marker}",))
        batch = replace(batch, raw_record_count=1, records=(record,))
    else:
        if location == "artifact_source":
            artifact = replace(artifact, source_reference=f"token={marker}")
        else:
            content = {
                "json": b'{"nested":{"api_key":"synthetic-privacy-marker"}}',
                "duplicate_json": b'{"x":{"token":"synthetic-privacy-marker"},"x":0}',
                "text": b"password=synthetic-privacy-marker",
                "bad_json": b'{"truncated":',
                "bom_object": b'\xef\xbb\xbf{"api_key":"synthetic-privacy-marker"}',
                "bom_array": b'\xef\xbb\xbf[{"password":"synthetic-privacy-marker"}]',
                "bom_duplicate": (
                    b'\xef\xbb\xbf{"x":{"token":"synthetic-privacy-marker"},"x":0}'
                ),
            }[location]
            media_type = ("text/plain" if location == "text" or location.startswith("bom_")
                          else "application/json")
            artifact = _artifact(content, media_type)
        batch = replace(batch, artifacts=(artifact,))

    class Adapter(_Captured):
        def fetch(self, request):
            return batch

    store = SQLiteStore(tmp_path / "privacy.sqlite3")
    store.initialize()
    artifact_root = tmp_path / "originals"
    artifacts = FileSystemArtifactStore(artifact_root)
    put = Mock(wraps=artifacts.put)
    wrapped = Mock(wraps=artifacts)
    wrapped.put = put
    with pytest.raises(ValueError, match="credential privacy preflight") as error:
        ProviderNeutralIngestionService(
            store, artifact_store=wrapped, clock=lambda: NOW
        ).ingest(Adapter(artifact), ProviderDatasetRequest("rollback_test", Market.US, "TEST", NOW))
    assert marker not in str(error.value)
    put.assert_not_called()
    assert not any(path.is_file() for path in artifact_root.rglob("*"))
    for table in ("ingestion_batches", "raw_dataset_fingerprints", "provider_evidence_records",
                  "provider_artifacts", "provider_artifact_observations"):
        assert store.table_count(table) == 0


def test_clean_bom_json_inspection_preserves_original_bytes_and_hash(tmp_path):
    content = b'\xef\xbb\xbf{"public_observation":12}'
    artifact = _artifact(content, "text/plain")
    artifacts = FileSystemArtifactStore(tmp_path / "originals")
    store = SQLiteStore(tmp_path / "privacy.sqlite3")
    store.initialize()
    result = _ingest(store, artifacts, artifact)
    assert store.ingestion_batch(result.batch_id) is not None
    assert artifacts.read_content(
        artifact.content_hash, artifact.media_type, max_bytes=1024
    ) == content
    assert artifact.content_hash == sha256(content).hexdigest()


@pytest.mark.parametrize("media_type", ["text/plain", "application/pdf", "application/json"])
def test_creator_rollback_cannot_delete_bytes_already_adopted_by_another_store(
    tmp_path, media_type
):
    artifact = _artifact(media_type=media_type)
    root = tmp_path / "shared"
    first = FileSystemArtifactStore(root)
    second = FileSystemArtifactStore(root)
    receipt = first.put(artifact)
    adopted = second.put(artifact)
    assert receipt.created and not adopted.created
    first.discard(receipt)
    assert (
        second.read_content(artifact.content_hash, artifact.media_type, max_bytes=1024) == CONTENT
    )
    assert second.model_version == ARTIFACT_STORAGE_VERSION


@pytest.mark.parametrize("same_database", [True, False])
def test_committed_registry_stays_verifiable_after_another_writer_rolls_back(
    tmp_path, same_database
):
    root = tmp_path / "shared"
    artifact = _artifact()
    creating_store = FileSystemArtifactStore(root)
    receipt = creating_store.put(artifact)
    first_database = SQLiteStore(tmp_path / "first.sqlite3")
    first_database.initialize()
    committed = first_database if same_database else SQLiteStore(tmp_path / "second.sqlite3")
    if not same_database:
        committed.initialize()
    result = _ingest(committed, FileSystemArtifactStore(root), artifact)
    creating_store.discard(receipt)
    assert committed.ingestion_batch(result.batch_id) is not None
    report = audit_provider_artifacts(committed.path, root)
    assert report["registered_count"] == report["verified_count"] == 1
    assert report["registered_artifacts_verified"] is True


def test_real_child_process_commits_before_creator_abandons_file(tmp_path):
    root = tmp_path / "shared"
    creator = FileSystemArtifactStore(root)
    receipt = creator.put(_artifact())
    database = tmp_path / "adopter.sqlite3"
    code = """
import sys
from pathlib import Path
from datetime import UTC, datetime
from hashlib import sha256
from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.models import IngestionBatch
from tong_quant.data.providers.contracts import ProviderArtifact
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import (
    Market, AvailabilityPrecision, DataTrustLevel, IngestionBatchStatus,
)
content = b'Synthetic shared original; not issuer evidence'
digest = sha256(content).hexdigest()
now = datetime(2026,11,4,tzinfo=UTC)
artifact = ProviderArtifact(digest,'synthetic','rollback_test',Market.US,'TEST',
    'synthetic','synthetic',now,now,digest,'text/plain',
    AvailabilityPrecision.RETRIEVAL_TIME,DataTrustLevel.LOW,content)
store = SQLiteStore(Path(sys.argv[1]))
store.initialize()
adopted = FileSystemArtifactStore(Path(sys.argv[2])).put(artifact)
assert not adopted.created
with store.transaction():
    store.save_ingestion_batch(IngestionBatch('committed','synthetic','rollback_test',now,
        IngestionBatchStatus.COMPLETED,digest,completed_at=now))
    store.save_provider_artifacts((adopted,),batch_id='committed')
"""
    subprocess.run(
        [sys.executable, "-c", code, str(database), str(root)],
        check=True,
        capture_output=True,
        timeout=20,
    )
    creator.discard(receipt)
    assert audit_provider_artifacts(database, root)["registered_artifacts_verified"] is True


def test_database_rollback_preserves_original_without_publishing_or_promoting_it(tmp_path):
    class FailingStore(SQLiteStore):
        def save_provider_artifacts(self, *args, **kwargs):
            raise RuntimeError("synthetic storage failure")

    store = FailingStore(tmp_path / "failed.sqlite3")
    store.initialize()
    artifacts = FileSystemArtifactStore(tmp_path / "originals")
    with pytest.raises(RuntimeError, match="synthetic storage failure"):
        _ingest(store, artifacts)
    for table in (
        "ingestion_batches",
        "provider_artifacts",
        "provider_evidence_records",
        "raw_dataset_fingerprints",
        "research_reports",
        "signals",
        "daily_bars",
    ):
        assert store.table_count(table) == 0
    assert artifacts.read_content(DIGEST, "text/plain", max_bytes=1024) == CONTENT
    report = audit_provider_artifacts(store.path, artifacts.root)
    assert report["registered_count"] == 0 and not report["registered_artifacts_verified"]
    assert "unregistered files are not inventoried" in " ".join(report["limitations"])


def test_partial_artifact_failure_does_not_erase_earlier_shared_content(tmp_path, monkeypatch):
    artifacts = FileSystemArtifactStore(tmp_path / "originals")
    store = SQLiteStore(tmp_path / "failed.sqlite3")
    store.initialize()
    first, second = _artifact(), _artifact(b"second synthetic document")
    batch = _Captured(first).fetch(None)
    batch = replace(batch, artifacts=(first, second))
    original = FileSystemArtifactStore.put

    def fail_second(self, artifact):
        if artifact.content_hash == second.content_hash:
            raise RuntimeError("synthetic second-file failure")
        return original(self, artifact)

    monkeypatch.setattr(FileSystemArtifactStore, "put", fail_second)

    class Captured(_Captured):
        def fetch(self, request):
            return batch

    with pytest.raises(RuntimeError, match="second-file failure"):
        ProviderNeutralIngestionService(store, artifact_store=artifacts, clock=lambda: NOW).ingest(
            Captured(first), ProviderDatasetRequest("rollback_test", Market.US, "TEST", NOW)
        )
    assert artifacts.read_content(DIGEST, "text/plain", max_bytes=1024) == CONTENT
    assert store.table_count("provider_artifacts") == store.table_count("ingestion_batches") == 0


def test_abandon_existing_file_is_idempotent_and_does_not_change_original_permissions(tmp_path):
    artifacts = FileSystemArtifactStore(tmp_path / "originals")
    first = artifacts.put(_artifact())
    existing = artifacts.put(_artifact())
    path = artifacts.root / first.storage_key
    before = path.read_bytes(), path.stat().st_mode, path.stat().st_mtime_ns
    for receipt in (first, existing, first):
        artifacts.discard(receipt)
    assert (path.read_bytes(), path.stat().st_mode, path.stat().st_mtime_ns) == before
    assert path.stat().st_mode & 0o777 == 0o600


def test_rollback_never_touches_a_replaced_symlink(tmp_path):
    artifacts = FileSystemArtifactStore(tmp_path / "originals")
    receipt = artifacts.put(_artifact())
    path = artifacts.root / receipt.storage_key
    path.unlink()
    outside = tmp_path / "outside"
    outside.write_bytes(b"do not touch synthetic outside bytes")
    path.symlink_to(outside)
    before = outside.read_bytes(), outside.stat().st_mode
    artifacts.discard(receipt)
    assert path.is_symlink() and (outside.read_bytes(), outside.stat().st_mode) == before
    with pytest.raises(ValueError, match="symbolic"):
        artifacts.read_content(DIGEST, "text/plain", max_bytes=1024)


def test_failure_does_not_introduce_cleanup_logs_or_secret_output(tmp_path, capsys):
    artifacts = FileSystemArtifactStore(tmp_path)
    receipt = artifacts.put(_artifact())
    artifacts.discard(receipt)
    output = capsys.readouterr()
    assert output.out == output.err == ""
    assert not any(path.suffix == ".tmp" for path in tmp_path.rglob("*"))


@pytest.mark.parametrize("same_database", [True, False])
def test_full_ingestion_interleaving_preserves_another_committed_writers_bytes(
    tmp_path,
    monkeypatch,
    same_database,
):
    class FailingStore(SQLiteStore):
        def save_provider_artifacts(self, *args, **kwargs):
            raise RuntimeError("synthetic creator rollback")

    failing = FailingStore(tmp_path / "first.sqlite3")
    failing.initialize()
    committed = SQLiteStore(failing.path if same_database else tmp_path / "second.sqlite3")
    if not same_database:
        committed.initialize()
    originals = FileSystemArtifactStore(tmp_path / "shared")
    original_put = FileSystemArtifactStore.put
    adopted = []

    def interleaved_put(self, artifact):
        receipt = original_put(self, artifact)
        if receipt.created:
            assert not adopted
            adopted.append(_ingest(committed, FileSystemArtifactStore(self.root), artifact))
        return receipt

    monkeypatch.setattr(FileSystemArtifactStore, "put", interleaved_put)
    with pytest.raises(RuntimeError, match="creator rollback"):
        _ingest(failing, originals)
    assert len(adopted) == 1
    assert committed.ingestion_batch(adopted[0].batch_id) is not None
    assert committed.table_count("ingestion_batches") == 1
    assert failing.table_count("ingestion_batches") == (1 if same_database else 0)
    assert audit_provider_artifacts(committed.path, originals.root)["registered_artifacts_verified"]
    assert originals.read_content(DIGEST, "text/plain", max_bytes=1024) == CONTENT
