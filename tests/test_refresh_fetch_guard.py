"""Committed fetch ownership checks only; no network, capture or admission."""

import sqlite3
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from tong_quant.data.refresh_attempts import RefreshFailureCode
from tong_quant.data.refresh_plan import build_refresh_plan, parse_refresh_watchlist
from tong_quant.data.storage import refresh
from tong_quant.data.storage.refresh import SQLiteRefreshRepository
from tong_quant.data.storage.sqlite import SQLiteStore

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 11, 5, tzinfo=UTC)


@pytest.fixture
def ledger(tmp_path):
    store = SQLiteStore(tmp_path / "synthetic-fetch.sqlite3")
    store.initialize()
    time = [NOW]
    repo = SQLiteRefreshRepository(store, clock=lambda: time[0])
    plan = build_refresh_plan(
        parse_refresh_watchlist((ROOT / "config/refresh/example-watchlist.toml").read_text()),
        planned_as_of=NOW - timedelta(seconds=1), git_commit="a" * 40, git_dirty=True,
    )
    return SimpleNamespace(store=store, repo=repo, time=time, plan=plan)


def _claimed(ledger, index=0):
    entry = ledger.plan["entries"][index]
    job = ledger.repo.register(
        ledger.plan, scope_hash=entry["scope_hash"], trigger_reference="fetch-guard-test",
    )
    attempt = ledger.repo.claim(job.job_id, worker_id="test-worker", expected_version=0)
    assert attempt is not None
    return job, attempt


@pytest.mark.parametrize("index", range(5))
def test_all_planned_scopes_allow_only_a_read_only_fetch_check(ledger, index):
    job, attempt = _claimed(ledger, index)
    before = ledger.repo.get(job.job_id)
    assert ledger.repo.validate_fetch_lease(attempt.lease) is None
    assert ledger.repo.get(job.job_id) == before
    assert ledger.repo.attempts(job.job_id) == (attempt,)
    assert ledger.store.table_count("ingestion_batches") == 0
    assert ledger.store.table_count("provider_artifacts") == 0


@pytest.mark.parametrize("seconds,valid", [(0, True), (59.999999, True), (60, False),
                                          (60.000001, False), (-0.000001, False)])
def test_utc_lease_boundaries_do_not_extend_the_lease(ledger, seconds, valid):
    job, attempt = _claimed(ledger)
    ledger.time[0] = NOW + timedelta(seconds=seconds)
    if valid:
        assert ledger.repo.validate_fetch_lease(attempt.lease) is None
    else:
        with pytest.raises(ValueError, match="fetch lease is not live"):
            ledger.repo.validate_fetch_lease(attempt.lease)
    assert ledger.repo.attempts(job.job_id) == (attempt,)


def test_timezone_equivalence_and_naive_clock(ledger):
    _, attempt = _claimed(ledger)
    ledger.time[0] = NOW.astimezone(timezone(timedelta(hours=8)))
    assert ledger.repo.validate_fetch_lease(attempt.lease) is None
    ledger.time[0] = NOW.replace(tzinfo=None)
    with pytest.raises(ValueError):
        ledger.repo.validate_fetch_lease(attempt.lease)


@pytest.mark.parametrize("changed", [
    {"nonce": "f" * 32}, {"generation": 2}, {"worker_id": "secret-sentinel"},
    {"job_id": "e" * 64},
])
def test_wrong_owner_or_identity_is_rejected_without_echoing_values(ledger, changed):
    _, attempt = _claimed(ledger)
    with pytest.raises(ValueError) as error:
        ledger.repo.validate_fetch_lease(replace(attempt.lease, **changed))
    assert "secret-sentinel" not in str(error.value)


@pytest.mark.parametrize("lease", [None, {}, "not-a-lease"])
def test_untyped_lease_does_not_enter_the_reader(ledger, lease):
    with pytest.raises(ValueError, match="typed lease"):
        ledger.repo.validate_fetch_lease(lease)


@pytest.mark.parametrize("context", ["read_snapshot", "transaction"])
def test_caller_store_context_is_rejected_and_left_untouched(ledger, context):
    job, attempt = _claimed(ledger)
    before = ledger.repo.get(job.job_id)
    assert ledger.store.has_active_connection is False
    with getattr(ledger.store, context)():
        assert ledger.store.has_active_connection is True
        with pytest.raises(ValueError, match="no active store context"):
            ledger.repo.validate_fetch_lease(attempt.lease)
        assert ledger.repo.get(job.job_id) == before
    assert ledger.store.has_active_connection is False
    assert ledger.repo.validate_fetch_lease(attempt.lease) is None


