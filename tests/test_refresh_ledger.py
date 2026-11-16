"""Synthetic local persistence/crash tests; never real captures or research admission."""

import sqlite3
import subprocess
import sys
from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path

import pytest

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.providers.contracts import ProviderDatasetRequest
from tong_quant.data.providers.yahoo_snapshot import (
    YahooGlobalSnapshotAdapter,
    YahooSnapshotCapture,
)
from tong_quant.data.refresh_attempts import (
    RefreshAttemptPolicy,
    RefreshAttemptStatus,
    RefreshFailureCode,
)
from tong_quant.data.refresh_plan import build_refresh_plan, parse_refresh_watchlist
from tong_quant.data.storage import migrations
from tong_quant.data.storage.engineering import SQLiteIntegrityService
from tong_quant.data.storage.migrations import (
    MIGRATION_HEAD,
    PORTFOLIO_EVIDENCE_LINEAGE,
    SCHEMA_DEFINITION_HASHES,
    schema_fingerprint,
)
from tong_quant.data.storage.refresh import SQLiteRefreshRepository
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 11, 3, 8, tzinfo=UTC)


def _plan():
    return build_refresh_plan(
        parse_refresh_watchlist((ROOT / "config/refresh/example-watchlist.toml").read_text()),
        planned_as_of=NOW - timedelta(seconds=1),
        git_commit="a" * 40,
        git_dirty=True,
    )


@pytest.fixture
def ledger(tmp_path):
    store = SQLiteStore(tmp_path / "refresh.sqlite3")
    store.initialize()
    time = [NOW]
    repo = SQLiteRefreshRepository(store, clock=lambda: time[0])
    plan = _plan()
    entry = next(item for item in plan["entries"] if item["scope"]["market"] == "us")
    job = repo.register(
        plan, scope_hash=entry["scope_hash"], trigger_reference="synthetic-trigger-1"
    )
    return store, repo, job, time, FileSystemArtifactStore(tmp_path / "artifacts")


def _prepared(ledger, kind="success", market=Market.US):
    store, repo, job, time, artifacts = ledger
    if market is not Market.US:
        plan = _plan()
        entry = next(
            item
            for item in plan["entries"]
            if item["scope"]["market"] == market.value
            and item["scope"]["dataset"] == "global_equity_price_snapshot"
        )
        job = repo.register(
            plan, scope_hash=entry["scope_hash"], trigger_reference="synthetic-global"
        )
    attempt = repo.claim(job.job_id, worker_id="worker-a", expected_version=job.row_version)
    assert attempt is not None
    time[0] = NOW + timedelta(seconds=1)
    entry = job.entry
    scope = entry["scope"]
    request = ProviderDatasetRequest(
        scope["dataset"],
        Market(scope["market"]),
        scope["subject"],
        NOW + timedelta(seconds=2),
        entry["request_parameters"],
    )
    if kind == "success":
        capture = YahooSnapshotCapture(
            {
                "chart": {
                    "error": None,
                    "result": [
                        {
                            "meta": {
                                "symbol": request.subject,
                                "currency": scope["currency"],
                                "exchangeName": scope["exchange"],
                                "instrumentType": "EQUITY",
                                "exchangeTimezoneName": scope["timezone"],
                                "dataGranularity": "1d",
                            },
                            "timestamp": [int(datetime(2026, 11, 2, 1, tzinfo=UTC).timestamp())],
                            "indicators": {
                                "quote": [
                                    {
                                        "open": [10],
                                        "high": [11],
                                        "low": [9],
                                        "close": [10],
                                        "volume": [10000],
                                    }
                                ]
                            },
                        }
                    ],
                }
            }
        )
    else:
        capture = YahooSnapshotCapture(None, "provider_unavailable")
    adapter = YahooGlobalSnapshotAdapter(download=lambda _: capture, clock=lambda: time[0])
    batch = adapter.fetch(request)
    time[0] = NOW + timedelta(seconds=2)
    repo.start_retention(attempt.lease, captured_payload_hash=batch.raw_data_hash)

    @dataclass
    class Captured:
        provider_id: str = "yahoo_finance"

        def capabilities(self):
            return adapter.capabilities()

        def fetch(self, received):
            assert received == request
            return batch

    return job, attempt.lease, request, batch, Captured()


