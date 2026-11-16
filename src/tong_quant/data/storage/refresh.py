"""Durable refresh audit and fencing; no network worker, checkpoint or source admission."""

import json
import re
import sqlite3
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any
from uuid import uuid4

from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.providers.contracts import ProviderDatasetRequest, ProviderEvidenceBatch
from tong_quant.data.refresh_attempts import (
    RefreshAttempt,
    RefreshAttemptPhase,
    RefreshAttemptPolicy,
    RefreshAttemptStatus,
    RefreshFailureCode,
    RefreshLease,
    expire_refresh_attempt,
    fail_refresh_attempt,
    finish_refresh_retention,
    new_refresh_attempt,
    start_refresh_retention,
)
from tong_quant.data.refresh_plan import RefreshScope, RefreshWatchlist, build_refresh_plan
from tong_quant.data.storage.migrations import MIGRATION_HEAD
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.domain.models import require_timezone
from tong_quant.version import DATA_REFRESH_LEDGER_VERSION, DATABASE_SCHEMA_VERSION


def _now() -> datetime:
    return datetime.now(UTC)


def _text(value: datetime) -> str:
    require_timezone(value, "refresh ledger clock")
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def _time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if _text(parsed) != value:
        raise ValueError("refresh ledger requires canonical UTC timestamps")
    return parsed


def _validate_metadata(connection: sqlite3.Connection) -> None:
    metadata = dict(connection.execute("SELECT key, value FROM schema_metadata"))
    if (
        metadata.get("migration_head") != MIGRATION_HEAD
        or metadata.get("schema_version") != DATABASE_SCHEMA_VERSION
    ):
        raise ValueError("refresh ledger requires an explicitly migrated database")


def _json(value: object) -> str:
    reject_sensitive_structure(value)
    result = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    if len(result.encode()) > 512 * 1024:
        raise ValueError("refresh ledger payload exceeds bound")
    return result


def _hash(value: object) -> str:
    return sha256(_json(value).encode()).hexdigest()


def _plan(value: dict[str, Any], *, current: bool = False) -> dict[str, Any]:
    _json(value)
    if value.get("plan_hash") != _hash({k: v for k, v in value.items() if k != "plan_hash"}):
        raise ValueError("refresh plan hash mismatch")
    if any(
        value.get(key) is not False
        for key in (
            "collection_authorized",
            "schedule_enabled",
            "research_refresh_authorized",
        )
    ):
        raise ValueError("offline plan cannot carry collection authority")
    if current:
        scopes = tuple(
            RefreshScope(**{**item["scope"], "market": Market(item["scope"]["market"])})
            for item in value["entries"]
        )
        rebuilt = build_refresh_plan(
            RefreshWatchlist(value["watchlist_version"], scopes),
            planned_as_of=datetime.fromisoformat(value["planned_as_of"]),
            git_commit=value["git_commit"],
            git_dirty=value["git_dirty"],
        )
        if _json(rebuilt) != _json(value):
            raise ValueError("refresh plan is not a current validated contract")
    return value


@dataclass(frozen=True, slots=True)
class RefreshJob:
    job_id: str
    plan_hash: str
    scope_hash: str
    trigger_reference: str
    plan_json: str
    policy: RefreshAttemptPolicy
    status: str
    generation: int
    row_version: int
    created_at: datetime
    updated_at: datetime
    next_eligible_at: datetime | None

    @property
    def entry(self) -> dict[str, Any]:
        plan = _plan(json.loads(self.plan_json))
        matches = [entry for entry in plan["entries"] if entry["scope_hash"] == self.scope_hash]
        if len(matches) != 1 or _hash(matches[0]["scope"]) != self.scope_hash:
            raise ValueError("refresh scope does not match its immutable plan")
        return dict(matches[0])


def _job(row: sqlite3.Row) -> RefreshJob:
    if row["model_version"] != DATA_REFRESH_LEDGER_VERSION:
        raise ValueError("unsupported refresh ledger version")
    plan = _plan(json.loads(row["plan_json"]))
    identity = {key: row[key] for key in ("plan_hash", "scope_hash", "trigger_reference")}
    if _hash(identity) != row["job_id"] or plan["plan_hash"] != row["plan_hash"]:
        raise ValueError("refresh job identity mismatch")
    policy = json.loads(row["policy_json"])
    if set(policy) != set(asdict(RefreshAttemptPolicy())):
        raise ValueError("incomplete refresh policy")
    result = RefreshJob(
        row["job_id"],
        row["plan_hash"],
        row["scope_hash"],
        row["trigger_reference"],
        row["plan_json"],
        RefreshAttemptPolicy(**policy),
        row["status"],
        row["generation"],
        row["row_version"],
        _time(row["created_at"]),
        _time(row["updated_at"]),
        None if row["next_eligible_at"] is None else _time(row["next_eligible_at"]),
    )
    if (
        result.updated_at < result.created_at
        or not 0 <= result.generation <= result.policy.maximum_attempts
    ):
        raise ValueError("invalid refresh job chronology or budget")
    _ = result.entry
    return result


