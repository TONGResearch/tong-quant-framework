import hashlib
import json
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tong_quant.core.exceptions import DatabaseIntegrityError
from tong_quant.data.storage import engineering
from tong_quant.data.storage.engineering import (
    DatabaseAuditStatus,
    SQLiteBackupService,
    SQLiteIntegrityService,
    database_integrity_json,
)
from tong_quant.data.storage.migrations import (
    CNINFO_ARTIFACT_CAPTURE,
    MIGRATION_HEAD,
    PROVIDER_CALIBRATION_ATTEMPTS,
    PROVIDER_CONTRACT_RUN_ORIGIN,
    SCHEMA_DEFINITION_HASHES,
    schema_fingerprint,
)
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import AssetType, Market
from tong_quant.domain.models import Instrument

NOW = datetime(2026, 8, 21, 12, tzinfo=UTC)
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _database(path: Path) -> SQLiteStore:
    store = SQLiteStore(path)
    store.initialize()
    store.upsert_instruments(
        (
            Instrument(
                symbol="600000",
                market=Market.CHINA_A,
                name="Synthetic Equity",
                asset_type=AssetType.EQUITY,
                available_at=NOW,
                source="test",
            ),
        )
    )
    return store


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_read_only_audit_validates_schema_migrations_and_rows(tmp_path: Path) -> None:
    path = tmp_path / "source.sqlite3"
    _database(path)
    before = _sha256(path)
    service = SQLiteIntegrityService(clock=lambda: NOW)

    first = service.audit(path)
    service.clock = lambda: NOW + timedelta(days=1)
    second = service.audit(path)

    assert first.status is DatabaseAuditStatus.PASSED
    assert first.migration_head == MIGRATION_HEAD
    assert first.schema_fingerprint_valid is True
    assert first.schema_definition_valid is True
    assert first.migration_checksums_valid is True
    assert first.foreign_key_violations == ()
    assert dict((item.table, item.rows) for item in first.table_counts)[
        "instruments"
    ] == 1
    assert first.audit_hash == second.audit_hash
    assert first.checked_at != second.checked_at
    assert _sha256(path) == before