def test_job_registration_is_idempotent_and_budget_cannot_change(ledger):
    store, repo, job, time, _ = ledger
    assert (
        repo.register(_plan(), scope_hash=job.scope_hash, trigger_reference=job.trigger_reference)
        == job
    )
    with pytest.raises(ValueError, match="immutable"):
        repo.register(
            _plan(),
            scope_hash=job.scope_hash,
            trigger_reference=job.trigger_reference,
            policy=RefreshAttemptPolicy(maximum_attempts=4),
        )
    assert store.table_count("refresh_jobs") == 1
    assert store.table_count("refresh_attempts") == 0


@pytest.mark.parametrize("kind", ["hash", "secret", "unsupported", "scope", "future"])
def test_invalid_or_unavailable_plan_cannot_be_registered(ledger, kind):
    store, repo, job, time, _ = ledger
    plan = deepcopy(_plan())
    if kind == "hash":
        plan["git_dirty"] = False
    elif kind == "secret":
        plan["api_key"] = "private-fixture"
    elif kind == "unsupported":
        plan["entries"][0]["request_contract_status"] = "UNSUPPORTED"
    elif kind == "future":
        time[0] = NOW - timedelta(seconds=2)
    scope = "f" * 64 if kind == "scope" else job.scope_hash
    with pytest.raises(ValueError):
        repo.register(plan, scope_hash=scope, trigger_reference="invalid-trigger")
    assert store.table_count("refresh_jobs") == 1


