"""Exact read-only receipt inspection; never repair a job or admit research data."""

import json
import os
import re
import sqlite3
import stat
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from tong_quant.data.providers.contracts import (
    ProviderArtifactStatus,
    provider_artifact_id,
    provider_artifact_observation_id,
    provider_evidence_id,
)
from tong_quant.data.refresh_attempts import RefreshAttemptStatus
from tong_quant.data.storage.artifact_audit import (
    _open_without_links,
    audit_provider_artifact_selection,
)
from tong_quant.data.storage.migrations import (
    MIGRATION_HEAD,
    MIGRATIONS,
    validate_latest_schema_fingerprint,
)
from tong_quant.data.storage.refresh import (
    SQLiteRefreshRepository,
    refresh_batch_parameters,
    refresh_retention_failure,
)
from tong_quant.data.storage.sqlite import SCHEMA, SQLiteStore
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market
from tong_quant.domain.models import require_timezone
from tong_quant.version import DATA_REFRESH_RECONCILIATION_VERSION, PROVIDER_EVIDENCE_VERSION

_SUPPORTED = {
    ("akshare", "a_share_daily"),
    ("yahoo_finance", "global_equity_price_snapshot"),
    ("yahoo_finance", "global_native_fundamental_snapshot"),
}
_MAX_METADATA_BYTES = 2 * 1024 * 1024


class _Mismatch(ValueError):
    pass


def _check(condition: bool) -> None:
    if not condition:
        raise _Mismatch("receipt mismatch")


def _digest(value: object) -> str:
    return sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False,
        default=lambda blob: {"blob_sha256": sha256(blob).hexdigest()},
    ).encode()).hexdigest()


def _time(value: str, cutoff: datetime) -> datetime:
    parsed = datetime.fromisoformat(value)
    require_timezone(parsed, "receipt timestamp")
    _check(parsed <= cutoff)
    return parsed


def _rows(
    conn: sqlite3.Connection, table: str, column: str, value: str, limit: int
) -> list[sqlite3.Row]:
    # Names come only from fixed calls below, never CLI/provider values.
    columns = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
    lengths = " + ".join(f'COALESCE(length(CAST("{name}" AS BLOB)), 0)' for name in columns)
    size = conn.execute(
        f"SELECT COALESCE(sum({lengths}), 0) FROM "
        f"(SELECT * FROM {table} WHERE {column} = ? ORDER BY rowid LIMIT ?)",
        (value, limit + 1),
    ).fetchone()[0]
    if size > _MAX_METADATA_BYTES:
        raise OverflowError("receipt metadata bound exceeded")
    rows = conn.execute(
        f"SELECT * FROM {table} WHERE {column} = ? ORDER BY rowid LIMIT ?",
        (value, limit + 1),
    ).fetchall()
    if len(rows) > limit:
        raise OverflowError("receipt row bound exceeded")
    if sum(len(json.dumps(tuple(row), default=str).encode()) for row in rows) > (
        _MAX_METADATA_BYTES
    ):
        raise OverflowError("receipt metadata bound exceeded")
    return rows


