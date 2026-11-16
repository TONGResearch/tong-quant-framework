"""Synthetic exact-link inspection; never network captures or operator databases."""

import json
import sqlite3
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

from tong_quant.data import refresh_reconciliation as inspection
from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.providers.contracts import ProviderDatasetRequest
from tong_quant.data.providers.yahoo_snapshot import (
    YahooGlobalSnapshotAdapter,
    YahooSnapshotCapture,
)
from tong_quant.data.refresh_plan import build_refresh_plan, parse_refresh_watchlist
from tong_quant.data.storage.refresh import SQLiteRefreshRepository
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 11, 3, 8, tzinfo=UTC)
CUTOFF = datetime(2099, 1, 1, tzinfo=UTC)


@pytest.fixture
def receipt(tmp_path):
    store = SQLiteStore(tmp_path / "inspection.sqlite3")
    store.initialize()
    clock = [NOW]
    repo = SQLiteRefreshRepository(store, clock=lambda: clock[0])
    plan = build_refresh_plan(
        parse_refresh_watchlist((ROOT / "config/refresh/example-watchlist.toml").read_text()),
        planned_as_of=NOW - timedelta(seconds=1), git_commit="a" * 40, git_dirty=True,
    )
    return SimpleNamespace(store=store, repo=repo, plan=plan, clock=clock,
                           root=tmp_path / "originals")


def _job(receipt, market="us"):
    entry = next(item for item in receipt.plan["entries"]
                 if item["scope"]["market"] == market
                 and item["scope"]["dataset"] == "global_equity_price_snapshot")
    return receipt.repo.register(
        receipt.plan, scope_hash=entry["scope_hash"], trigger_reference="synthetic-inspection",
    )


def _retained(receipt, market="us", failed=False):
    job = _job(receipt, market)
    attempt = receipt.repo.claim(job.job_id, worker_id="inspector-test", expected_version=0)
    assert attempt is not None
    scope = job.entry["scope"]
    request = ProviderDatasetRequest(
        scope["dataset"], Market(market), scope["subject"], NOW + timedelta(seconds=2),
        job.entry["request_parameters"],
    )
    capture = YahooSnapshotCapture({
        "chart": {"error": None, "result": [{
            "meta": {"symbol": request.subject, "currency": scope["currency"],
                     "exchangeName": scope["exchange"], "instrumentType": "EQUITY",
                     "exchangeTimezoneName": scope["timezone"], "dataGranularity": "1d"},
            "timestamp": [int(datetime(2026, 11, 2, 1, tzinfo=UTC).timestamp())],
            "indicators": {"quote": [{"open": [10], "high": [11], "low": [9],
                                      "close": [10], "volume": [10000]}]},
        }]},
    })
    if failed:
        capture = YahooSnapshotCapture(None, "provider_unavailable")
    adapter = YahooGlobalSnapshotAdapter(
        download=lambda _: capture, clock=lambda: NOW + timedelta(seconds=1),
    )
    batch = adapter.fetch(request)
    receipt.clock[0] = NOW + timedelta(seconds=2)
    receipt.repo.start_retention(attempt.lease, captured_payload_hash=batch.raw_data_hash)
    captured = SimpleNamespace(provider_id=adapter.provider_id, capabilities=adapter.capabilities,
                               fetch=lambda _: batch)
    ProviderNeutralIngestionService(
        receipt.store, artifact_store=FileSystemArtifactStore(receipt.root),
        clock=lambda: receipt.clock[0],
    ).ingest(captured, request, refresh_lease=attempt.lease)
    return job


def _inspect(receipt, job, **kwargs):
    return inspection.inspect_refresh_reconciliation(
        receipt.store.path, receipt.root, job_id=job.job_id,
        inspected_as_of=kwargs.pop("inspected_as_of", CUTOFF), **kwargs,
    )


