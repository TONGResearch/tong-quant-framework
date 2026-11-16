import ast
import socket
import sqlite3
import subprocess
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

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

NOW = datetime(2026, 11, 3, 8, tzinfo=UTC)
LEASE = RefreshLease("a" * 64, 1, "worker-a", "1" * 32)
DIGEST = "b" * 64


def test_new_attempt_has_no_response_hash_or_outcome_and_is_immutable() -> None:
    attempt = new_refresh_attempt(LEASE, now=NOW)
    assert attempt.status is RefreshAttemptStatus.RUNNING
    assert attempt.phase is RefreshAttemptPhase.FETCHING
    assert attempt.captured_payload_hash is attempt.ingestion_batch_id is None
    assert attempt.retry_at is None and not attempt.reconciliation_required
    assert attempt.lease_expires_at == NOW + timedelta(seconds=60)
    with pytest.raises(FrozenInstanceError):
        attempt.status = RefreshAttemptStatus.DATA_RETAINED


@pytest.mark.parametrize("code", [RefreshFailureCode.TIMEOUT,
                                 RefreshFailureCode.NETWORK_UNAVAILABLE,
                                 RefreshFailureCode.RATE_LIMITED])
def test_observed_transient_fetch_failure_has_bounded_retry_and_no_fake_payload(
    code: RefreshFailureCode,
) -> None:
    attempt = new_refresh_attempt(LEASE, now=NOW)
    failed = fail_refresh_attempt(attempt, LEASE, now=NOW + timedelta(seconds=2), failure_code=code)
    assert failed.retry_at == NOW + timedelta(seconds=7)
    assert failed.captured_payload_hash is failed.ingestion_batch_id is None
    assert not failed.reconciliation_required
    assert attempt.status is RefreshAttemptStatus.RUNNING


@pytest.mark.parametrize("code", [RefreshFailureCode.PERMISSION_DENIED,
    RefreshFailureCode.UNSUPPORTED_ENDPOINT, RefreshFailureCode.INVALID_RESPONSE,
    RefreshFailureCode.INTERNAL_ERROR])
def test_permanent_or_unknown_failure_does_not_retry(code: RefreshFailureCode) -> None:
    failed = fail_refresh_attempt(new_refresh_attempt(LEASE, now=NOW), LEASE,
        now=NOW + timedelta(seconds=1), failure_code=code)
    assert failed.status is RefreshAttemptStatus.FETCH_FAILED
    assert failed.retry_at is None and not failed.reconciliation_required


def test_retry_budget_exhaustion_and_backoff_cap_are_separate_from_fetch_result() -> None:
    policy = RefreshAttemptPolicy(maximum_attempts=5, initial_backoff_seconds=5,
                                  maximum_backoff_seconds=8)
    for generation, delay in ((1, 5), (2, 8), (4, 8), (5, None)):
        lease = replace(LEASE, generation=generation)
        failed = fail_refresh_attempt(new_refresh_attempt(lease, now=NOW, policy=policy), lease,
                                      now=NOW, failure_code=RefreshFailureCode.TIMEOUT)
        assert failed.retry_at == (None if delay is None else NOW + timedelta(seconds=delay))


@pytest.mark.parametrize("retaining", [False, True])
def test_crash_or_expiry_always_requires_reconciliation_before_retry(retaining: bool) -> None:
    attempt = new_refresh_attempt(LEASE, now=NOW)
    if retaining:
        attempt = start_refresh_retention(attempt, LEASE, now=NOW + timedelta(seconds=1),
                                           captured_payload_hash=DIGEST)
    expired = expire_refresh_attempt(attempt, now=attempt.lease_expires_at)
    assert expired.status is RefreshAttemptStatus.LEASE_EXPIRED
    assert expired.reconciliation_required and expired.retry_at is None
    assert expired.captured_payload_hash == (DIGEST if retaining else None)
    assert expired.ingestion_batch_id is None
    with pytest.raises(ValueError):
        fail_refresh_attempt(expired, LEASE, now=expired.updated_at,
                             failure_code=RefreshFailureCode.TIMEOUT)


@pytest.mark.parametrize("change", [
    {"job_id": "c" * 64}, {"generation": 2}, {"worker_id": "worker-b"}, {"nonce": "2" * 32},
])
def test_wrong_job_generation_worker_or_nonce_cannot_update_current_state(
    change: dict[str, object],
) -> None:
    attempt = new_refresh_attempt(LEASE, now=NOW)
    with pytest.raises(ValueError):
        start_refresh_retention(attempt, replace(LEASE, **change), now=NOW,
                                captured_payload_hash=DIGEST)


