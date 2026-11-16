"""Pure refresh-attempt transitions, not persistent claims, collection or scheduling."""

import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from tong_quant.domain.models import require_timezone
from tong_quant.version import DATA_REFRESH_ATTEMPT_VERSION


class RefreshAttemptPhase(StrEnum):
    FETCHING = "fetching"
    RETAINING = "retaining"


class RefreshAttemptStatus(StrEnum):
    RUNNING = "running"
    FETCH_FAILED = "fetch_failed"
    RETENTION_FAILED = "retention_failed"
    LEASE_EXPIRED = "lease_expired"
    DATA_RETAINED = "data_retained"
    FAILURE_SNAPSHOT_RETAINED = "failure_snapshot_retained"


class RefreshFailureCode(StrEnum):
    TIMEOUT = "timeout"
    NETWORK_UNAVAILABLE = "network_unavailable"
    RATE_LIMITED = "rate_limited"
    PERMISSION_DENIED = "permission_denied"
    UNSUPPORTED_ENDPOINT = "unsupported_endpoint"
    INVALID_RESPONSE = "invalid_response"
    INSUFFICIENT_DATA = "insufficient_data"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    INTERNAL_ERROR = "internal_error"
    LEASE_EXPIRED = "lease_expired"


_RETRYABLE = {RefreshFailureCode.TIMEOUT, RefreshFailureCode.NETWORK_UNAVAILABLE,
              RefreshFailureCode.RATE_LIMITED}
_RECONCILE = {RefreshAttemptStatus.LEASE_EXPIRED, RefreshAttemptStatus.RETENTION_FAILED,
              RefreshAttemptStatus.DATA_RETAINED, RefreshAttemptStatus.FAILURE_SNAPSHOT_RETAINED}


def _instant(value: datetime) -> datetime:
    if not isinstance(value, datetime):
        raise ValueError("attempt clock requires an aware datetime")
    require_timezone(value, "refresh attempt clock")
    return value.astimezone(UTC)