def inspect_refresh_reconciliation(
    database_path: Path,
    artifact_root: Path,
    *,
    job_id: str,
    inspected_as_of: datetime,
    max_records: int = 10_000,
    max_file_bytes: int = 64 * 1024 * 1024,
    max_total_bytes: int = 512 * 1024 * 1024,
) -> dict[str, Any]:
    """Inspect the exact linked batch in one SQL snapshot and bounded file reads.

    This is a current-snapshot diagnostic with an upper timestamp bound, not a
    reconstruction of the database as it existed at a past cutoff.
    """
    require_timezone(inspected_as_of, "reconciliation cutoff")
    if not re.fullmatch(r"[0-9a-f]{64}", job_id):
        raise ValueError("job ID must be a SHA-256 digest")
    for limit in (max_records, max_file_bytes, max_total_bytes):
        if type(limit) is not int or limit < 1:
            raise ValueError("reconciliation limits must be positive integers")
    cutoff = inspected_as_of.astimezone(UTC)
    report: dict[str, Any] = {
        "model_version": DATA_REFRESH_RECONCILIATION_VERSION,
        "job_id": job_id,
        "inspected_as_of": cutoff.isoformat(timespec="microseconds"),
        "status": "UNREADABLE_OR_INCONSISTENT",
        "checkpoint_advanced": False,
        "collection_complete": False,
        "data_qualified": False,
        "research_refresh_authorized": False,
        "validation_authorized": False,
        "execution_authorized": False,
        "limits": {"records": max_records, "file_bytes": max_file_bytes,
                   "total_file_bytes": max_total_bytes},
        "limitations": [
            "Current database snapshot only, not historical database reconstruction.",
            "File reads are not atomic with the database; quiesce writers and repeat.",
            "Exact references and byte identity do not authenticate source truth or PIT quality.",
            "No payload re-normalization, numeric validation, checkpoint or retry reset.",
            "Unreferenced files and unrelated batches are not searched or deleted.",
            "No data, research, trading or execution readiness is granted.",
        ],
    }
    try:
        # Reuse the existing no-symlink path check; SQL is opened read-only too.
        descriptor = _open_without_links(database_path.expanduser().absolute())
        try:
            _check(stat.S_ISREG(os.fstat(descriptor).st_mode))
        finally:
            os.close(descriptor)
        store = SQLiteStore(database_path, read_only=True)
        with store.read_snapshot(), store.repository_connection() as conn:
            repo = SQLiteRefreshRepository(store)
            fingerprint = conn.execute(
                "SELECT migration_head FROM schema_fingerprints ORDER BY rowid DESC LIMIT 1"
            ).fetchone()
            _check(fingerprint is not None and fingerprint[0] == MIGRATION_HEAD)
            ledger = conn.execute(
                "SELECT migration_id, checksum FROM schema_migrations ORDER BY migration_id"
            ).fetchall()
            _check([tuple(row) for row in ledger] == [
                (item.migration_id, item.checksum) for item in MIGRATIONS
            ])
            validate_latest_schema_fingerprint(conn, schema_definition=SCHEMA)
            _inspect(conn, repo, job_id, cutoff, report, artifact_root,
                     max_records, max_file_bytes, max_total_bytes)
    except OverflowError:
        report["status"] = "LIMIT_EXCEEDED"
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, sqlite3.Error):
        # Deliberately omit exception text and arbitrary stored values, paths or URLs.
        report["status"] = "UNREADABLE_OR_INCONSISTENT"
    report["report_hash"] = _digest(report)
    return report