def test_real_processes_compete_for_exactly_one_claim(ledger):
    store, repo, job, _, _ = ledger
    code = """
import sys
from pathlib import Path
from datetime import datetime
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.data.storage.refresh import SQLiteRefreshRepository
repo = SQLiteRefreshRepository(SQLiteStore(Path(sys.argv[1])),
    clock=lambda: datetime.fromisoformat(sys.argv[3]))
print('ready', flush=True)
sys.stdin.readline()
result = repo.claim(sys.argv[2], worker_id='worker-' + sys.argv[4], expected_version=0)
print('claimed' if result is not None else 'not_claimed', flush=True)
"""
    children = [
        subprocess.Popen(
            [sys.executable, "-c", code, str(store.path), job.job_id, NOW.isoformat(), str(index)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for index in range(2)
    ]
    try:
        for child in children:
            assert child.stdout.readline().strip() == "ready"
        for child in children:
            child.stdin.write("\n")
            child.stdin.flush()
        results = [child.communicate(timeout=20) for child in children]
        assert all(child.returncode == 0 for child in children), results
        assert sorted(output.strip() for output, error in results) == ["claimed", "not_claimed"]
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
                child.communicate(timeout=5)
    assert len(repo.attempts(job.job_id)) == 1


def test_process_exit_before_fetch_preserves_attempt_and_blocks_blind_reclaim(ledger):
    store, repo, job, time, _ = ledger
    code = """
import os, sys
from pathlib import Path
from datetime import datetime
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.data.storage.refresh import SQLiteRefreshRepository
repo = SQLiteRefreshRepository(SQLiteStore(Path(sys.argv[1])),
    clock=lambda: datetime.fromisoformat(sys.argv[3]))
assert repo.claim(sys.argv[2], worker_id='crashed-worker', expected_version=0) is not None
os._exit(0)
"""
    subprocess.run(
        [sys.executable, "-c", code, str(store.path), job.job_id, NOW.isoformat()],
        check=True,
        timeout=20,
        capture_output=True,
    )
    time[0] = NOW + timedelta(seconds=60)
    recovered = repo.recover_expired(job.job_id)
    assert recovered.status is RefreshAttemptStatus.LEASE_EXPIRED
    assert recovered.captured_payload_hash is None and recovered.ingestion_batch_id is None
    assert repo.get(job.job_id).status == "reconciliation_required"
    assert (
        repo.claim(
            job.job_id, worker_id="next-worker", expected_version=repo.get(job.job_id).row_version
        )
        is None
    )
    assert repo.recover_expired(job.job_id) is None
    assert store.table_count("ingestion_batches") == 0


def test_transient_fetch_retries_survive_reopen_and_exhaust_budget(ledger):
    store, repo, job, time, _ = ledger
    for generation in range(1, 4):
        current = repo.get(job.job_id)
        attempt = repo.claim(
            job.job_id, worker_id="retry-worker", expected_version=current.row_version
        )
        assert attempt.lease.generation == generation
        failed = repo.fail(attempt.lease, failure_code=RefreshFailureCode.TIMEOUT)
        reopened = SQLiteRefreshRepository(SQLiteStore(store.path), clock=lambda: time[0])
        assert reopened.attempts(job.job_id)[-1] == failed
        if generation < 3:
            assert (
                reopened.claim(
                    job.job_id,
                    worker_id="early-worker",
                    expected_version=reopened.get(job.job_id).row_version,
                )
                is None
            )
            time[0] = failed.retry_at
    assert repo.get(job.job_id).status == "exhausted"
    assert (
        repo.claim(
            job.job_id, worker_id="over-budget", expected_version=repo.get(job.job_id).row_version
        )
        is None
    )


@pytest.mark.parametrize("market", [Market.US, Market.HONG_KONG, Market.MALAYSIA])
@pytest.mark.parametrize("kind", ["success", "failure"])
def test_atomic_batch_links_survive_restart_without_promoting_data(ledger, market, kind):
    store, repo, _, time, artifacts = ledger
    job, lease, request, batch, adapter = _prepared(ledger, kind, market)
    result = ProviderNeutralIngestionService(
        store, artifact_store=artifacts, clock=lambda: time[0]
    ).ingest(adapter, request, refresh_lease=lease)
    reopened = SQLiteRefreshRepository(SQLiteStore(store.path), clock=lambda: time[0])
    retained = reopened.attempts(job.job_id)[-1]
    assert retained.ingestion_batch_id == result.batch_id
    assert retained.status is (
        RefreshAttemptStatus.DATA_RETAINED
        if kind == "success"
        else RefreshAttemptStatus.FAILURE_SNAPSHOT_RETAINED
    )
    assert retained.failure_code is (
        None if kind == "success" else RefreshFailureCode.PROVIDER_UNAVAILABLE
    )
    assert reopened.get(job.job_id).status == "reconciliation_required"
    assert store.ingestion_batch(result.batch_id)["raw_response_hash"] == batch.raw_data_hash
    assert store.table_count("provider_evidence_records") == 1
    assert store.table_count("research_reports") == store.table_count("signals") == 0
    assert store.table_count("daily_bars") == 0
    assert retained.retry_at is None


def test_commit_then_caller_crash_keeps_precise_batch_not_a_second_attempt(ledger):
    store, repo, _, time, artifacts = ledger
    job, lease, request, batch, adapter = _prepared(ledger)
    with pytest.raises(RuntimeError, match="caller-crash"):
        ProviderNeutralIngestionService(
            store, artifact_store=artifacts, clock=lambda: time[0]
        ).ingest(adapter, request, refresh_lease=lease)
        raise RuntimeError("caller-crash")
    reopened = SQLiteRefreshRepository(SQLiteStore(store.path), clock=lambda: time[0])
    assert store.ingestion_batch(reopened.attempts(job.job_id)[-1].ingestion_batch_id) is not None
    assert (
        reopened.claim(
            job.job_id,
            worker_id="do-not-repeat",
            expected_version=reopened.get(job.job_id).row_version,
        )
        is None
    )
    assert store.table_count("ingestion_batches") == 1


@pytest.mark.parametrize("failure", ["expired", "association_fault"])
def test_failure_at_atomic_link_rolls_back_all_database_writes(ledger, monkeypatch, failure):
    store, repo, _, time, artifacts = ledger
    job, lease, request, batch, adapter = _prepared(ledger)
    if failure == "expired":
        original = store.save_provider_evidence_records

        def late(*args, **kwargs):
            result = original(*args, **kwargs)
            time[0] = NOW + timedelta(seconds=60)
            return result

        monkeypatch.setattr(store, "save_provider_evidence_records", late)
    else:
        with (
            store.transaction(),
            store.repository_connection(require_transaction=True) as connection,
        ):
            connection.execute("""CREATE TRIGGER synthetic_attach_failure
                BEFORE UPDATE ON refresh_attempts
                WHEN NEW.ingestion_batch_id IS NOT NULL
                BEGIN SELECT RAISE(ABORT, 'synthetic association fault'); END""")
    with pytest.raises((ValueError, sqlite3.IntegrityError)):
        ProviderNeutralIngestionService(
            store, artifact_store=artifacts, clock=lambda: time[0]
        ).ingest(adapter, request, refresh_lease=lease)
    for table in (
        "ingestion_batches",
        "provider_evidence_records",
        "provider_artifacts",
        "provider_artifact_observations",
        "raw_dataset_fingerprints",
    ):
        assert store.table_count(table) == 0
    assert repo.get(job.job_id).status == "running"
    assert repo.attempts(job.job_id)[-1].ingestion_batch_id is None
    # DB rollback does not authorize deleting content another writer may have adopted.
    retained = [path for path in artifacts.root.rglob("*") if path.is_file()]
    assert len(retained) == 1
    assert sha256(retained[0].read_bytes()).hexdigest() == batch.artifacts[0].content_hash


@pytest.mark.parametrize("kind", ["lease", "scope", "hash", "parameters", "clock"])
def test_changed_or_stale_inputs_cannot_publish_a_batch(ledger, kind):
    store, repo, _, time, artifacts = ledger
    job, lease, request, batch, adapter = _prepared(ledger)
    if kind == "lease":
        lease = replace(lease, nonce="f" * 32)
    elif kind == "scope":
        request = replace(request, subject="OTHER")
    elif kind == "hash":
        with (
            store.transaction(),
            store.repository_connection(require_transaction=True) as connection,
        ):
            connection.execute(
                "UPDATE refresh_attempts SET captured_payload_hash = ? WHERE job_id = ?",
                ("f" * 64, job.job_id),
            )
    elif kind == "parameters":
        request = replace(request, parameters={**request.parameters, "start_date": "2026-02-01"})
    else:
        time[0] = NOW + timedelta(seconds=1)
    if kind in {"scope", "parameters"}:
        with pytest.raises(ValueError):
            repo.validate_retention(lease, request, batch)
    else:
        with pytest.raises(ValueError):
            ProviderNeutralIngestionService(
                store, artifact_store=artifacts, clock=lambda: time[0]
            ).ingest(adapter, request, refresh_lease=lease)
    assert store.table_count("ingestion_batches") == 0


def test_association_requires_ingestion_transaction_and_history_is_immutable(ledger):
    store, repo, _, time, _ = ledger
    job, lease, request, batch, adapter = _prepared(ledger)
    with pytest.raises(RuntimeError, match="transaction"):
        repo.attach_ingestion(lease, request, batch, "uncommitted-batch")
    failed = repo.fail(lease, failure_code=RefreshFailureCode.INTERNAL_ERROR)
    assert failed.reconciliation_required
    with store.repository_connection() as connection:
        for statement in (
            "UPDATE refresh_jobs SET policy_json = '{}'",
            "UPDATE refresh_attempts SET status = 'running'",
            "DELETE FROM refresh_attempts",
            "DELETE FROM refresh_jobs",
        ):
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute(statement)
    assert store.table_count("refresh_attempts") == 1


def _legacy(path):
    store = SQLiteStore(path)
    store.initialize()
    previous = PORTFOLIO_EVIDENCE_LINEAGE.migration_id
    with store.repository_connection() as connection:
        connection.execute("DROP TRIGGER refresh_batch_immutable")
        connection.execute("DROP TABLE refresh_attempts")
        connection.execute("DROP TABLE refresh_jobs")
        connection.execute("DELETE FROM schema_migrations WHERE migration_id > ?", (previous,))
        connection.execute("DELETE FROM schema_fingerprints")
        fingerprint = schema_fingerprint(connection)
        connection.execute(
            "INSERT INTO schema_fingerprints VALUES (?, ?, ?, ?)",
            (previous, fingerprint, SCHEMA_DEFINITION_HASHES[previous], NOW.isoformat()),
        )
        for key, value in (
            ("migration_head", previous),
            ("schema_version", "0.8.2"),
            ("schema_fingerprint", fingerprint),
        ):
            connection.execute("UPDATE schema_metadata SET value = ? WHERE key = ?", (value, key))
    return store


def test_legacy_open_refuses_silent_upgrade_and_explicit_temp_migration_is_idempotent(tmp_path):
    store = _legacy(tmp_path / "legacy.sqlite3")
    before = sha256(store.path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="migrated"):
        SQLiteRefreshRepository(store)
    assert sha256(store.path.read_bytes()).hexdigest() == before
    store.initialize()
    first = SQLiteIntegrityService().audit(store.path)
    assert first.passed and first.migration_head == MIGRATION_HEAD
    store.initialize()
    assert SQLiteIntegrityService().audit(store.path).audit_hash == first.audit_hash
    assert store.table_count("refresh_jobs") == store.table_count("refresh_attempts") == 0


def test_new_ddl_and_migration_ledger_roll_back_together(tmp_path, monkeypatch):
    store = _legacy(tmp_path / "legacy.sqlite3")
    original = migrations._apply_migration

    def fail(connection, migration):
        original(connection, migration)
        if migration is migrations.REFRESH_LEDGER:
            raise RuntimeError("synthetic migration failure")

    monkeypatch.setattr(migrations, "_apply_migration", fail)
    with pytest.raises(RuntimeError, match="synthetic"):
        store.initialize()
    with store.repository_connection() as connection:
        assert (
            connection.execute(
                "SELECT name FROM sqlite_master WHERE name IN ('refresh_jobs','refresh_attempts')"
            ).fetchall()
            == []
        )
    assert store.migration_head() == PORTFOLIO_EVIDENCE_LINEAGE.migration_id


def test_missing_database_is_not_created_and_write_helper_requires_transaction(tmp_path):
    path = tmp_path / "absent.sqlite3"
    with pytest.raises(ValueError):
        SQLiteRefreshRepository(SQLiteStore(path))
    assert not path.exists()
    store = SQLiteStore(tmp_path / "initialized.sqlite3")
    store.initialize()
    with pytest.raises(RuntimeError), store.repository_connection(require_transaction=True):
        pytest.fail("write connection provided outside transaction")


def test_foreign_key_rejects_a_nonexistent_batch(ledger):
    store, repo, job, _, _ = ledger
    repo.claim(job.job_id, worker_id="worker-a", expected_version=0)
    with (
        store.repository_connection() as connection,
        pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"),
    ):
        connection.execute("UPDATE refresh_attempts SET ingestion_batch_id = 'absent-batch'")
    assert repo.attempts(job.job_id)[0].ingestion_batch_id is None


def test_read_only_repository_reconstructs_without_writing(ledger):
    store, repo, job, time, _ = ledger
    repo.claim(job.job_id, worker_id="worker-a", expected_version=0)
    before = sha256(store.path.read_bytes()).hexdigest()
    readonly = SQLiteRefreshRepository(
        SQLiteStore(store.path, read_only=True), clock=lambda: time[0]
    )
    assert readonly.get(job.job_id) == repo.get(job.job_id)
    assert readonly.attempts(job.job_id) == repo.attempts(job.job_id)
    with pytest.raises((RuntimeError, sqlite3.OperationalError)):
        readonly.fail(
            repo.attempts(job.job_id)[0].lease, failure_code=RefreshFailureCode.INTERNAL_ERROR
        )
    assert sha256(store.path.read_bytes()).hexdigest() == before


@pytest.mark.parametrize(
    "code", [RefreshFailureCode.PERMISSION_DENIED, RefreshFailureCode.UNSUPPORTED_ENDPOINT]
)
def test_provider_permissions_and_unsupported_endpoints_stop_without_retry(ledger, code):
    _, repo, job, _, _ = ledger
    attempt = repo.claim(job.job_id, worker_id="worker-a", expected_version=0)
    repo.fail(attempt.lease, failure_code=code)
    assert repo.get(job.job_id).status == "failed"
    assert (
        repo.claim(
            job.job_id, worker_id="no-loop", expected_version=repo.get(job.job_id).row_version
        )
        is None
    )


def test_akshare_captured_request_uses_empty_evidence_parameters_not_legacy_parameters(ledger):
    from tong_quant.data.providers.contracts import (
        ProviderCapabilityStatus,
        ProviderDatasetCapability,
        ProviderEvidenceBatch,
    )
    from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel

    store, repo, _, time, _ = ledger
    plan = _plan()
    entry = next(item for item in plan["entries"] if item["scope"]["market"] == "china_a")
    job = repo.register(plan, scope_hash=entry["scope_hash"], trigger_reference="synthetic-akshare")
    attempt = repo.claim(job.job_id, worker_id="china-worker", expected_version=0)
    params = {key: value for key, value in entry["request_parameters"].items() if key != "market"}
    params.update(
        {
            "fetch_version": entry["provider_contract_versions"]["fetch"],
            "normalization_version": entry["provider_contract_versions"]["normalization"],
            "symbol_routing_version": entry["provider_contract_versions"]["routing"],
        }
    )
    content_hash = sha256(b"Synthetic empty legacy snapshot, not upstream wire bytes").hexdigest()
    time[0] = NOW + timedelta(seconds=2)
    repo.start_retention(attempt.lease, captured_payload_hash=content_hash)
    request = ProviderDatasetRequest("a_share_daily", Market.CHINA_A, "000063", time[0], {})
    batch = ProviderEvidenceBatch(
        "akshare",
        "a_share_daily",
        Market.CHINA_A,
        NOW + timedelta(seconds=1),
        "akshare:stock_zh_a_hist",
        params,
        content_hash,
        0,
        (),
        (),
    )

    class Captured:
        provider_id = "akshare"

        def capabilities(self):
            return (
                ProviderDatasetCapability(
                    "akshare",
                    "a_share_daily",
                    (Market.CHINA_A,),
                    ProviderCapabilityStatus.DEGRADED,
                    DataTrustLevel.LOW,
                    AvailabilityPrecision.RETRIEVAL_TIME,
                    False,
                    (),
                    (),
                ),
            )

        def fetch(self, received):
            assert received == request
            return batch

    result = ProviderNeutralIngestionService(store, clock=lambda: time[0]).ingest(
        Captured(), request, refresh_lease=attempt.lease
    )
    retained = repo.attempts(job.job_id)[0]
    assert retained.ingestion_batch_id == result.batch_id
    assert retained.failure_code is RefreshFailureCode.INSUFFICIENT_DATA
    assert retained.reconciliation_required


def test_unsupported_dataset_stays_visible_in_plan_but_is_not_a_claimable_job(ledger):
    _, repo, _, _, _ = ledger
    watchlist = parse_refresh_watchlist(
        (ROOT / "config/refresh/example-watchlist.toml").read_text()
    )
    watchlist = replace(
        watchlist, scopes=(replace(watchlist.scopes[0], dataset="unknown_dataset"),)
    )
    plan = build_refresh_plan(watchlist, planned_as_of=NOW, git_commit="a" * 40, git_dirty=True)
    assert plan["entries"][0]["request_contract_status"] == "UNSUPPORTED"
    with pytest.raises(ValueError, match="unsupported"):
        repo.register(
            plan, scope_hash=plan["entries"][0]["scope_hash"], trigger_reference="unsupported"
        )


def test_clock_rollback_cannot_claim_or_change_attempt(ledger):
    _, repo, job, time, _ = ledger
    time[0] = NOW - timedelta(microseconds=1)
    with pytest.raises(ValueError, match="backwards"):
        repo.claim(job.job_id, worker_id="worker-a", expected_version=0)
    time[0] = NOW
    attempt = repo.claim(job.job_id, worker_id="worker-a", expected_version=0)
    time[0] = NOW - timedelta(microseconds=1)
    with pytest.raises(ValueError):
        repo.fail(attempt.lease, failure_code=RefreshFailureCode.TIMEOUT)
    assert repo.get(job.job_id).status == "running"


def test_linked_completed_batch_cannot_be_rewritten(ledger):
    store, repo, _, time, artifacts = ledger
    job, lease, request, batch, adapter = _prepared(ledger)
    result = ProviderNeutralIngestionService(
        store, artifact_store=artifacts, clock=lambda: time[0]
    ).ingest(adapter, request, refresh_lease=lease)
    with (
        store.repository_connection() as connection,
        pytest.raises(sqlite3.IntegrityError, match="immutable"),
    ):
        connection.execute(
            "UPDATE ingestion_batches SET raw_response_hash = ? WHERE batch_id = ?",
            ("f" * 64, result.batch_id),
        )
    assert store.ingestion_batch(result.batch_id)["raw_response_hash"] == batch.raw_data_hash


def test_native_financial_permission_failure_is_retained_not_a_parser_defect(ledger):
    from tong_quant.data.providers.yahoo_fundamentals import (
        YahooFundamentalCapture,
        YahooFundamentalSnapshotAdapter,
    )

    store, repo, _, time, artifacts = ledger
    plan = _plan()
    entry = next(
        item
        for item in plan["entries"]
        if item["scope"]["dataset"] == "global_native_fundamental_snapshot"
    )
    job = repo.register(plan, scope_hash=entry["scope_hash"], trigger_reference="native-permission")
    attempt = repo.claim(job.job_id, worker_id="native-worker", expected_version=0)
    time[0] = NOW + timedelta(seconds=1)
    request = ProviderDatasetRequest(
        entry["scope"]["dataset"],
        Market.MALAYSIA,
        "1155.KL",
        NOW + timedelta(seconds=2),
        entry["request_parameters"],
    )
    original = YahooFundamentalSnapshotAdapter(
        download=lambda _: YahooFundamentalCapture(None, "http_401"),
        clock=lambda: NOW + timedelta(seconds=1),
    )
    batch = original.fetch(request)
    time[0] = NOW + timedelta(seconds=2)
    repo.start_retention(attempt.lease, captured_payload_hash=batch.raw_data_hash)

    class Captured:
        provider_id = "yahoo_finance"

        def capabilities(self):
            return original.capabilities()

        def fetch(self, _):
            return batch

    ProviderNeutralIngestionService(store, artifact_store=artifacts, clock=lambda: time[0]).ingest(
        Captured(), request, refresh_lease=attempt.lease
    )
    retained = repo.attempts(job.job_id)[-1]
    assert retained.failure_code is RefreshFailureCode.PERMISSION_DENIED
    assert retained.status is RefreshAttemptStatus.FAILURE_SNAPSHOT_RETAINED
    assert retained.retry_at is None and retained.reconciliation_required