def _identifier(value: str, pattern: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(pattern, value, flags=re.ASCII):
        raise ValueError("invalid public refresh identifier")


@dataclass(frozen=True, slots=True)
class RefreshAttemptPolicy:
    maximum_attempts: int = 3
    lease_seconds: int = 60
    initial_backoff_seconds: int = 5
    maximum_backoff_seconds: int = 300

    def __post_init__(self) -> None:
        if (any(type(value) is not int for value in (
                self.maximum_attempts, self.lease_seconds,
                self.initial_backoff_seconds, self.maximum_backoff_seconds))
                or not 1 <= self.maximum_attempts <= 10
                or not 1 <= self.lease_seconds <= 3600
                or not 1 <= self.initial_backoff_seconds <= self.maximum_backoff_seconds <= 3600):
            raise ValueError("refresh attempt policy exceeds bounds")


@dataclass(frozen=True, slots=True)
class RefreshLease:
    job_id: str
    generation: int
    worker_id: str
    nonce: str

    def __post_init__(self) -> None:
        _identifier(self.job_id, r"[0-9a-f]{64}")
        _identifier(self.worker_id, r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}")
        _identifier(self.nonce, r"[0-9a-f]{32}")
        if type(self.generation) is not int or not 1 <= self.generation <= 10:
            raise ValueError("invalid refresh attempt generation")


@dataclass(frozen=True, slots=True)
class RefreshAttempt:
    lease: RefreshLease
    policy: RefreshAttemptPolicy
    claimed_at: datetime
    lease_expires_at: datetime
    updated_at: datetime
    phase: RefreshAttemptPhase = RefreshAttemptPhase.FETCHING
    status: RefreshAttemptStatus = RefreshAttemptStatus.RUNNING
    retention_started_at: datetime | None = None
    captured_payload_hash: str | None = None
    ingestion_batch_id: str | None = None
    failure_code: RefreshFailureCode | None = None
    model_version: str = DATA_REFRESH_ATTEMPT_VERSION

    def __post_init__(self) -> None:
        if (not isinstance(self.lease, RefreshLease)
                or not isinstance(self.policy, RefreshAttemptPolicy)
                or not isinstance(self.phase, RefreshAttemptPhase)
                or not isinstance(self.status, RefreshAttemptStatus)
                or (self.failure_code is not None
                    and not isinstance(self.failure_code, RefreshFailureCode))
                or self.model_version != DATA_REFRESH_ATTEMPT_VERSION):
            raise ValueError("invalid refresh attempt contract")
        self.lease.__post_init__()
        self.policy.__post_init__()
        for field in ("claimed_at", "lease_expires_at", "updated_at"):
            object.__setattr__(self, field, _instant(getattr(self, field)))
        if (self.lease.generation > self.policy.maximum_attempts
                or self.lease_expires_at != self.claimed_at + timedelta(
                    seconds=self.policy.lease_seconds)
                or self.updated_at < self.claimed_at):
            raise ValueError("invalid refresh attempt chronology or budget")
        if self.phase is RefreshAttemptPhase.FETCHING:
            if self.retention_started_at is not None or self.captured_payload_hash is not None:
                raise ValueError("fetch phase cannot claim a retained payload")
        else:
            if self.retention_started_at is None or self.captured_payload_hash is None:
                raise ValueError("retention requires a declared payload and start instant")
            _identifier(self.captured_payload_hash, r"[0-9a-f]{64}")
            object.__setattr__(self, "retention_started_at", _instant(self.retention_started_at))
            if (not self.claimed_at <= self.retention_started_at <= self.updated_at
                    or self.retention_started_at >= self.lease_expires_at):
                raise ValueError("invalid retention chronology")
        if self.ingestion_batch_id is not None:
            _identifier(self.ingestion_batch_id, r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}")
        if self.status is RefreshAttemptStatus.LEASE_EXPIRED:
            if (self.updated_at < self.lease_expires_at
                    or self.failure_code is not RefreshFailureCode.LEASE_EXPIRED
                    or self.ingestion_batch_id is not None):
                raise ValueError("invalid expired attempt")
        elif self.updated_at >= self.lease_expires_at:
            raise ValueError("owned attempt update is outside its lease")
        elif self.status is RefreshAttemptStatus.RUNNING:
            if self.failure_code is not None or self.ingestion_batch_id is not None:
                raise ValueError("running attempt cannot claim a final outcome")
        elif self.status in {RefreshAttemptStatus.FETCH_FAILED,
                             RefreshAttemptStatus.RETENTION_FAILED}:
            expected = (RefreshAttemptPhase.FETCHING
                        if self.status is RefreshAttemptStatus.FETCH_FAILED
                        else RefreshAttemptPhase.RETAINING)
            if (self.phase is not expected or self.failure_code is None
                    or self.failure_code is RefreshFailureCode.LEASE_EXPIRED
                    or self.ingestion_batch_id is not None):
                raise ValueError("invalid failed attempt")
        elif (self.phase is not RefreshAttemptPhase.RETAINING or self.ingestion_batch_id is None
              or (self.status is RefreshAttemptStatus.DATA_RETAINED
                  and self.failure_code is not None)
              or (self.status is RefreshAttemptStatus.FAILURE_SNAPSHOT_RETAINED
                  and self.failure_code in (None, RefreshFailureCode.LEASE_EXPIRED))):
            raise ValueError("invalid retained attempt")

    @property
    def reconciliation_required(self) -> bool:
        return self.status in _RECONCILE

    @property
    def retry_at(self) -> datetime | None:
        if (self.status is not RefreshAttemptStatus.FETCH_FAILED
                or self.failure_code not in _RETRYABLE
                or self.lease.generation >= self.policy.maximum_attempts):
            return None
        delay = min(self.policy.maximum_backoff_seconds,
                    self.policy.initial_backoff_seconds * 2 ** (self.lease.generation - 1))
        return self.updated_at + timedelta(seconds=delay)


def new_refresh_attempt(lease: RefreshLease, *, now: datetime,
                        policy: RefreshAttemptPolicy | None = None) -> RefreshAttempt:
    now = _instant(now)
    if policy is None:
        policy = RefreshAttemptPolicy()
    if not isinstance(policy, RefreshAttemptPolicy):
        raise ValueError("invalid refresh attempt policy")
    policy.__post_init__()
    return RefreshAttempt(lease, policy, now, now + timedelta(seconds=policy.lease_seconds), now)


def _owned(attempt: RefreshAttempt, lease: RefreshLease, now: datetime) -> datetime:
    attempt.__post_init__()
    now = _instant(now)
    if (attempt.lease != lease or attempt.status is not RefreshAttemptStatus.RUNNING
            or now < attempt.updated_at or now >= attempt.lease_expires_at):
        raise ValueError("stale, terminal or expired refresh attempt update")
    return now


def start_refresh_retention(attempt: RefreshAttempt, lease: RefreshLease, *, now: datetime,
                            captured_payload_hash: str) -> RefreshAttempt:
    now = _owned(attempt, lease, now)
    if attempt.phase is not RefreshAttemptPhase.FETCHING:
        raise ValueError("retention already started")
    return replace(attempt, phase=RefreshAttemptPhase.RETAINING, updated_at=now,
                   retention_started_at=now, captured_payload_hash=captured_payload_hash)


def finish_refresh_retention(attempt: RefreshAttempt, lease: RefreshLease, *, now: datetime,
                             ingestion_batch_id: str,
                             failure_code: RefreshFailureCode | None = None) -> RefreshAttempt:
    now = _owned(attempt, lease, now)
    if attempt.phase is not RefreshAttemptPhase.RETAINING:
        raise ValueError("retention must be started before declaring a stored batch")
    status = (RefreshAttemptStatus.DATA_RETAINED if failure_code is None
              else RefreshAttemptStatus.FAILURE_SNAPSHOT_RETAINED)
    return replace(attempt, status=status, updated_at=now,
                   ingestion_batch_id=ingestion_batch_id, failure_code=failure_code)


def fail_refresh_attempt(attempt: RefreshAttempt, lease: RefreshLease, *, now: datetime,
                         failure_code: RefreshFailureCode) -> RefreshAttempt:
    now = _owned(attempt, lease, now)
    status = (RefreshAttemptStatus.FETCH_FAILED
              if attempt.phase is RefreshAttemptPhase.FETCHING
              else RefreshAttemptStatus.RETENTION_FAILED)
    return replace(attempt, status=status, updated_at=now, failure_code=failure_code)


def expire_refresh_attempt(attempt: RefreshAttempt, *, now: datetime) -> RefreshAttempt:
    attempt.__post_init__()
    now = _instant(now)
    if (attempt.status is not RefreshAttemptStatus.RUNNING or now < attempt.updated_at
            or now < attempt.lease_expires_at):
        raise ValueError("only a running expired lease can enter recovery")
    return replace(attempt, status=RefreshAttemptStatus.LEASE_EXPIRED,
                   updated_at=now, failure_code=RefreshFailureCode.LEASE_EXPIRED)
