"""Verify a decoded snapshot against immutable evidence and ingestion ownership."""

import json
from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.providers.contracts import ProviderEvidenceBatch, ProviderEvidenceRecord
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.models import require_timezone


def _stored_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    require_timezone(parsed, "retained snapshot stored timestamp")
    return parsed.astimezone(UTC)


def verify_retained_snapshot(
    store: SQLiteStore, artifacts: FileSystemArtifactStore, record: ProviderEvidenceRecord,
    *, as_of: datetime, max_bytes: int,
    rebuild: Callable[[dict[str, Any]], ProviderEvidenceBatch],
) -> dict[str, Any]:
    """Caller supplies normalization; verification grants consistency, not source trust."""
    require_timezone(as_of, "retained snapshot cutoff")
    cutoff = as_of.astimezone(UTC)
    if max(record.available_at.astimezone(UTC), record.retrieved_at.astimezone(UTC)) > cutoff:
        raise ValueError("future retained snapshot")
    content = artifacts.read_content(record.raw_data_hash, "application/json", max_bytes=max_bytes)
    envelope = json.loads(content)
    if not isinstance(envelope, dict):
        raise ValueError("retained snapshot envelope must be an object")
    batch = rebuild(envelope)
    batch.__post_init__()
    if len(batch.artifacts) != 1:
        raise ValueError("retained snapshot requires exactly one artifact")
    artifact = batch.artifacts[0]
    captured = batch.retrieved_at.astimezone(UTC)
    if batch.records != (record,) or artifact.content != content:
        raise ValueError("retained snapshot reconstruction mismatch")
    saved_artifact = store.provider_artifact(artifact.artifact_id)
    if (saved_artifact is None or saved_artifact["storage_key"] != (
        f"sha256/{record.raw_data_hash[:2]}/{record.raw_data_hash}.bin")
            or saved_artifact["byte_size"] != len(content)):
        raise ValueError("retained snapshot artifact registry mismatch")
    for key, value in asdict(artifact).items():
        if key not in {"content", "published_at", "retrieved_at"} and saved_artifact[key] != value:
            raise ValueError("retained snapshot artifact metadata mismatch")
    for key in ("published_at", "first_retrieved_at"):
        if _stored_utc(saved_artifact[key]) != captured:
            raise ValueError("retained snapshot artifact chronology mismatch")
    row = next((row for row in store.provider_evidence_as_of(
        provider=record.provider, dataset=record.dataset, market=record.market,
        subject=record.subject, as_of=as_of) if row["evidence_id"] == record.evidence_id), None)
    if row is None:
        raise ValueError("retained snapshot evidence ownership missing")
    for batch_id in {row["batch_id"], saved_artifact["first_batch_id"]}:
        saved = store.ingestion_batch(batch_id)
        if (saved is None or saved["provider"] != record.provider
                or saved["dataset"] != record.dataset or saved["status"] != "completed"
                or saved["completed_at"] is None
                or saved["raw_response_hash"] != record.raw_data_hash
                or json.loads(saved["parameters_json"]) != batch.parameters
                or _stored_utc(saved["started_at"]) != captured
                or not captured <= _stored_utc(saved["completed_at"]) <= cutoff):
            raise ValueError("retained snapshot ingestion chronology or ownership rejected")
    return envelope