def test_fetch_and_retention_guards_are_not_interchangeable(ledger):
    _, attempt = _claimed(ledger)
    with pytest.raises(ValueError, match="retention lease is not live"):
        ledger.repo.validate_live_lease(attempt.lease)
    ledger.time[0] += timedelta(seconds=1)
    ledger.repo.start_retention(attempt.lease, captured_payload_hash="b" * 64)
    with pytest.raises(ValueError, match="fetch lease is not live"):
        ledger.repo.validate_fetch_lease(attempt.lease)
    with ledger.store.transaction():
        assert ledger.repo.validate_live_lease(attempt.lease) is None


def test_terminal_failure_cannot_authorize_a_fetch(ledger):
    _, attempt = _claimed(ledger)
    ledger.time[0] += timedelta(seconds=1)
    ledger.repo.fail(attempt.lease, failure_code=RefreshFailureCode.INVALID_RESPONSE)
    with pytest.raises(ValueError):
        ledger.repo.validate_fetch_lease(attempt.lease)


@pytest.mark.parametrize("action", ["retain", "retry", "expire"])
def test_another_process_can_invalidate_the_parents_cached_lease(ledger, action):
    job, attempt = _claimed(ledger)
    child = """
import sys
from datetime import datetime, timedelta
from pathlib import Path
from tong_quant.data.refresh_attempts import RefreshFailureCode
from tong_quant.data.storage.refresh import SQLiteRefreshRepository
from tong_quant.data.storage.sqlite import SQLiteStore
path, job_id, instant, action = sys.argv[1:]
time = [datetime.fromisoformat(instant)]
repo = SQLiteRefreshRepository(SQLiteStore(Path(path)), clock=lambda: time[0])
lease = repo.attempts(job_id)[-1].lease
if action == 'retain':
    repo.start_retention(lease, captured_payload_hash='c' * 64)
elif action == 'retry':
    repo.fail(lease, failure_code=RefreshFailureCode.TIMEOUT)
    time[0] += timedelta(seconds=5)
    job = repo.get(job_id)
    assert repo.claim(job_id, worker_id='child-worker', expected_version=job.row_version)
else:
    time[0] += timedelta(seconds=59)
    assert repo.recover_expired(job_id) is not None
"""
    result = subprocess.run(
        [sys.executable, "-c", child, str(ledger.store.path), job.job_id,
         (NOW + timedelta(seconds=1)).isoformat(), action],
        capture_output=True, text=True, check=False, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    ledger.time[0] = NOW + timedelta(seconds=61 if action == "expire" else 7)
    with pytest.raises(ValueError):
        ledger.repo.validate_fetch_lease(attempt.lease)
    if action == "retry":
        current = ledger.repo.attempts(job.job_id)[-1]
        assert current.lease.generation == 2
        assert ledger.repo.validate_fetch_lease(current.lease) is None


@pytest.mark.parametrize("key", ["schema_version", "migration_head"])
def test_metadata_is_checked_fresh_not_only_at_repository_construction(ledger, key):
    _, attempt = _claimed(ledger)
    with sqlite3.connect(ledger.store.path) as conn:
        conn.execute("UPDATE schema_metadata SET value = 'unknown-version' WHERE key = ?", (key,))
    with pytest.raises(ValueError, match="explicitly migrated"):
        ledger.repo.validate_fetch_lease(attempt.lease)


def test_runtime_plan_drift_requires_revalidation_without_rewriting_job(ledger, monkeypatch):
    job, attempt = _claimed(ledger)
    before = ledger.repo.get(job.job_id)
    monkeypatch.setattr(refresh, "build_refresh_plan", lambda *args, **kwargs: {})
    with pytest.raises(ValueError, match="current validated contract"):
        ledger.repo.validate_fetch_lease(attempt.lease)
    assert ledger.repo.get(job.job_id) == before


def test_guard_opens_one_new_read_only_connection_and_closes_it(ledger, monkeypatch):
    _, attempt = _claimed(ledger)
    original = SQLiteStore._new_connection
    connections = []

    def observe(store):
        connection = original(store)
        connections.append((store.read_only, connection))
        return connection

    monkeypatch.setattr(SQLiteStore, "_new_connection", observe)
    assert ledger.repo.validate_fetch_lease(attempt.lease) is None
    assert len(connections) == 1 and connections[0][0] is True
    with pytest.raises(sqlite3.ProgrammingError):
        connections[0][1].execute("SELECT 1")


def test_read_only_store_is_supported_but_not_an_ambient_read_snapshot(ledger):
    _, attempt = _claimed(ledger)
    store = SQLiteStore(ledger.store.path, read_only=True)
    reader = SQLiteRefreshRepository(store, clock=lambda: NOW)
    assert reader.validate_fetch_lease(attempt.lease) is None
    with store.read_snapshot(), pytest.raises(ValueError, match="no active store context"):
        reader.validate_fetch_lease(attempt.lease)


def test_missing_database_is_never_recreated(ledger):
    _, attempt = _claimed(ledger)
    ledger.store.path.unlink()
    with pytest.raises(sqlite3.OperationalError):
        ledger.repo.validate_fetch_lease(attempt.lease)
    assert not ledger.store.path.exists()