def _attempt(row: sqlite3.Row, job: RefreshJob) -> RefreshAttempt:
    return RefreshAttempt(
        RefreshLease(job.job_id, row["generation"], row["worker_id"], row["lease_nonce"]),
        job.policy,
        _time(row["claimed_at"]),
        _time(row["lease_expires_at"]),
        _time(row["updated_at"]),
        RefreshAttemptPhase(row["phase"]),
        RefreshAttemptStatus(row["status"]),
        None if row["retention_started_at"] is None else _time(row["retention_started_at"]),
        row["captured_payload_hash"],
        row["ingestion_batch_id"],
        None if row["failure_code"] is None else RefreshFailureCode(row["failure_code"]),
        row["model_version"],
    )


@dataclass(slots=True)
class SQLiteRefreshRepository:
    store: SQLiteStore
    clock: Callable[[], datetime] = _now

    def __post_init__(self) -> None:
        if not self.store.path.is_file():
            raise ValueError("refresh ledger requires an explicitly initialized database")
        with self.store.read_snapshot(), self.store.repository_connection() as connection:
            _validate_metadata(connection)

    def get(self, job_id: str) -> RefreshJob | None:
        with self.store.repository_connection() as connection:
            row = connection.execute(
                "SELECT * FROM refresh_jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
        return None if row is None else _job(row)

    def attempts(self, job_id: str) -> tuple[RefreshAttempt, ...]:
        with self.store.read_snapshot(), self.store.repository_connection() as connection:
            job = self._require_job(connection, job_id)
            rows = connection.execute(
                "SELECT * FROM refresh_attempts WHERE job_id = ? ORDER BY generation", (job_id,)
            ).fetchall()
            return tuple(_attempt(row, job) for row in rows)

    @staticmethod
    def _require_job(connection: sqlite3.Connection, job_id: str) -> RefreshJob:
        row = connection.execute(
            "SELECT * FROM refresh_jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
        if row is None:
            raise ValueError("refresh job not found")
        return _job(row)

    def register(
        self,
        plan: dict[str, Any],
        *,
        scope_hash: str,
        trigger_reference: str,
        policy: RefreshAttemptPolicy | None = None,
    ) -> RefreshJob:
        _plan(plan, current=True)
        if not isinstance(trigger_reference, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", trigger_reference, flags=re.ASCII
        ):
            raise ValueError("invalid public refresh trigger identity")
        matches = [entry for entry in plan["entries"] if entry["scope_hash"] == scope_hash]
        if len(matches) != 1 or matches[0]["request_contract_status"] != "REQUEST_SCOPE_VALIDATED":
            raise ValueError("unsupported refresh scope must remain in the plan, not be claimed")
        policy = RefreshAttemptPolicy() if policy is None else policy
        if not isinstance(policy, RefreshAttemptPolicy):
            raise ValueError("invalid refresh policy")
        policy.__post_init__()
        policy_json, plan_json = _json(asdict(policy)), _json(plan)
        job_id = _hash(
            {
                "plan_hash": plan["plan_hash"],
                "scope_hash": scope_hash,
                "trigger_reference": trigger_reference,
            }
        )
        with (
            self.store.transaction(),
            self.store.repository_connection(require_transaction=True) as conn,
        ):
            now = _text(self.clock())
            if datetime.fromisoformat(plan["planned_as_of"]).astimezone(UTC) > _time(now):
                raise ValueError("cannot register a future refresh plan")
            conn.execute(
                """INSERT INTO refresh_jobs VALUES
                (?, ?, ?, ?, ?, ?, ?, 'queued', 0, 0, ?, ?, NULL)
                ON CONFLICT(job_id) DO NOTHING""",
                (
                    job_id,
                    plan["plan_hash"],
                    scope_hash,
                    trigger_reference,
                    plan_json,
                    policy_json,
                    DATA_REFRESH_LEDGER_VERSION,
                    now,
                    now,
                ),
            )
            job = self._require_job(conn, job_id)
            if job.plan_json != plan_json or job.policy != policy:
                raise ValueError("refresh job cannot change its immutable request or budget")
            return job

    def claim(self, job_id: str, *, worker_id: str, expected_version: int) -> RefreshAttempt | None:
        if type(expected_version) is not int or expected_version < 0:
            raise ValueError("invalid refresh row version")
        with (
            self.store.transaction(),
            self.store.repository_connection(require_transaction=True) as conn,
        ):
            job = self._require_job(conn, job_id)
            now = _time(_text(self.clock()))
            if now < job.updated_at:
                raise ValueError("refresh ledger clock moved backwards")
            if (
                job.row_version != expected_version
                or job.status not in {"queued", "retry_wait"}
                or (job.next_eligible_at is not None and now < job.next_eligible_at)
            ):
                return None
            _plan(json.loads(job.plan_json), current=True)
            history = conn.execute(
                "SELECT * FROM refresh_attempts WHERE job_id = ? ORDER BY generation", (job_id,)
            ).fetchall()
            if (
                len(history) != job.generation
                or [row["generation"] for row in history] != list(range(1, job.generation + 1))
                or (job.status == "queued" and job.generation != 0)
                or (
                    job.status == "retry_wait"
                    and (
                        not history
                        or _attempt(history[-1], job).retry_at is None
                        or _attempt(history[-1], job).retry_at != job.next_eligible_at
                    )
                )
            ):
                raise ValueError("refresh retry history does not match its job")
            attempt = new_refresh_attempt(
                RefreshLease(job_id, job.generation + 1, worker_id, uuid4().hex),
                now=now,
                policy=job.policy,
            )
            conn.execute(
                """INSERT INTO refresh_attempts VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, NULL, ?)""",
                (
                    job_id,
                    attempt.lease.generation,
                    worker_id,
                    attempt.lease.nonce,
                    attempt.phase.value,
                    attempt.status.value,
                    _text(now),
                    _text(attempt.lease_expires_at),
                    _text(now),
                    attempt.model_version,
                ),
            )
            self._update_job(conn, job, "running", now, attempt.lease.generation, None)
            return attempt

    def _current(
        self, conn: sqlite3.Connection, lease: RefreshLease
    ) -> tuple[RefreshJob, RefreshAttempt]:
        lease.__post_init__()
        job = self._require_job(conn, lease.job_id)
        row = conn.execute(
            "SELECT * FROM refresh_attempts WHERE job_id = ? AND generation = ?",
            (job.job_id, job.generation),
        ).fetchone()
        if row is None or job.status != "running":
            raise ValueError("refresh job is not currently owned")
        attempt = _attempt(row, job)
        if (
            attempt.lease != lease
            or attempt.status is not RefreshAttemptStatus.RUNNING
            or attempt.updated_at != job.updated_at
        ):
            raise ValueError("stale refresh lease")
        return job, attempt

    @staticmethod
    def _update_job(
        conn: sqlite3.Connection,
        job: RefreshJob,
        status: str,
        now: datetime,
        generation: int,
        retry_at: datetime | None,
    ) -> None:
        changed = conn.execute(
            """UPDATE refresh_jobs SET status = ?, generation = ?,
            row_version = row_version + 1, updated_at = ?, next_eligible_at = ?
            WHERE job_id = ? AND row_version = ? AND generation = ?""",
            (
                status,
                generation,
                _text(now),
                None if retry_at is None else _text(retry_at),
                job.job_id,
                job.row_version,
                job.generation,
            ),
        ).rowcount
        if changed != 1:
            raise ValueError("refresh job compare-and-set failed")

    def _save(self, conn: sqlite3.Connection, job: RefreshJob, attempt: RefreshAttempt) -> None:
        changed = conn.execute(
            """UPDATE refresh_attempts SET phase = ?, status = ?, updated_at = ?,
            retention_started_at = ?, captured_payload_hash = ?,
            ingestion_batch_id = ?, failure_code = ?
            WHERE job_id = ? AND generation = ? AND lease_nonce = ? AND status = 'running'""",
            (
                attempt.phase.value,
                attempt.status.value,
                _text(attempt.updated_at),
                None
                if attempt.retention_started_at is None
                else _text(attempt.retention_started_at),
                attempt.captured_payload_hash,
                attempt.ingestion_batch_id,
                attempt.failure_code,
                job.job_id,
                attempt.lease.generation,
                attempt.lease.nonce,
            ),
        ).rowcount
        if changed != 1:
            raise ValueError("refresh attempt compare-and-set failed")
        status = (
            "running"
            if attempt.status is RefreshAttemptStatus.RUNNING
            else (
                "reconciliation_required"
                if attempt.reconciliation_required
                else (
                    "retry_wait"
                    if attempt.retry_at is not None
                    else (
                        "exhausted"
                        if attempt.failure_code
                        in {
                            RefreshFailureCode.TIMEOUT,
                            RefreshFailureCode.NETWORK_UNAVAILABLE,
                            RefreshFailureCode.RATE_LIMITED,
                        }
                        else "failed"
                    )
                )
            )
        )
        self._update_job(
            conn, job, status, attempt.updated_at, attempt.lease.generation, attempt.retry_at
        )

    def start_retention(self, lease: RefreshLease, *, captured_payload_hash: str) -> RefreshAttempt:
        with (
            self.store.transaction(),
            self.store.repository_connection(require_transaction=True) as conn,
        ):
            job, current = self._current(conn, lease)
            updated = start_refresh_retention(
                current, lease, now=self.clock(), captured_payload_hash=captured_payload_hash
            )
            self._save(conn, job, updated)
            return updated

    def fail(self, lease: RefreshLease, *, failure_code: RefreshFailureCode) -> RefreshAttempt:
        with (
            self.store.transaction(),
            self.store.repository_connection(require_transaction=True) as conn,
        ):
            job, current = self._current(conn, lease)
            updated = fail_refresh_attempt(
                current, lease, now=self.clock(), failure_code=failure_code
            )
            self._save(conn, job, updated)
            return updated

    def recover_expired(self, job_id: str) -> RefreshAttempt | None:
        with (
            self.store.transaction(),
            self.store.repository_connection(require_transaction=True) as conn,
        ):
            job = self._require_job(conn, job_id)
            if job.status != "running":
                return None
            row = conn.execute(
                "SELECT * FROM refresh_attempts WHERE job_id = ? AND generation = ?",
                (job_id, job.generation),
            ).fetchone()
            if row is None:
                raise ValueError("running refresh job has no attempt")
            current = _attempt(row, job)
            now = _time(_text(self.clock()))
            if now < current.updated_at:
                raise ValueError("refresh ledger clock moved backwards")
            if now < current.lease_expires_at:
                return None
            updated = expire_refresh_attempt(current, now=now)
            self._save(conn, job, updated)
            return updated

    def validate_retention(
        self, lease: RefreshLease, request: ProviderDatasetRequest, batch: ProviderEvidenceBatch
    ) -> None:
        with self.store.read_snapshot(), self.store.repository_connection() as conn:
            self._validated_retention(conn, lease, request, batch)

    def validate_live_lease(self, lease: RefreshLease) -> None:
        with self.store.read_snapshot(), self.store.repository_connection() as conn:
            _, attempt = self._current(conn, lease)
            now = _time(_text(self.clock()))
            if (
                attempt.phase is not RefreshAttemptPhase.RETAINING
                or now < attempt.updated_at
                or now >= attempt.lease_expires_at
            ):
                raise ValueError("refresh retention lease is not live")

    def validate_fetch_lease(self, lease: RefreshLease) -> None:
        """Check committed FETCHING ownership now, not capacity or future authority.

        Never inherit a managed snapshot or check from this store's managed
        context. Later capture/retention handoffs still need fencing.
        """
        if not isinstance(lease, RefreshLease):
            raise ValueError("refresh fetch requires a typed lease")
        if self.store.has_active_connection:
            raise ValueError("refresh fetch guard requires no active store context")
        reader = SQLiteStore(self.store.path, read_only=True)
        with reader.read_snapshot(), reader.repository_connection() as connection:
            _validate_metadata(connection)
            job, attempt = self._current(connection, lease)
            _plan(json.loads(job.plan_json), current=True)
            now = _time(_text(self.clock()))
            if (
                attempt.phase is not RefreshAttemptPhase.FETCHING
                or now < attempt.updated_at
                or now >= attempt.lease_expires_at
            ):
                raise ValueError("refresh fetch lease is not live")

    def _validated_retention(
        self,
        conn: sqlite3.Connection,
        lease: RefreshLease,
        request: ProviderDatasetRequest,
        batch: ProviderEvidenceBatch,
    ) -> tuple[RefreshJob, RefreshAttempt, datetime]:
        job, attempt = self._current(conn, lease)
        now = _time(_text(self.clock()))
        # Reuse the live-owner guard without changing the stored value.
        if (
            attempt.phase is not RefreshAttemptPhase.RETAINING
            or attempt.retention_started_at is None
            or now < attempt.updated_at
            or now >= attempt.lease_expires_at
            or batch.raw_data_hash != attempt.captured_payload_hash
            or not attempt.claimed_at
            <= batch.retrieved_at.astimezone(UTC)
            <= attempt.retention_started_at
            <= now
            or request.as_of.astimezone(UTC) > now
        ):
            raise ValueError("refresh retention clock, payload or lease mismatch")
        entry, scope = job.entry, job.entry["scope"]
        if (
            (batch.provider, batch.dataset, batch.market.value, request.subject)
            != (scope["provider"], scope["dataset"], scope["market"], scope["subject"])
            or (request.dataset, request.market.value) != (scope["dataset"], scope["market"])
            or any(item.subject != scope["subject"] for item in batch.records)
            or any(item.subject != scope["subject"] for item in batch.artifacts)
            or any(item.subject != scope["subject"] for item in batch.artifact_observations)
        ):
            raise ValueError("refresh capture does not belong to its job scope")
        expected_request = (
            entry["request_parameters"]
            if entry["request_contract"] == "ProviderDatasetRequest" else {}
        )
        if (
            request.parameters != expected_request
            or batch.parameters != refresh_batch_parameters(entry)
        ):
            raise ValueError("refresh provider parameters changed after planning")
        return job, attempt, now

    def attach_ingestion(
        self,
        lease: RefreshLease,
        request: ProviderDatasetRequest,
        batch: ProviderEvidenceBatch,
        batch_id: str,
    ) -> RefreshAttempt:
        """Only the ingestion owner's existing transaction may attach its exact new batch."""
        with self.store.repository_connection(require_transaction=True) as conn:
            job, current, now = self._validated_retention(conn, lease, request, batch)
            stored = conn.execute(
                "SELECT * FROM ingestion_batches WHERE batch_id = ?", (batch_id,)
            ).fetchone()
            if (
                stored is None
                or stored["raw_response_hash"] != batch.raw_data_hash
                or stored["provider"] != batch.provider
                or stored["dataset"] != batch.dataset
                or stored["status"] != "completed"
            ):
                raise ValueError("refresh ingestion receipt mismatch")
            code = _retention_failure(batch)
            updated = finish_refresh_retention(
                current, lease, now=now, ingestion_batch_id=batch_id, failure_code=code
            )
            self._save(conn, job, updated)
            return updated


def _retention_failure(batch: ProviderEvidenceBatch) -> RefreshFailureCode | None:
    return refresh_retention_failure(
        batch.provider, tuple(record.payload.get("status") for record in batch.records)
    )


def refresh_batch_parameters(entry: dict[str, Any]) -> dict[str, str]:
    """Shared immutable capture contract for retention and read-side reconciliation."""
    if entry["request_contract"] == "ProviderDatasetRequest":
        return {
            "subject": entry["scope"]["subject"],
            **entry["request_parameters"],
            "normalization_version": entry["provider_model_version"],
        }
    return {
        **{k: v for k, v in entry["request_parameters"].items() if k != "market"},
        "fetch_version": entry["provider_contract_versions"]["fetch"],
        "symbol_routing_version": entry["provider_contract_versions"]["routing"],
        "normalization_version": entry["provider_contract_versions"]["normalization"],
    }


def refresh_retention_failure(
    provider: str, record_statuses: tuple[object, ...]
) -> RefreshFailureCode | None:
    """Classify capture receipts without granting source quality or research admission."""
    if not record_statuses:
        return RefreshFailureCode.INSUFFICIENT_DATA
    if provider == "akshare":
        return None
    if any(not isinstance(status, str) for status in record_statuses):
        return RefreshFailureCode.INVALID_RESPONSE
    statuses = set(record_statuses)
    if statuses <= {"observed_unqualified", "partial_unqualified"}:
        return None
    if statuses & {
        "no_observations",
        "insufficient_native_data",
        "current_session_completion_unverified",
    }:
        return RefreshFailureCode.INSUFFICIENT_DATA
    if statuses & {"http_401", "http_403"}:
        return RefreshFailureCode.PERMISSION_DENIED
    if statuses & {"http_429"}:
        return RefreshFailureCode.RATE_LIMITED
    if statuses & {"provider_unavailable", "network_unavailable", "http_error", "http_404"}:
        return RefreshFailureCode.PROVIDER_UNAVAILABLE
    return RefreshFailureCode.INVALID_RESPONSE