@pytest.mark.parametrize("market", ["us", "hong_kong", "malaysia"])
def test_exact_global_receipt_read_only_and_deterministic(receipt, market):
    job = _retained(receipt, market)
    before = sha256(receipt.store.path.read_bytes()).hexdigest()
    report = _inspect(receipt, job)
    assert report["status"] == "LINKED_BYTES_MATCH"
    assert report["artifact_audit"]["registry_scope"] == "caller_selected_rows_only"
    assert report == _inspect(receipt, job)
    assert report == _inspect(receipt, job, inspected_as_of=CUTOFF.astimezone(
        timezone(timedelta(hours=8))))
    assert report["report_hash"] != _inspect(
        receipt, job, inspected_as_of=CUTOFF + timedelta(seconds=1))["report_hash"]
    assert sha256(receipt.store.path.read_bytes()).hexdigest() == before
    assert all(report[key] is False for key in (
        "checkpoint_advanced", "collection_complete", "research_refresh_authorized",
        "validation_authorized", "execution_authorized",
    ))


def test_failure_bytes_are_never_success(receipt):
    job = _retained(receipt, failed=True)
    assert _inspect(receipt, job)["status"] == "LINKED_FAILURE_BYTES_MATCH"


def test_schema_ledger_and_receipt_share_exactly_one_read_only_connection(receipt, monkeypatch):
    job = _retained(receipt)
    original = SQLiteStore._new_connection
    connections = []

    def observed(store):
        connections.append(store.read_only)
        return original(store)

    monkeypatch.setattr(SQLiteStore, "_new_connection", observed)
    assert _inspect(receipt, job)["status"] == "LINKED_BYTES_MATCH"
    assert connections == [True]


def test_missing_job_and_no_attempt_do_not_guess_by_symbol(receipt):
    job = _job(receipt)
    assert _inspect(receipt, job)["status"] == "NO_ATTEMPT"
    assert inspection.inspect_refresh_reconciliation(
        receipt.store.path, receipt.root, job_id="f" * 64, inspected_as_of=CUTOFF,
    )["status"] == "JOB_MISSING"


def test_active_expired_and_failed_attempts_are_visible_without_mutation(receipt):
    job = _job(receipt)
    attempt = receipt.repo.claim(job.job_id, worker_id="inspector-test", expected_version=0)
    assert _inspect(receipt, job, inspected_as_of=NOW)["status"] == "IN_PROGRESS"
    assert _inspect(receipt, job)["status"] == "RECOVERY_REQUIRED"
    assert receipt.repo.attempts(job.job_id)[0] == attempt
    receipt.clock[0] += timedelta(seconds=61)
    receipt.repo.recover_expired(job.job_id)
    assert _inspect(receipt, job)["status"] == "NO_LINKED_BATCH"


def test_other_healthy_batch_and_files_cannot_supply_an_unlinked_job(receipt):
    retained = _retained(receipt)
    other = receipt.repo.register(
        receipt.plan, scope_hash=retained.scope_hash, trigger_reference="different-observation",
    )
    assert _inspect(receipt, other)["status"] == "NO_ATTEMPT"
    receipt.repo.claim(other.job_id, worker_id="other-worker", expected_version=0)
    assert _inspect(receipt, other)["status"] == "RECOVERY_REQUIRED"


def test_missing_exact_batch_is_not_reconstructed_from_its_remaining_files(receipt):
    job = _retained(receipt)
    with sqlite3.connect(receipt.store.path) as conn:
        conn.execute("DELETE FROM ingestion_batches")
    assert _inspect(receipt, job)["status"] == "UNREADABLE_OR_INCONSISTENT"


def test_record_budget_does_not_hide_extra_rows(receipt):
    job = _retained(receipt)
    with sqlite3.connect(receipt.store.path) as conn:
        columns = [row[1] for row in conn.execute("PRAGMA table_info(provider_evidence_records)")]
        values = ["'" + "f" * 64 + "'" if key == "evidence_id" else key for key in columns]
        conn.execute("INSERT INTO provider_evidence_records SELECT " + ",".join(values)
                     + " FROM provider_evidence_records LIMIT 1")
    assert _inspect(receipt, job, max_records=1)["status"] == "LIMIT_EXCEEDED"


def test_database_symlink_is_not_followed(receipt):
    job = _retained(receipt)
    alias = receipt.store.path.parent / "database-link.sqlite3"
    alias.symlink_to(receipt.store.path)
    assert inspection.inspect_refresh_reconciliation(
        alias, receipt.root, job_id=job.job_id, inspected_as_of=CUTOFF,
    )["status"] == "UNREADABLE_OR_INCONSISTENT"