@pytest.mark.parametrize("seconds", [-1, 60, 61])
def test_clock_regression_or_exact_lease_boundary_cannot_finish(seconds: int) -> None:
    attempt = start_refresh_retention(new_refresh_attempt(LEASE, now=NOW), LEASE, now=NOW,
                                       captured_payload_hash=DIGEST)
    with pytest.raises(ValueError):
        finish_refresh_retention(attempt, LEASE, now=NOW + timedelta(seconds=seconds),
                                 ingestion_batch_id="batch-1")


@pytest.mark.parametrize("code", [None, RefreshFailureCode.PERMISSION_DENIED])
def test_retained_data_and_failure_snapshot_both_need_actual_repository_verification(
    code: RefreshFailureCode | None,
) -> None:
    attempt = start_refresh_retention(new_refresh_attempt(LEASE, now=NOW), LEASE,
        now=NOW + timedelta(seconds=1), captured_payload_hash=DIGEST)
    retained = finish_refresh_retention(attempt, LEASE, now=NOW + timedelta(seconds=2),
                                       ingestion_batch_id="batch-1", failure_code=code)
    assert retained.status is (RefreshAttemptStatus.DATA_RETAINED if code is None
                              else RefreshAttemptStatus.FAILURE_SNAPSHOT_RETAINED)
    assert retained.reconciliation_required and retained.retry_at is None
    assert retained.ingestion_batch_id == "batch-1"
    assert retained.retention_started_at == NOW + timedelta(seconds=1)
    assert not hasattr(retained, "checkpoint") and not hasattr(retained, "research_authorized")
    with pytest.raises(ValueError):
        finish_refresh_retention(retained, LEASE, now=retained.updated_at,
                                 ingestion_batch_id="batch-2")


def test_retention_timeout_cannot_be_retried_as_an_uncommitted_fetch() -> None:
    attempt = start_refresh_retention(new_refresh_attempt(LEASE, now=NOW), LEASE,
        now=NOW + timedelta(seconds=1), captured_payload_hash=DIGEST)
    failed = fail_refresh_attempt(attempt, LEASE, now=NOW + timedelta(seconds=2),
                                   failure_code=RefreshFailureCode.TIMEOUT)
    assert failed.status is RefreshAttemptStatus.RETENTION_FAILED
    assert failed.reconciliation_required and failed.retry_at is None
    assert failed.captured_payload_hash == DIGEST and failed.ingestion_batch_id is None


def test_cannot_skip_or_restart_retention_or_recover_early() -> None:
    attempt = new_refresh_attempt(LEASE, now=NOW)
    with pytest.raises(ValueError):
        finish_refresh_retention(attempt, LEASE, now=NOW, ingestion_batch_id="batch-1")
    with pytest.raises(ValueError):
        expire_refresh_attempt(attempt, now=NOW + timedelta(seconds=59))
    retaining = start_refresh_retention(attempt, LEASE, now=NOW + timedelta(seconds=1),
                                        captured_payload_hash=DIGEST)
    with pytest.raises(ValueError):
        start_refresh_retention(retaining, LEASE, now=NOW + timedelta(seconds=2),
                                captured_payload_hash=DIGEST)
    with pytest.raises(ValueError):
        fail_refresh_attempt(retaining, LEASE, now=NOW,
                             failure_code=RefreshFailureCode.INTERNAL_ERROR)