def _inspect(
    conn: sqlite3.Connection,
    repo: SQLiteRefreshRepository,
    job_id: str,
    cutoff: datetime,
    report: dict[str, Any],
    artifact_root: Path,
    limit: int,
    max_file_bytes: int,
    max_total_bytes: int,
) -> None:
    _rows(conn, "refresh_jobs", "job_id", job_id, 1)
    _rows(conn, "refresh_attempts", "job_id", job_id, 10)
    job = repo.get(job_id)
    if job is None:
        report["status"] = "JOB_MISSING"
        return
    entry = job.entry
    scope = entry["scope"]
    _check((scope["provider"], scope["dataset"]) in _SUPPORTED)
    _check(job.created_at <= job.updated_at <= cutoff)
    _check(_time(json.loads(job.plan_json)["planned_as_of"], cutoff) <= job.created_at)
    attempts = repo.attempts(job_id)
    _check([item.lease.generation for item in attempts] == list(range(1, job.generation + 1)))
    _check(all(item.updated_at <= cutoff for item in attempts))
    _check(all(item.status is not RefreshAttemptStatus.RUNNING for item in attempts[:-1]))
    for previous, current in zip(attempts, attempts[1:], strict=False):
        _check(previous.retry_at is not None and previous.retry_at <= current.claimed_at)
    report["ledger_hash"] = _digest([
        tuple(row) for table in ("refresh_jobs", "refresh_attempts")
        for row in _rows(conn, table, "job_id", job_id, 10)
    ])
    report["generation"] = job.generation
    if not attempts:
        _check(job.status == "queued")
        report["status"] = "NO_ATTEMPT"
        return
    attempt = attempts[-1]
    report["attempt_status"] = attempt.status.value
    report["failure_code"] = None if attempt.failure_code is None else attempt.failure_code.value
    _check(job.updated_at == attempt.updated_at)
    if attempt.ingestion_batch_id is None:
        if attempt.status is RefreshAttemptStatus.RUNNING:
            _check(job.status == "running")
            report["status"] = (
                "IN_PROGRESS" if cutoff < attempt.lease_expires_at else "RECOVERY_REQUIRED"
            )
        else:
            report["status"] = "NO_LINKED_BATCH"
        return
    _check(job.status == "reconciliation_required")
    _check(attempt.status in {
        RefreshAttemptStatus.DATA_RETAINED, RefreshAttemptStatus.FAILURE_SNAPSHOT_RETAINED,
    })
    if attempt.retention_started_at is None:
        raise _Mismatch("missing retention phase")
    batches = _rows(conn, "ingestion_batches", "batch_id", attempt.ingestion_batch_id, 1)
    _check(len(batches) == 1)
    batch = batches[0]
    _check((batch["provider"], batch["dataset"]) == (scope["provider"], scope["dataset"]))
    _check(batch["status"] == "completed" and not batch["failure_reason"])
    _check(batch["raw_response_hash"] == attempt.captured_payload_hash)
    expected = refresh_batch_parameters(entry)
    _check(json.loads(batch["parameters_json"]) == expected)
    retrieved = _time(batch["started_at"], cutoff)
    completed = _time(batch["completed_at"], cutoff)
    _check(attempt.claimed_at <= retrieved <= attempt.retention_started_at)
    _check(attempt.retention_started_at <= completed <= attempt.updated_at)
    _time(batch["ingested_at"], cutoff)
    fingerprints = _rows(
        conn, "raw_dataset_fingerprints", "raw_data_hash", batch["raw_response_hash"], 1
    )
    _check(len(fingerprints) == 1)
    raw = fingerprints[0]
    _check((raw["provider"], raw["dataset"]) == (scope["provider"], scope["dataset"]))
    _check(json.loads(raw["parameters_json"]) == expected)
    _check(_time(raw["retrieved_at"], cutoff) <= retrieved)
    _check(type(raw["row_count"]) is int and raw["row_count"] >= 0)
    _time(raw["ingested_at"], cutoff)
    evidence = _rows(conn, "provider_evidence_records", "batch_id", batch["batch_id"], limit)
    observations = _rows(
        conn, "provider_artifact_observations", "batch_id", batch["batch_id"], limit
    )
    first_registered = _rows(
        conn, "provider_artifacts", "first_batch_id", batch["batch_id"], limit
    )
    _check(len(observations) == (1 if scope["provider"] == "akshare" else 0))
    _check(raw["row_count"] >= len(evidence))
    ids: set[str] = set()
    sources: set[str] = set()
    statuses: list[object] = []
    for row in evidence:
        _scope(row, scope)
        _check(row["raw_data_hash"] == batch["raw_response_hash"])
        _check(_time(row["retrieved_at"], cutoff) == retrieved)
        available = _time(row["available_at"], cutoff)
        _check(available == retrieved)
        for field in ("published_at", "observed_at"):
            if row[field] is not None:
                _check(_time(row[field], cutoff) <= retrieved)
        _time(row["ingested_at"], cutoff)
        _unqualified(row)
        payload = json.loads(row["payload_json"])
        _check(isinstance(payload, dict))
        _check(row["evidence_id"] == provider_evidence_id(
            provider=row["provider"], dataset=row["dataset"], market=Market(row["market"]),
            subject=row["subject"], available_at=datetime.fromisoformat(row["available_at"]),
            source_reference=row["source_reference"], payload=payload,
        ))
        artifact_id = payload.get("artifact_id")
        _check(isinstance(artifact_id, str) and bool(re.fullmatch(r"[0-9a-f]{64}", artifact_id)))
        ids.add(artifact_id)
        sources.add(row["source_reference"])
        statuses.append(payload.get("status"))
        if scope["dataset"] == "global_equity_price_snapshot":
            _check(payload.get("model_version") == entry["provider_model_version"])
    for row in observations:
        _scope(row, scope)
        _check(_time(row["retrieved_at"], cutoff) == retrieved)
        _check(_time(row["published_at"], cutoff) <= retrieved)
        _time(row["ingested_at"], cutoff)
        status = ProviderArtifactStatus(row["status"])
        _check(status is ProviderArtifactStatus.CAPTURED and not row["error_code"])
        _check(_time(row["published_at"], cutoff) == retrieved)
        _check(row["observation_id"] == provider_artifact_observation_id(
            provider=row["provider"], dataset=row["dataset"], market=Market(row["market"]),
            subject=row["subject"], source_identity=row["source_identity"],
            source_reference=row["source_reference"],
            published_at=datetime.fromisoformat(row["published_at"]),
            retrieved_at=datetime.fromisoformat(row["retrieved_at"]), status=status,
            artifact_id=row["artifact_id"], error_code=row["error_code"],
            related_source_identities=tuple(json.loads(row["related_source_identities_json"])),
        ))
        ids.add(row["artifact_id"])
        sources.add(row["source_reference"])
    failure = refresh_retention_failure(scope["provider"], tuple(statuses))
    _check(failure == attempt.failure_code)
    _check((failure is None) == (attempt.status is RefreshAttemptStatus.DATA_RETAINED))
    _check(all(row["artifact_id"] in ids for row in first_registered))
    report["evidence_count"] = len(evidence)
    report["observation_count"] = len(observations)
    if not ids:
        report["status"] = "NO_REFERENCED_ORIGINAL"
        return
    if len(ids) > limit:
        raise OverflowError("artifact reference bound exceeded")
    artifacts: list[sqlite3.Row] = []
    owners_seen: list[sqlite3.Row] = []
    for identity in sorted(ids):
        selected = _rows(conn, "provider_artifacts", "artifact_id", identity, 1)
        _check(len(selected) == 1)
        row = selected[0]
        _scope(row, scope)
        _unqualified(row)
        _check(row["source_reference"] in sources and row["source_reference"] == raw["source"])
        _check(row["content_hash"] == attempt.captured_payload_hash)
        _check(_time(row["published_at"], cutoff) <= _time(row["first_retrieved_at"], cutoff))
        _check(_time(row["first_retrieved_at"], cutoff) <= retrieved)
        _time(row["ingested_at"], cutoff)
        owners = _rows(conn, "ingestion_batches", "batch_id", row["first_batch_id"], 1)
        _check(len(owners) == 1)
        owner = owners[0]
        _check(owner["status"] == "completed" and owner["raw_response_hash"] == row["content_hash"])
        _check((owner["provider"], owner["dataset"]) == (scope["provider"], scope["dataset"]))
        _check(json.loads(owner["parameters_json"]) == expected)
        _check(_time(owner["started_at"], cutoff) == _time(row["first_retrieved_at"], cutoff))
        _time(owner["completed_at"], cutoff)
        _time(owner["ingested_at"], cutoff)
        owners_seen.append(owner)
        _check(row["model_version"] == (
            PROVIDER_EVIDENCE_VERSION if scope["provider"] == "akshare"
            else entry["provider_model_version"]
        ))
        _check(identity == provider_artifact_id(
            provider=row["provider"], dataset=row["dataset"], market=Market(row["market"]),
            subject=row["subject"], source_identity=row["source_identity"],
            source_reference=row["source_reference"], content_hash=row["content_hash"],
        ))
        artifacts.append(row)
    _check(sources == {row["source_reference"] for row in artifacts})
    for observation in observations:
        referenced = next(
            row for row in artifacts if row["artifact_id"] == observation["artifact_id"]
        )
        _check(all(observation[key] == referenced[key]
                   for key in ("source_identity", "source_reference")))
    report["receipt_hash"] = _digest([
        dict(row) for row in [batch, raw, *evidence, *observations, *artifacts, *owners_seen]
    ])
    audit = audit_provider_artifact_selection(
        tuple(tuple(row[key] for key in (
            "artifact_id", "content_hash", "media_type", "byte_size", "storage_key"
        )) for row in artifacts), artifact_root,
        max_records=limit, max_file_bytes=max_file_bytes, max_total_bytes=max_total_bytes,
    )
    report["artifact_audit"] = audit
    if not audit["selected_artifacts_verified"]:
        report["status"] = "ORIGINAL_UNVERIFIABLE"
        return
    report["status"] = (
        "LINKED_BYTES_MATCH" if failure is None else "LINKED_FAILURE_BYTES_MATCH"
    )


def _scope(row: sqlite3.Row, scope: dict[str, Any]) -> None:
    _check(all(row[key] == scope[key] for key in ("provider", "dataset", "market", "subject")))


def _unqualified(row: sqlite3.Row) -> None:
    _check(row["trust_level"] in {DataTrustLevel.LOW.value, DataTrustLevel.UNKNOWN.value})
    _check(row["availability_precision"] == AvailabilityPrecision.RETRIEVAL_TIME.value)