@pytest.mark.parametrize("damage", ["missing", "content", "symlink", "directory"])
def test_bad_original_cannot_pass(receipt, damage):
    job = _retained(receipt)
    original = next(receipt.root.rglob("*.bin"))
    if damage == "content":
        original.write_bytes(b"x" * original.stat().st_size)
    else:
        content = original.read_bytes()
        original.unlink()
        if damage == "symlink":
            destination = receipt.root / "unrelated"
            destination.write_bytes(content)
            original.symlink_to(destination)
        elif damage == "directory":
            original.mkdir()
    assert _inspect(receipt, job)["status"] == "ORIGINAL_UNVERIFIABLE"


@pytest.mark.parametrize("statement", [
    "UPDATE provider_evidence_records SET raw_data_hash = 'f' || substr(raw_data_hash, 2)",
    "UPDATE provider_evidence_records SET subject = 'OTHER'",
    "UPDATE provider_evidence_records SET available_at = '2100-01-01T00:00:00+00:00'",
    "UPDATE provider_evidence_records SET payload_json = '{}'",
    "UPDATE provider_evidence_records SET trust_level = 'VERIFIED'",
    "UPDATE provider_evidence_records SET source_reference = 'secret-sentinel-do-not-render'",
    "UPDATE raw_dataset_fingerprints SET parameters_json = '{}'",
    "UPDATE provider_artifacts SET source_identity = 'wrong-source'",
    "UPDATE provider_artifacts SET content_hash = 'f' || substr(content_hash, 2)",
    "UPDATE provider_artifacts SET model_version = 'old'",
    "UPDATE provider_artifacts SET first_retrieved_at = '2100-01-01T00:00:00+00:00'",
    "DELETE FROM provider_artifacts",
])
def test_metadata_mismatch_future_and_secret_content_fail_closed(receipt, statement):
    job = _retained(receipt)
    with sqlite3.connect(receipt.store.path) as conn:
        conn.execute(statement)
    report = _inspect(receipt, job)
    assert report["status"] == "UNREADABLE_OR_INCONSISTENT"
    assert "secret-sentinel" not in json.dumps(report)


def test_earlier_artifact_registry_owner_is_not_an_implicit_batch_requirement(receipt):
    job = _retained(receipt)
    # The explicit evidence reference is authoritative for selection, not registry ownership.
    with sqlite3.connect(receipt.store.path) as conn:
        conn.execute("""INSERT INTO ingestion_batches SELECT
            'earlier-registry-owner', provider, dataset, started_at, completed_at,
            status, parameters_json, raw_response_hash, failure_reason, retry_of, ingested_at
            FROM ingestion_batches LIMIT 1""")
        conn.execute("UPDATE provider_artifacts SET first_batch_id = 'earlier-registry-owner'")
    assert _inspect(receipt, job)["status"] == "LINKED_BYTES_MATCH"


def test_missing_first_registry_owner_stays_visible_as_a_broken_reference(receipt):
    job = _retained(receipt)
    with sqlite3.connect(receipt.store.path) as conn:
        conn.execute("UPDATE provider_artifacts SET first_batch_id = 'missing-owner'")
    assert _inspect(receipt, job)["status"] == "UNREADABLE_OR_INCONSISTENT"