@pytest.mark.parametrize("kwargs", [
    {"maximum_attempts": 0}, {"maximum_attempts": 11}, {"maximum_attempts": True},
    {"lease_seconds": 0}, {"lease_seconds": 3601}, {"lease_seconds": 1.5},
    {"initial_backoff_seconds": 0}, {"maximum_backoff_seconds": 4},
    {"maximum_backoff_seconds": 3601},
])
def test_policy_has_strict_resource_bounds(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        RefreshAttemptPolicy(**kwargs)


@pytest.mark.parametrize("change", [
    {"job_id": "unknown"}, {"generation": 0}, {"generation": True},
    {"worker_id": "secret=fixture"}, {"nonce": "token=fixture"}, {"nonce": "0" * 31},
])
def test_lease_accepts_only_bounded_public_identifiers(change: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        replace(LEASE, **change)


@pytest.mark.parametrize("change", [
    {"status": "running"}, {"failure_code": "token=fixture"},
    {"lease_expires_at": NOW + timedelta(seconds=61)},
    {"updated_at": NOW - timedelta(seconds=1)},
    {"phase": RefreshAttemptPhase.RETAINING}, {"captured_payload_hash": DIGEST},
    {"ingestion_batch_id": "batch-1"}, {"failure_code": RefreshFailureCode.INTERNAL_ERROR},
    {"model_version": "unknown"}, {"claimed_at": NOW.replace(tzinfo=None)},
])
def test_reconstruction_rejects_inconsistent_or_unsupported_records(
    change: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        replace(new_refresh_attempt(LEASE, now=NOW), **change)


def test_payload_identity_and_failure_code_are_not_raw_exception_text() -> None:
    attempt = new_refresh_attempt(LEASE, now=NOW)
    with pytest.raises(ValueError):
        start_refresh_retention(attempt, LEASE, now=NOW, captured_payload_hash="secret=fixture")
    with pytest.raises(ValueError):
        fail_refresh_attempt(attempt, LEASE, now=NOW, failure_code="password=fixture")
    with pytest.raises(ValueError):
        fail_refresh_attempt(attempt, LEASE, now=NOW, failure_code=RefreshFailureCode.LEASE_EXPIRED)


def test_utc_equivalence_and_dst_folds_use_actual_instants() -> None:
    assert new_refresh_attempt(LEASE, now=NOW) == new_refresh_attempt(
        LEASE, now=NOW.astimezone(ZoneInfo("Asia/Kuala_Lumpur")))
    first = datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo("America/New_York"))
    attempt = new_refresh_attempt(LEASE, now=first)
    with pytest.raises(ValueError):
        fail_refresh_attempt(attempt, LEASE, now=first.replace(fold=1),
                             failure_code=RefreshFailureCode.TIMEOUT)
    expired = expire_refresh_attempt(attempt, now=first.replace(fold=1))
    assert expired.updated_at - expired.claimed_at == timedelta(hours=1)
    assert expired.reconciliation_required


def test_transition_layer_has_no_io_or_trading_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("attempt value transitions crossed an I/O boundary")
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(sqlite3, "connect", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    attempt = new_refresh_attempt(LEASE, now=NOW)
    assert expire_refresh_attempt(attempt, now=attempt.lease_expires_at).reconciliation_required
    source = Path(__file__).resolve().parents[1] / "src/tong_quant/data/refresh_attempts.py"
    imports = {node.module for node in ast.walk(ast.parse(source.read_text()))
               if isinstance(node, ast.ImportFrom)}
    assert imports == {"dataclasses", "datetime", "enum", "tong_quant.domain.models",
                       "tong_quant.version"}


def test_explicit_budget_cannot_be_bypassed_by_new_attempt_number() -> None:
    with pytest.raises(ValueError):
        new_refresh_attempt(replace(LEASE, generation=4), now=NOW)
    assert isinstance(new_refresh_attempt(LEASE, now=NOW), RefreshAttempt)


def test_expired_reconstruction_cannot_backfill_a_post_lease_retention_start() -> None:
    attempt = new_refresh_attempt(LEASE, now=NOW)
    with pytest.raises(ValueError):
        replace(attempt, phase=RefreshAttemptPhase.RETAINING,
            status=RefreshAttemptStatus.LEASE_EXPIRED,
            retention_started_at=NOW + timedelta(seconds=60), captured_payload_hash=DIGEST,
            updated_at=NOW + timedelta(seconds=61), failure_code=RefreshFailureCode.LEASE_EXPIRED)


@pytest.mark.parametrize("batch_id", ["secret=fixture", "https://example.invalid", ""])
def test_batch_reference_is_bounded_and_cannot_embed_exception_or_auth_url(batch_id: str) -> None:
    attempt = start_refresh_retention(new_refresh_attempt(LEASE, now=NOW), LEASE,
                                      now=NOW, captured_payload_hash=DIGEST)
    with pytest.raises(ValueError):
        finish_refresh_retention(attempt, LEASE, now=NOW, ingestion_batch_id=batch_id)


def test_invalid_policy_type_is_rejected_not_replaced_by_defaults() -> None:
    with pytest.raises(ValueError):
        new_refresh_attempt(LEASE, now=NOW, policy=False)


def test_old_lease_cannot_complete_a_later_generation_value() -> None:
    current_lease = replace(LEASE, generation=2, nonce="2" * 32)
    current = start_refresh_retention(new_refresh_attempt(current_lease, now=NOW), current_lease,
                                      now=NOW, captured_payload_hash=DIGEST)
    with pytest.raises(ValueError):
        finish_refresh_retention(current, LEASE, now=NOW, ingestion_batch_id="stale-batch")