def test_backup_and_dry_run_restore_preserve_database_state(tmp_path: Path) -> None:
    source = tmp_path / "source.sqlite3"
    backup = tmp_path / "backups" / "source-20260821.sqlite3"
    restored = tmp_path / "restore-drill" / "source.sqlite3"
    _database(source)
    integrity = SQLiteIntegrityService(clock=lambda: NOW)
    service = SQLiteBackupService(
        integrity_service=integrity,
        clock=lambda: NOW,
        pages_per_step=1,
    )

    manifest = service.create_backup(
        source_path=source,
        destination_path=backup,
    )
    restore = service.dry_run_restore(
        backup_path=backup,
        destination_path=restored,
    )

    assert manifest.table_counts_match is True
    assert manifest.source_audit_hash == manifest.backup_audit_hash
    assert manifest.migration_head == MIGRATION_HEAD
    assert manifest.backup_sha256 == _sha256(backup)
    assert backup.stat().st_mode & 0o777 == 0o600
    assert restore.common_table_counts_match is True
    assert restore.source_migration_head == MIGRATION_HEAD
    assert restore.restored_migration_head == MIGRATION_HEAD
    assert restore.migration_applied is False
    assert manifest.source_content_hash == manifest.backup_content_hash
    assert restore.same_schema_content_verified is True
    assert restore.source_content_hash == restore.restored_content_hash
    assert restore.restored_sha256 == _sha256(restored)
    assert restored.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize(
    ("previous_head", "schema_version"),
    (
        (PROVIDER_CONTRACT_RUN_ORIGIN.migration_id, "0.8.1"),
        (PROVIDER_CALIBRATION_ATTEMPTS.migration_id, "0.8.0"),
        (CNINFO_ARTIFACT_CAPTURE.migration_id, "0.8.0"),
    ),
)
def test_restore_migrates_a_supported_fingerprinted_backup(
    tmp_path: Path, previous_head: str, schema_version: str
) -> None:
    source = tmp_path / "source.sqlite3"
    restored = tmp_path / "restored.sqlite3"
    _database(source)
    with sqlite3.connect(source) as connection:
        connection.execute(
            """
            INSERT INTO provider_contract_runs (
                run_id, started_at, completed_at, status,
                implementation_version, generated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("legacy-run", NOW.isoformat(), NOW.isoformat(), "healthy", "v1", NOW.isoformat()),
        )
        connection.execute("DROP TRIGGER refresh_batch_immutable")
        connection.execute("DROP TABLE refresh_attempts")
        connection.execute("DROP TABLE refresh_jobs")
        connection.execute("DROP TABLE portfolio_evidence_references")
        connection.execute("DELETE FROM schema_migrations WHERE migration_id > ?", (previous_head,))
        if previous_head != PROVIDER_CONTRACT_RUN_ORIGIN.migration_id:
            connection.execute(
                "ALTER TABLE provider_contract_runs DROP COLUMN origin_reference"
            )
            connection.execute("ALTER TABLE provider_contract_runs DROP COLUMN run_origin")
        if previous_head == CNINFO_ARTIFACT_CAPTURE.migration_id:
            connection.execute("DROP TABLE provider_calibration_attempts")
        fingerprint = schema_fingerprint(connection)
        connection.execute(
            "DELETE FROM schema_migrations WHERE migration_id = ?",
            (MIGRATION_HEAD,),
        )
        if previous_head != PROVIDER_CONTRACT_RUN_ORIGIN.migration_id:
            connection.execute(
                "DELETE FROM schema_migrations WHERE migration_id = ?",
                (PROVIDER_CONTRACT_RUN_ORIGIN.migration_id,),
            )
        if previous_head == CNINFO_ARTIFACT_CAPTURE.migration_id:
            connection.execute(
                "DELETE FROM schema_migrations WHERE migration_id = ?",
                (PROVIDER_CALIBRATION_ATTEMPTS.migration_id,),
            )
        connection.execute("DELETE FROM schema_fingerprints")
        connection.execute(
            """
            INSERT INTO schema_fingerprints (
                migration_head, schema_fingerprint,
                schema_definition_hash, recorded_at
            ) VALUES (?, ?, ?, ?)
            """,
            (
                previous_head,
                fingerprint,
                SCHEMA_DEFINITION_HASHES[previous_head],
                NOW.isoformat(),
            ),
        )
        connection.execute(
            "UPDATE schema_metadata SET value = ? WHERE key = 'migration_head'",
            (previous_head,),
        )
        connection.execute(
            "UPDATE schema_metadata SET value = ? WHERE key = 'schema_version'",
            (schema_version,),
        )
        connection.execute(
            "UPDATE schema_metadata SET value = ? WHERE key = 'schema_fingerprint'",
            (fingerprint,),
        )
    integrity = SQLiteIntegrityService(clock=lambda: NOW)
    before = integrity.audit(source)

    report = SQLiteBackupService(
        integrity_service=integrity,
        clock=lambda: NOW,
    ).dry_run_restore(backup_path=source, destination_path=restored)

    assert before.passed is False
    assert before.requires_migration is True
    assert before.schema_fingerprint_valid is True
    assert before.schema_definition_valid is True
    assert before.schema_version == schema_version
    assert report.source_migration_head == previous_head
    assert report.restored_migration_head == MIGRATION_HEAD
    assert report.migration_applied is True
    assert report.same_schema_content_verified is False
    assert report.common_table_counts_match is True
    assert integrity.audit(restored).passed is True
    with sqlite3.connect(restored) as connection:
        if previous_head != PROVIDER_CONTRACT_RUN_ORIGIN.migration_id:
            assert connection.execute(
                "SELECT run_origin, origin_reference FROM provider_contract_runs WHERE run_id = ?",
                ("legacy-run",),
            ).fetchone() == ("unknown", None)
        assert connection.execute(
            "SELECT COUNT(*) FROM portfolio_evidence_references"
        ).fetchone() == (0,)


def test_backup_never_overwrites_existing_destination(tmp_path: Path) -> None:
    source = tmp_path / "source.sqlite3"
    destination = tmp_path / "existing.sqlite3"
    _database(source)
    destination.write_bytes(b"keep-me")
    before = destination.read_bytes()
    service = SQLiteBackupService(SQLiteIntegrityService(clock=lambda: NOW))

    with pytest.raises(DatabaseIntegrityError, match="overwrite is disabled"):
        service.create_backup(source_path=source, destination_path=destination)

    assert destination.read_bytes() == before


def test_current_schema_restore_does_not_reinitialize_or_rewrite_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source.sqlite3"
    restored = tmp_path / "restored.sqlite3"
    _database(source)
    before = engineering._logical_dump_hash(source)

    def forbidden_initialize(self: SQLiteStore) -> None:
        raise AssertionError("current-schema restore must not reinitialize metadata")

    monkeypatch.setattr(SQLiteStore, "initialize", forbidden_initialize)
    report = SQLiteBackupService(SQLiteIntegrityService()).dry_run_restore(
        backup_path=source, destination_path=restored,
    )
    assert report.same_schema_content_verified is True
    assert engineering._logical_dump_hash(restored) == before
    assert engineering._logical_dump_hash(source) == before


@pytest.mark.parametrize("operation", ["backup", "restore"])
def test_same_count_content_tampering_blocks_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str,
) -> None:
    source = tmp_path / "source.sqlite3"
    destination = tmp_path / "destination.sqlite3"
    _database(source)
    original_copy = engineering._copy_to_temporary
    before = engineering._logical_dump_hash(source)

    def changed_copy(**kwargs: object) -> Path:
        temporary = original_copy(**kwargs)
        with sqlite3.connect(temporary) as connection:
            connection.execute("UPDATE instruments SET name = 'Changed synthetic name'")
        return temporary

    monkeypatch.setattr(engineering, "_copy_to_temporary", changed_copy)
    service = SQLiteBackupService(SQLiteIntegrityService())
    with pytest.raises(DatabaseIntegrityError, match="logical content"):
        if operation == "backup":
            service.create_backup(source_path=source, destination_path=destination)
        else:
            service.dry_run_restore(backup_path=source, destination_path=destination)
    assert not destination.exists()
    assert list(tmp_path.glob(".destination.sqlite3.*.tmp")) == []
    assert engineering._logical_dump_hash(source) == before


def test_integrity_audit_closes_its_read_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source.sqlite3"
    _database(source)
    original = engineering._read_only_connection
    connections: list[sqlite3.Connection] = []

    def tracked(path: Path) -> sqlite3.Connection:
        connection = original(path)
        connections.append(connection)
        return connection

    monkeypatch.setattr(engineering, "_read_only_connection", tracked)
    assert SQLiteIntegrityService().audit(source).passed
    for connection in connections:
        with pytest.raises(sqlite3.ProgrammingError, match="closed"):
            connection.execute("SELECT 1")


def test_logical_dump_rejects_text_that_sqlite_quote_would_truncate(tmp_path: Path) -> None:
    source = tmp_path / "source.sqlite3"
    _database(source)
    with sqlite3.connect(source) as connection:
        connection.execute("UPDATE instruments SET name = ?", ("synthetic\0hidden",))
    assert SQLiteIntegrityService().audit(source).passed
    with pytest.raises(DatabaseIntegrityError, match="NUL text"):
        SQLiteBackupService(SQLiteIntegrityService()).create_backup(
            source_path=source, destination_path=tmp_path / "snapshot.sqlite3",
        )
    assert not (tmp_path / "snapshot.sqlite3").exists()


def test_backup_rejects_source_as_destination(tmp_path: Path) -> None:
    source = tmp_path / "source.sqlite3"
    _database(source)
    service = SQLiteBackupService(SQLiteIntegrityService(clock=lambda: NOW))

    with pytest.raises(DatabaseIntegrityError, match="must be different"):
        service.create_backup(source_path=source, destination_path=source)


def test_backup_rejects_symbolic_link_destination(tmp_path: Path) -> None:
    source = tmp_path / "source.sqlite3"
    destination = tmp_path / "backup-link.sqlite3"
    _database(source)
    destination.symlink_to(tmp_path / "unpublished-target.sqlite3")
    service = SQLiteBackupService(SQLiteIntegrityService(clock=lambda: NOW))

    with pytest.raises(DatabaseIntegrityError, match="symbolic link"):
        service.create_backup(source_path=source, destination_path=destination)

    assert not (tmp_path / "unpublished-target.sqlite3").exists()


def test_interrupted_backup_removes_partial_snapshot(tmp_path: Path) -> None:
    source = tmp_path / "source.sqlite3"
    destination = tmp_path / "interrupted.sqlite3"
    _database(source)

    def interrupt(_status: int, _remaining: int, _total: int) -> None:
        raise RuntimeError("simulated interruption")

    service = SQLiteBackupService(
        SQLiteIntegrityService(clock=lambda: NOW),
        progress=interrupt,
        pages_per_step=1,
    )

    with pytest.raises(RuntimeError, match="simulated interruption"):
        service.create_backup(source_path=source, destination_path=destination)

    assert not destination.exists()
    assert tuple(tmp_path.glob(".interrupted.sqlite3.*.tmp")) == ()


def test_corrupted_database_and_backup_fail_closed(tmp_path: Path) -> None:
    corrupted = tmp_path / "corrupted.sqlite3"
    corrupted.write_bytes(b"not a sqlite database")
    destination = tmp_path / "should-not-exist.sqlite3"
    integrity = SQLiteIntegrityService(clock=lambda: NOW)
    service = SQLiteBackupService(integrity)

    report = integrity.audit(corrupted)

    assert report.passed is False
    assert report.error_code == "DatabaseError"
    with pytest.raises(DatabaseIntegrityError, match="failed pre-backup audit"):
        service.create_backup(
            source_path=corrupted,
            destination_path=destination,
        )
    assert not destination.exists()


def test_migration_checksum_mismatch_blocks_backup(tmp_path: Path) -> None:
    source = tmp_path / "tampered.sqlite3"
    destination = tmp_path / "backup.sqlite3"
    _database(source)
    with sqlite3.connect(source) as connection:
        connection.execute(
            "UPDATE schema_migrations SET checksum = 'tampered' WHERE migration_id = ?",
            (MIGRATION_HEAD,),
        )
    integrity = SQLiteIntegrityService(clock=lambda: NOW)
    service = SQLiteBackupService(integrity)

    report = integrity.audit(source)

    assert report.passed is False
    assert report.migration_checksums_valid is False
    with pytest.raises(DatabaseIntegrityError, match="failed pre-backup audit"):
        service.create_backup(source_path=source, destination_path=destination)
    assert not destination.exists()


def test_corrupted_backup_blocks_restore_and_leaves_no_destination(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.sqlite3"
    backup = tmp_path / "backup.sqlite3"
    restored = tmp_path / "restored.sqlite3"
    _database(source)
    service = SQLiteBackupService(SQLiteIntegrityService(clock=lambda: NOW))
    service.create_backup(source_path=source, destination_path=backup)
    payload = bytearray(backup.read_bytes())
    payload[:16] = b"corrupted backup"
    backup.write_bytes(payload)

    with pytest.raises(DatabaseIntegrityError, match="failed pre-restore audit"):
        service.dry_run_restore(backup_path=backup, destination_path=restored)

    assert not restored.exists()


def test_read_only_audit_command_outputs_structured_report(tmp_path: Path) -> None:
    source = tmp_path / "source.sqlite3"
    _database(source)

    result = subprocess.run(
        (
            sys.executable,
            "scripts/manage_database.py",
            "audit",
            "--database",
            str(source),
        ),
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["status"] == "passed"
    assert report["migration_head"] == MIGRATION_HEAD
    assert report == database_integrity_json(
        SQLiteIntegrityService().audit(source)
    ) | {"checked_at": report["checked_at"]}


def test_backup_command_rejects_report_at_database_destination(tmp_path: Path) -> None:
    source = tmp_path / "source.sqlite3"
    destination = tmp_path / "backup.sqlite3"
    _database(source)

    result = subprocess.run(
        (
            sys.executable,
            "scripts/manage_database.py",
            "backup",
            "--database",
            str(source),
            "--destination",
            str(destination),
            "--output",
            str(destination),
        ),
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "must differ" in result.stderr
    assert not destination.exists()