def test_one_sql_snapshot_even_if_writer_changes_evidence_during_file_audit(receipt, monkeypatch):
    job = _retained(receipt)
    with sqlite3.connect(receipt.store.path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
    original = inspection.audit_provider_artifact_selection

    def concurrent(*args, **kwargs):
        with sqlite3.connect(receipt.store.path) as conn:
            conn.execute("UPDATE provider_evidence_records SET subject = 'CHANGED'")
        return original(*args, **kwargs)

    monkeypatch.setattr(inspection, "audit_provider_artifact_selection", concurrent)
    assert _inspect(receipt, job)["status"] == "LINKED_BYTES_MATCH"
    assert _inspect(receipt, job)["status"] == "UNREADABLE_OR_INCONSISTENT"


def test_limits_and_missing_database_never_bootstrap(receipt, tmp_path):
    job = _retained(receipt)
    assert _inspect(receipt, job, max_file_bytes=1)["status"] == "ORIGINAL_UNVERIFIABLE"
    assert _inspect(receipt, job, max_total_bytes=1)["status"] == "ORIGINAL_UNVERIFIABLE"
    missing = tmp_path / "not-created.sqlite3"
    assert inspection.inspect_refresh_reconciliation(
        missing, receipt.root, job_id=job.job_id, inspected_as_of=CUTOFF,
    )["status"] == "UNREADABLE_OR_INCONSISTENT"
    assert not missing.exists()
    with pytest.raises(ValueError):
        _inspect(receipt, job, inspected_as_of=datetime(2026, 11, 3))
    with pytest.raises(ValueError):
        _inspect(receipt, job, max_records=True)


def test_physical_schema_drift_is_not_silently_accepted(receipt):
    job = _retained(receipt)
    with sqlite3.connect(receipt.store.path) as conn:
        conn.execute("CREATE TABLE unexpected_drift (value TEXT)")
    assert _inspect(receipt, job)["status"] == "UNREADABLE_OR_INCONSISTENT"


def test_tampered_migration_checksum_is_not_accepted(receipt):
    job = _retained(receipt)
    with sqlite3.connect(receipt.store.path) as conn:
        conn.execute("UPDATE schema_migrations SET checksum = 'changed'")
    assert _inspect(receipt, job)["status"] == "UNREADABLE_OR_INCONSISTENT"


def test_large_metadata_is_bounded_before_parsing_and_never_rendered(receipt):
    job = _retained(receipt)
    with sqlite3.connect(receipt.store.path) as conn:
        conn.execute("UPDATE provider_evidence_records SET payload_json = ?", ("x" * 2_100_000,))
    assert _inspect(receipt, job)["status"] == "LIMIT_EXCEEDED"


def test_native_fundamental_failure_snapshot_remains_a_failure(receipt):
    from tong_quant.data.providers.yahoo_fundamentals import (
        YahooFundamentalCapture,
        YahooFundamentalSnapshotAdapter,
    )

    entry = next(item for item in receipt.plan["entries"]
                 if item["scope"]["dataset"] == "global_native_fundamental_snapshot")
    job = receipt.repo.register(
        receipt.plan, scope_hash=entry["scope_hash"], trigger_reference="native-test",
    )
    attempt = receipt.repo.claim(job.job_id, worker_id="native-test", expected_version=0)
    request = ProviderDatasetRequest(
        entry["scope"]["dataset"], Market.MALAYSIA, entry["scope"]["subject"],
        NOW + timedelta(seconds=2), entry["request_parameters"],
    )
    adapter = YahooFundamentalSnapshotAdapter(
        download=lambda _: YahooFundamentalCapture(None, "http_401"),
        clock=lambda: NOW + timedelta(seconds=1),
    )
    batch = adapter.fetch(request)
    receipt.clock[0] += timedelta(seconds=2)
    receipt.repo.start_retention(attempt.lease, captured_payload_hash=batch.raw_data_hash)
    captured = SimpleNamespace(provider_id=adapter.provider_id, capabilities=adapter.capabilities,
                               fetch=lambda _: batch)
    ProviderNeutralIngestionService(
        receipt.store, artifact_store=FileSystemArtifactStore(receipt.root),
        clock=lambda: receipt.clock[0],
    ).ingest(captured, request, refresh_lease=attempt.lease)
    report = _inspect(receipt, job)
    assert report["status"] == "LINKED_FAILURE_BYTES_MATCH"
    assert report["failure_code"] == "permission_denied"


def test_akshare_exact_frame_and_observation_links(receipt):
    import pandas as pd

    from tong_quant.data.models import DailyBarRequest, RawDataset, dataframe_sha256
    from tong_quant.data.normalization import normalize_daily_bars
    from tong_quant.data.providers.akshare_prices import AkShareDailyBarEvidenceAdapter
    from tong_quant.data.storage.refresh import refresh_batch_parameters
    from tong_quant.domain.models import Instrument

    entry = next(item for item in receipt.plan["entries"]
                 if item["scope"]["market"] == "china_a")
    job = receipt.repo.register(
        receipt.plan, scope_hash=entry["scope_hash"], trigger_reference="china-test",
    )
    attempt = receipt.repo.claim(job.job_id, worker_id="china-test", expected_version=0)
    params = refresh_batch_parameters(entry)
    query = DailyBarRequest(params["symbol"], params["start_date"], params["end_date"])
    frame = pd.DataFrame({
        "日期": ["2026-11-02"], "股票代码": [query.symbol], "开盘": [10.0], "收盘": [10.5],
        "最高": [11.0], "最低": [9.0], "成交量": [1000], "成交额": [None],
    })
    raw = RawDataset("a_share_daily", frame, NOW + timedelta(seconds=1),
                     "akshare:stock_zh_a_hist", params, dataframe_sha256(frame, params))
    bars = normalize_daily_bars(raw, query, Instrument(query.symbol, Market.CHINA_A, "synthetic"))
    adapter = AkShareDailyBarEvidenceAdapter(raw, query, tuple(bars))
    request = ProviderDatasetRequest("a_share_daily", Market.CHINA_A, query.symbol,
                                     NOW + timedelta(seconds=2), {})
    batch = adapter.fetch(request)
    receipt.clock[0] += timedelta(seconds=2)
    receipt.repo.start_retention(attempt.lease, captured_payload_hash=batch.raw_data_hash)
    ProviderNeutralIngestionService(
        receipt.store, artifact_store=FileSystemArtifactStore(receipt.root),
        clock=lambda: receipt.clock[0],
    ).ingest(adapter, request, refresh_lease=attempt.lease)
    report = _inspect(receipt, job)
    assert report["status"] == "LINKED_BYTES_MATCH"
    assert report["observation_count"] == 1
    # Identical AKShare bytes can be observed again: first registry time is NOT
    # this observation's time, nor proof that the newest attempt owns the file.
    second = receipt.repo.register(
        receipt.plan, scope_hash=entry["scope_hash"], trigger_reference="china-second-observation",
    )
    second_attempt = receipt.repo.claim(second.job_id, worker_id="china-test", expected_version=0)
    second_raw = replace(raw, retrieved_at=NOW + timedelta(seconds=3))
    second_bars = normalize_daily_bars(
        second_raw, query, Instrument(query.symbol, Market.CHINA_A, "synthetic"),
    )
    second_adapter = AkShareDailyBarEvidenceAdapter(second_raw, query, tuple(second_bars))
    second_request = replace(request, as_of=NOW + timedelta(seconds=4))
    second_batch = second_adapter.fetch(second_request)
    assert second_batch.raw_data_hash == batch.raw_data_hash
    receipt.clock[0] += timedelta(seconds=2)
    receipt.repo.start_retention(
        second_attempt.lease, captured_payload_hash=second_batch.raw_data_hash,
    )
    ProviderNeutralIngestionService(
        receipt.store, artifact_store=FileSystemArtifactStore(receipt.root),
        clock=lambda: receipt.clock[0],
    ).ingest(second_adapter, second_request, refresh_lease=second_attempt.lease)
    assert receipt.store.table_count("provider_artifacts") == 1
    assert _inspect(receipt, second)["status"] == "LINKED_BYTES_MATCH"
    with sqlite3.connect(receipt.store.path) as conn:
        conn.execute("UPDATE provider_artifact_observations SET source_identity = 'changed'")
    assert _inspect(receipt, job)["status"] == "UNREADABLE_OR_INCONSISTENT"


def test_cli_reports_only_diagnostics_and_rejects_capture_flags_safely(receipt):
    job = _retained(receipt)
    command = [sys.executable, str(ROOT / "scripts/inspect_refresh_reconciliation.py"),
               "--database", str(receipt.store.path), "--artifact-root", str(receipt.root),
               "--job-id", job.job_id, "--as-of", CUTOFF.isoformat()]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "LINKED_BYTES_MATCH"
    assert str(receipt.root) not in result.stdout
    invalid = subprocess.run(command + ["--capture", "secret-sentinel"],
                             capture_output=True, text=True, check=False)
    assert invalid.returncode == 2
    assert "secret-sentinel" not in invalid.stderr
