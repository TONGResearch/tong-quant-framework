import sqlite3
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tong_quant.data.baselines import (
    ProviderBaselineBuilder,
    ProviderBaselineQuery,
    ProviderBaselineScope,
)
from tong_quant.data.evidence_bundle import (
    ProviderEvidenceBundleExporter,
    provider_evidence_bundle_json,
    render_provider_evidence_bundle_markdown,
    verify_provider_evidence_document,
)
from tong_quant.data.providers.contracts import (
    ProviderContractCheck,
    ProviderContractRun,
    ProviderContractStatus,
)
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market

START = datetime(2026, 5, 1, tzinfo=UTC)
END = START + timedelta(days=90)


def test_bundle_is_deterministic_reconstructable_and_excludes_storage_paths(
    tmp_path: Path,
) -> None:
    database = tmp_path / "provider.sqlite3"
    store = SQLiteStore(database)
    store.initialize()
    _save_contract_run(store, "run-one", "check-one", START)
    _save_contract_run(store, "run-two", "check-two", END)
    ProviderBaselineBuilder(repository=store, clock=lambda: END).build(
        ProviderBaselineQuery(
            period_start=START,
            period_end=END,
            expected_interval_days=7,
            scopes=(_scope(),),
        )
    )
    exporter = ProviderEvidenceBundleExporter()

    first = exporter.export(database, as_of=END)
    second = exporter.export(database, as_of=END)
    document = provider_evidence_bundle_json(first)
    verify_provider_evidence_document(document)

    assert first.bundle_id == second.bundle_id
    assert first.missing_tables == ()
    assert {item.table for item in first.tables} >= {
        "provider_evidence_records",
        "historical_coverage_assessments",
        "pit_readiness_assessments",
    }
    summary = first.dataset_summaries[0]
    assert summary.dataset == "global_daily_bars"
    assert summary.contract_check_count == 2
    assert summary.observation_days == 90
    assert summary.baseline_count == 1
    scope_summary = first.scope_summaries[0]
    assert scope_summary.identity == (
        "yahoo_finance",
        "global_daily_bars",
        "us",
        "MSFT",
    )
    assert scope_summary.contract_check_count == 2
    assert scope_summary.observation_days == 90
    artifact_table = next(
        item for item in first.tables if item.table == "provider_artifacts"
    )
    assert "storage_key" not in artifact_table.columns
    markdown = render_provider_evidence_bundle_markdown(first)
    assert first.bundle_id in markdown
    assert markdown.endswith("\n") and not markdown.endswith("\n\n")


def test_bundle_as_of_excludes_future_contract_observations(tmp_path: Path) -> None:
    database = tmp_path / "future.sqlite3"
    store = SQLiteStore(database)
    store.initialize()
    _save_contract_run(store, "run-now", "check-now", START)
    _save_contract_run(store, "run-future", "check-future", END)

    bundle = ProviderEvidenceBundleExporter().export(database, as_of=START)

    summary = bundle.dataset_summaries[0]
    assert summary.contract_check_count == 1
    assert summary.first_observed_at == START.isoformat()
    assert summary.last_observed_at == START.isoformat()


def test_bundle_as_of_excludes_batches_completed_after_boundary(
    tmp_path: Path,
) -> None:
    database = tmp_path / "batches.sqlite3"
    store = SQLiteStore(database)
    store.initialize()
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            INSERT INTO ingestion_batches (
                batch_id, provider, dataset, started_at, completed_at, status,
                parameters_json, raw_response_hash, failure_reason, retry_of,
                ingested_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "future-completion",
                "provider",
                "daily_bars",
                START.isoformat(),
                END.isoformat(),
                "completed",
                "{}",
                "a" * 64,
                "",
                None,
                END.isoformat(),
            ),
        )

    bundle = ProviderEvidenceBundleExporter().export(database, as_of=START)
    batches = next(item for item in bundle.tables if item.table == "ingestion_batches")

    assert batches.row_count == 0


def test_bundle_tampering_fails_hash_verification(tmp_path: Path) -> None:
    database = tmp_path / "tamper.sqlite3"
    store = SQLiteStore(database)
    store.initialize()
    _save_contract_run(store, "run-one", "check-one", START)
    document = provider_evidence_bundle_json(
        ProviderEvidenceBundleExporter().export(database, as_of=END)
    )
    document["framework_version"] = "tampered"

    with pytest.raises(ValueError, match="hash does not match"):
        verify_provider_evidence_document(document)


def test_bundle_rejects_credential_assignments_at_export_boundary(
    tmp_path: Path,
) -> None:
    database = tmp_path / "secret.sqlite3"
    store = SQLiteStore(database)
    store.initialize()
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            INSERT INTO provider_limitations (
                limitation_id, provider, dataset, limitation_code,
                description, trust_level, documented_at, ingested_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "limitation-secret",
                "provider",
                "daily_bars",
                "unsafe",
                "token=do-not-export",
                "unknown",
                START.isoformat(),
                START.isoformat(),
            ),
        )

    with pytest.raises(ValueError, match="credential-like"):
        ProviderEvidenceBundleExporter().export(database, as_of=END)


def test_bundle_rejects_local_paths_at_export_boundary(tmp_path: Path) -> None:
    database = tmp_path / "path.sqlite3"
    store = SQLiteStore(database)
    store.initialize()
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            INSERT INTO provider_limitations (
                limitation_id, provider, dataset, limitation_code,
                description, trust_level, documented_at, ingested_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "limitation-path",
                "provider",
                "daily_bars",
                "unsafe_path",
                "/Users/example/private-artifact.pdf",
                "unknown",
                START.isoformat(),
                START.isoformat(),
            ),
        )

    with pytest.raises(ValueError, match="local filesystem path"):
        ProviderEvidenceBundleExporter().export(database, as_of=END)


def test_missing_tables_remain_visible(tmp_path: Path) -> None:
    database = tmp_path / "partial.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            CREATE TABLE provider_contract_checks (
                check_id TEXT PRIMARY KEY,
                dataset TEXT NOT NULL,
                provider TEXT NOT NULL,
                market TEXT NOT NULL,
                subject TEXT NOT NULL,
                checked_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "INSERT INTO provider_contract_checks VALUES (?, ?, ?, ?, ?, ?)",
            (
                "check-one",
                "daily_bars",
                "provider",
                "us",
                "MSFT",
                START.isoformat(),
            ),
        )

    bundle = ProviderEvidenceBundleExporter().export(database, as_of=END)

    assert "provider_baseline_manifests" in bundle.missing_tables
    assert bundle.dataset_summaries[0].contract_check_count == 1
    assert any("Missing operational evidence table" in item for item in bundle.limitations)


def test_export_script_writes_and_verifies_content_addressed_bundle(
    tmp_path: Path,
) -> None:
    database = tmp_path / "script.sqlite3"
    SQLiteStore(database).initialize()
    output = tmp_path / "output"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/export_provider_evidence.py",
            "--database",
            str(database),
            "--as-of",
            END.isoformat(),
            "--output-dir",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    json_path = next(output.glob("*.json"))
    markdown_path = next(output.glob("*.md"))
    assert not markdown_path.read_text(encoding="utf-8").endswith("\n\n")
    verify = subprocess.run(
        [
            sys.executable,
            "scripts/export_provider_evidence.py",
            "--verify",
            str(json_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert verify.returncode == 0, verify.stderr


def _scope() -> ProviderBaselineScope:
    return ProviderBaselineScope(
        provider="yahoo_finance",
        dataset="daily_bars",
        market=Market.US,
        subject="MSFT",
    )


def _save_contract_run(
    store: SQLiteStore,
    run_id: str,
    check_id: str,
    checked_at: datetime,
) -> None:
    check = ProviderContractCheck(
        check_id=check_id,
        run_id=run_id,
        provider="yahoo_finance",
        dataset="daily_bars",
        market=Market.US,
        subject="MSFT",
        request_as_of=checked_at,
        status=ProviderContractStatus.HEALTHY,
        records_observed=10,
        trust_level=DataTrustLevel.LOW,
        availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
        latency_ms=10,
        required_fields=("close", "volume"),
        missing_fields=(),
        limitations=("research-grade evidence",),
        error_code="",
        checked_at=checked_at,
    )
    store.save_provider_contract_run(
        ProviderContractRun(
            run_id=run_id,
            started_at=checked_at,
            completed_at=checked_at,
            status=ProviderContractStatus.HEALTHY,
            checks=(check,),
            implementation_version="provider-contract-monitor-test",
        )
    )
