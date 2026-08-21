import json
import os
import sqlite3
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
from pathlib import Path

from tong_quant.core.exceptions import DatabaseIntegrityError
from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.storage.migrations import (
    MIGRATION_HEAD,
    MIGRATIONS,
    expected_schema_definition_hash,
    schema_fingerprint,
)
from tong_quant.data.storage.sqlite import SCHEMA, SQLiteStore
from tong_quant.version import DATABASE_ENGINEERING_VERSION, DATABASE_SCHEMA_VERSION


def _utc_now() -> datetime:
    return datetime.now(UTC)


class DatabaseAuditStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True, order=True)
class DatabaseTableCount:
    table: str
    rows: int

    def __post_init__(self) -> None:
        if not self.table.strip() or self.rows < 0:
            raise ValueError("database table counts require a table and non-negative rows")


@dataclass(frozen=True, slots=True)
class ForeignKeyViolation:
    table: str
    row_id: int | None
    parent: str
    foreign_key_id: int


@dataclass(frozen=True, slots=True)
class DatabaseIntegrityReport:
    database_path: Path
    checked_at: datetime
    status: DatabaseAuditStatus
    integrity_messages: tuple[str, ...]
    foreign_key_violations: tuple[ForeignKeyViolation, ...]
    table_counts: tuple[DatabaseTableCount, ...]
    schema_version: str
    migration_head: str
    migration_checksums_valid: bool
    migration_ledger_is_prefix: bool
    schema_fingerprint: str
    computed_schema_fingerprint: str
    schema_fingerprint_valid: bool
    schema_definition_valid: bool
    credential_columns_absent: bool
    requires_migration: bool
    warnings: tuple[str, ...]
    error_code: str
    audit_hash: str
    model_version: str = DATABASE_ENGINEERING_VERSION

    @property
    def passed(self) -> bool:
        return self.status is DatabaseAuditStatus.PASSED


@dataclass(frozen=True, slots=True)
class DatabaseBackupManifest:
    backup_id: str
    source_path: Path
    destination_path: Path
    created_at: datetime
    source_audit_hash: str
    backup_audit_hash: str
    backup_sha256: str
    backup_size_bytes: int
    migration_head: str
    schema_fingerprint: str
    table_counts_match: bool
    model_version: str = DATABASE_ENGINEERING_VERSION

    def __post_init__(self) -> None:
        if len(self.backup_id) != 64 or len(self.backup_sha256) != 64:
            raise ValueError("database backup identifiers must be SHA-256 digests")
        if self.backup_size_bytes < 1 or not self.table_counts_match:
            raise ValueError("database backup manifest requires a verified snapshot")


@dataclass(frozen=True, slots=True)
class DatabaseRestoreReport:
    restore_id: str
    backup_path: Path
    destination_path: Path
    restored_at: datetime
    source_audit_hash: str
    restored_audit_hash: str
    source_migration_head: str
    restored_migration_head: str
    migration_applied: bool
    common_table_counts_match: bool
    restored_schema_fingerprint: str
    restored_sha256: str
    model_version: str = DATABASE_ENGINEERING_VERSION

    def __post_init__(self) -> None:
        if len(self.restore_id) != 64 or len(self.restored_sha256) != 64:
            raise ValueError("database restore identifiers must be SHA-256 digests")
        if not self.common_table_counts_match:
            raise ValueError("database restore must preserve all source table counts")


BackupProgress = Callable[[int, int, int], None]


@dataclass(slots=True)
class SQLiteIntegrityService:
    clock: Callable[[], datetime] = _utc_now

    def audit(self, database_path: Path) -> DatabaseIntegrityReport:
        checked_at = self.clock()
        expanded_path = database_path.expanduser()
        path = expanded_path.resolve()
        try:
            if expanded_path.is_symlink():
                raise ValueError("database path must not be a symbolic link")
            _require_database_file(path)
            with _read_only_connection(path) as connection:
                integrity_messages = tuple(
                    str(row[0])
                    for row in connection.execute("PRAGMA integrity_check").fetchall()
                )
                foreign_key_violations = tuple(
                    ForeignKeyViolation(
                        table=str(row[0]),
                        row_id=None if row[1] is None else int(row[1]),
                        parent=str(row[2]),
                        foreign_key_id=int(row[3]),
                    )
                    for row in connection.execute("PRAGMA foreign_key_check").fetchall()
                )
                table_counts = _table_counts(connection)
                credential_columns_absent = _credential_columns_absent(connection)
                metadata = _schema_metadata(connection)
                migration_head = metadata.get("migration_head", "")
                schema_version = metadata.get("schema_version", "")
                stored_fingerprint = metadata.get("schema_fingerprint", "")
                (
                    migration_checksums_valid,
                    migration_ledger_is_prefix,
                ) = _migration_ledger_state(connection, migration_head)
                computed_fingerprint = schema_fingerprint(connection)
                fingerprint_valid, definition_valid = _fingerprint_state(
                    connection,
                    migration_head=migration_head,
                    stored_fingerprint=stored_fingerprint,
                    computed_fingerprint=computed_fingerprint,
                )
            warnings = _audit_warnings(
                schema_version=schema_version,
                migration_head=migration_head,
                credential_columns_absent=credential_columns_absent,
            )
            passed = all(
                (
                    integrity_messages == ("ok",),
                    not foreign_key_violations,
                    migration_checksums_valid,
                    migration_ledger_is_prefix,
                    fingerprint_valid,
                    definition_valid,
                    credential_columns_absent,
                    schema_version == DATABASE_SCHEMA_VERSION,
                    migration_head == MIGRATION_HEAD,
                )
            )
            error_code = "" if passed else "database_integrity_check_failed"
            return _integrity_report(
                database_path=path,
                checked_at=checked_at,
                passed=passed,
                integrity_messages=integrity_messages,
                foreign_key_violations=foreign_key_violations,
                table_counts=table_counts,
                schema_version=schema_version,
                migration_head=migration_head,
                migration_checksums_valid=migration_checksums_valid,
                migration_ledger_is_prefix=migration_ledger_is_prefix,
                schema_fingerprint=stored_fingerprint,
                computed_schema_fingerprint=computed_fingerprint,
                schema_fingerprint_valid=fingerprint_valid,
                schema_definition_valid=definition_valid,
                credential_columns_absent=credential_columns_absent,
                warnings=warnings,
                error_code=error_code,
            )
        except (OSError, sqlite3.DatabaseError, ValueError) as error:
            return _integrity_report(
                database_path=path,
                checked_at=checked_at,
                passed=False,
                error_code=type(error).__name__,
            )


@dataclass(slots=True)
class SQLiteBackupService:
    integrity_service: SQLiteIntegrityService
    clock: Callable[[], datetime] = _utc_now
    progress: BackupProgress | None = None
    pages_per_step: int = 128

    def __post_init__(self) -> None:
        if self.pages_per_step < 1:
            raise ValueError("SQLite backup pages_per_step must be positive")

    def create_backup(
        self,
        *,
        source_path: Path,
        destination_path: Path,
    ) -> DatabaseBackupManifest:
        source, destination = _safe_operation_paths(source_path, destination_path)
        _require_distinct_new_destination(source, destination)
        source_report = self.integrity_service.audit(source)
        _require_passed(source_report, "source database failed pre-backup audit")

        temporary = _copy_to_temporary(
            source=source,
            destination=destination,
            pages_per_step=self.pages_per_step,
            progress=self.progress,
        )
        try:
            backup_report = self.integrity_service.audit(temporary)
            _require_passed(backup_report, "backup snapshot failed post-copy audit")
            table_counts_match = source_report.table_counts == backup_report.table_counts
            if not all(
                (
                    table_counts_match,
                    source_report.audit_hash == backup_report.audit_hash,
                    source_report.migration_head == backup_report.migration_head,
                    source_report.schema_fingerprint
                    == backup_report.schema_fingerprint,
                )
            ):
                raise DatabaseIntegrityError("backup snapshot does not match source")
            backup_hash = _file_sha256(temporary)
            created_at = self.clock()
            backup_id = _stable_hash(
                {
                    "source_audit_hash": source_report.audit_hash,
                    "backup_audit_hash": backup_report.audit_hash,
                    "backup_sha256": backup_hash,
                    "migration_head": backup_report.migration_head,
                    "schema_fingerprint": backup_report.schema_fingerprint,
                }
            )
            manifest = DatabaseBackupManifest(
                backup_id=backup_id,
                source_path=source,
                destination_path=destination,
                created_at=created_at,
                source_audit_hash=source_report.audit_hash,
                backup_audit_hash=backup_report.audit_hash,
                backup_sha256=backup_hash,
                backup_size_bytes=temporary.stat().st_size,
                migration_head=backup_report.migration_head,
                schema_fingerprint=backup_report.schema_fingerprint,
                table_counts_match=table_counts_match,
            )
            _publish_without_overwrite(temporary, destination)
            return manifest
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    def dry_run_restore(
        self,
        *,
        backup_path: Path,
        destination_path: Path,
    ) -> DatabaseRestoreReport:
        backup, destination = _safe_operation_paths(backup_path, destination_path)
        _require_distinct_new_destination(backup, destination)
        source_report = self.integrity_service.audit(backup)
        _require_restorable(source_report)

        temporary = _copy_to_temporary(
            source=backup,
            destination=destination,
            pages_per_step=self.pages_per_step,
            progress=self.progress,
        )
        try:
            SQLiteStore(temporary).initialize()
            restored_report = self.integrity_service.audit(temporary)
            _require_passed(restored_report, "restored database failed audit")
            source_counts = {item.table: item.rows for item in source_report.table_counts}
            restored_counts = {
                item.table: item.rows for item in restored_report.table_counts
            }
            migration_owned_tables = {"schema_fingerprints", "schema_migrations"}
            common_table_counts_match = all(
                restored_counts.get(table) == rows
                for table, rows in source_counts.items()
                if table not in migration_owned_tables
            ) and all(
                restored_counts.get(table, 0) >= source_counts.get(table, 0)
                for table in migration_owned_tables
            )
            if not common_table_counts_match:
                raise DatabaseIntegrityError("restore changed source table row counts")
            if restored_report.migration_head != MIGRATION_HEAD:
                raise DatabaseIntegrityError("restore did not reach the migration head")
            restored_hash = _file_sha256(temporary)
            restored_at = self.clock()
            restore_id = _stable_hash(
                {
                    "source_audit_hash": source_report.audit_hash,
                    "restored_audit_hash": restored_report.audit_hash,
                    "restored_sha256": restored_hash,
                    "source_migration_head": source_report.migration_head,
                    "restored_migration_head": restored_report.migration_head,
                }
            )
            report = DatabaseRestoreReport(
                restore_id=restore_id,
                backup_path=backup,
                destination_path=destination,
                restored_at=restored_at,
                source_audit_hash=source_report.audit_hash,
                restored_audit_hash=restored_report.audit_hash,
                source_migration_head=source_report.migration_head,
                restored_migration_head=restored_report.migration_head,
                migration_applied=(
                    source_report.migration_head != restored_report.migration_head
                ),
                common_table_counts_match=common_table_counts_match,
                restored_schema_fingerprint=restored_report.schema_fingerprint,
                restored_sha256=restored_hash,
            )
            _publish_without_overwrite(temporary, destination)
            return report
        except Exception:
            temporary.unlink(missing_ok=True)
            raise


def database_integrity_json(report: DatabaseIntegrityReport) -> dict[str, object]:
    return {
        "database_path": str(report.database_path),
        "checked_at": report.checked_at.isoformat(),
        "status": report.status.value,
        "integrity_messages": list(report.integrity_messages),
        "foreign_key_violations": [
            {
                "table": item.table,
                "row_id": item.row_id,
                "parent": item.parent,
                "foreign_key_id": item.foreign_key_id,
            }
            for item in report.foreign_key_violations
        ],
        "table_counts": {item.table: item.rows for item in report.table_counts},
        "schema_version": report.schema_version,
        "migration_head": report.migration_head,
        "migration_checksums_valid": report.migration_checksums_valid,
        "migration_ledger_is_prefix": report.migration_ledger_is_prefix,
        "schema_fingerprint": report.schema_fingerprint,
        "computed_schema_fingerprint": report.computed_schema_fingerprint,
        "schema_fingerprint_valid": report.schema_fingerprint_valid,
        "schema_definition_valid": report.schema_definition_valid,
        "credential_columns_absent": report.credential_columns_absent,
        "requires_migration": report.requires_migration,
        "warnings": list(report.warnings),
        "error_code": report.error_code,
        "audit_hash": report.audit_hash,
        "model_version": report.model_version,
    }


def database_backup_json(manifest: DatabaseBackupManifest) -> dict[str, object]:
    return {
        "backup_id": manifest.backup_id,
        "source_path": str(manifest.source_path),
        "destination_path": str(manifest.destination_path),
        "created_at": manifest.created_at.isoformat(),
        "source_audit_hash": manifest.source_audit_hash,
        "backup_audit_hash": manifest.backup_audit_hash,
        "backup_sha256": manifest.backup_sha256,
        "backup_size_bytes": manifest.backup_size_bytes,
        "migration_head": manifest.migration_head,
        "schema_fingerprint": manifest.schema_fingerprint,
        "table_counts_match": manifest.table_counts_match,
        "model_version": manifest.model_version,
    }


def database_restore_json(report: DatabaseRestoreReport) -> dict[str, object]:
    return {
        "restore_id": report.restore_id,
        "backup_path": str(report.backup_path),
        "destination_path": str(report.destination_path),
        "restored_at": report.restored_at.isoformat(),
        "source_audit_hash": report.source_audit_hash,
        "restored_audit_hash": report.restored_audit_hash,
        "source_migration_head": report.source_migration_head,
        "restored_migration_head": report.restored_migration_head,
        "migration_applied": report.migration_applied,
        "common_table_counts_match": report.common_table_counts_match,
        "restored_schema_fingerprint": report.restored_schema_fingerprint,
        "restored_sha256": report.restored_sha256,
        "model_version": report.model_version,
    }


def serialize_database_report(document: dict[str, object]) -> str:
    return json.dumps(document, indent=2, sort_keys=True)


def _integrity_report(
    *,
    database_path: Path,
    checked_at: datetime,
    passed: bool,
    integrity_messages: tuple[str, ...] = (),
    foreign_key_violations: tuple[ForeignKeyViolation, ...] = (),
    table_counts: tuple[DatabaseTableCount, ...] = (),
    schema_version: str = "",
    migration_head: str = "",
    migration_checksums_valid: bool = False,
    migration_ledger_is_prefix: bool = False,
    schema_fingerprint: str = "",
    computed_schema_fingerprint: str = "",
    schema_fingerprint_valid: bool = False,
    schema_definition_valid: bool = False,
    credential_columns_absent: bool = False,
    warnings: tuple[str, ...] = (),
    error_code: str = "",
) -> DatabaseIntegrityReport:
    content = {
        "status": DatabaseAuditStatus.PASSED.value
        if passed
        else DatabaseAuditStatus.FAILED.value,
        "integrity_messages": integrity_messages,
        "foreign_key_violations": [
            (item.table, item.row_id, item.parent, item.foreign_key_id)
            for item in foreign_key_violations
        ],
        "table_counts": [(item.table, item.rows) for item in table_counts],
        "schema_version": schema_version,
        "migration_head": migration_head,
        "migration_checksums_valid": migration_checksums_valid,
        "migration_ledger_is_prefix": migration_ledger_is_prefix,
        "schema_fingerprint": schema_fingerprint,
        "computed_schema_fingerprint": computed_schema_fingerprint,
        "schema_fingerprint_valid": schema_fingerprint_valid,
        "schema_definition_valid": schema_definition_valid,
        "credential_columns_absent": credential_columns_absent,
        "warnings": warnings,
        "error_code": error_code,
        "model_version": DATABASE_ENGINEERING_VERSION,
    }
    return DatabaseIntegrityReport(
        database_path=database_path,
        checked_at=checked_at,
        status=(DatabaseAuditStatus.PASSED if passed else DatabaseAuditStatus.FAILED),
        integrity_messages=integrity_messages,
        foreign_key_violations=foreign_key_violations,
        table_counts=table_counts,
        schema_version=schema_version,
        migration_head=migration_head,
        migration_checksums_valid=migration_checksums_valid,
        migration_ledger_is_prefix=migration_ledger_is_prefix,
        schema_fingerprint=schema_fingerprint,
        computed_schema_fingerprint=computed_schema_fingerprint,
        schema_fingerprint_valid=schema_fingerprint_valid,
        schema_definition_valid=schema_definition_valid,
        credential_columns_absent=credential_columns_absent,
        requires_migration=bool(migration_head and migration_head != MIGRATION_HEAD),
        warnings=warnings,
        error_code=error_code,
        audit_hash=_stable_hash(content),
    )


def _table_counts(connection: sqlite3.Connection) -> tuple[DatabaseTableCount, ...]:
    tables = tuple(
        str(row[0])
        for row in connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()
    )
    return tuple(
        DatabaseTableCount(
            table=table,
            rows=int(
                connection.execute(
                    f'SELECT COUNT(*) FROM "{table.replace(chr(34), chr(34) * 2)}"'
                ).fetchone()[0]
            ),
        )
        for table in tables
    )


def _credential_columns_absent(connection: sqlite3.Connection) -> bool:
    schema: dict[str, dict[str, str]] = {}
    for row in connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
    ).fetchall():
        table = str(row[0])
        escaped = table.replace('"', '""')
        schema[table] = {
            str(column[1]): ""
            for column in connection.execute(
                f'PRAGMA table_info("{escaped}")'
            ).fetchall()
        }
    try:
        reject_sensitive_structure(schema, path="database_schema")
    except ValueError:
        return False
    return True


def _schema_metadata(connection: sqlite3.Connection) -> dict[str, str]:
    return {
        str(row[0]): str(row[1])
        for row in connection.execute(
            "SELECT key, value FROM schema_metadata ORDER BY key"
        ).fetchall()
    }


def _migration_ledger_state(
    connection: sqlite3.Connection,
    migration_head: str,
) -> tuple[bool, bool]:
    rows = connection.execute(
        "SELECT migration_id, checksum FROM schema_migrations ORDER BY migration_id"
    ).fetchall()
    applied_ids = tuple(str(row[0]) for row in rows)
    known_ids = tuple(item.migration_id for item in MIGRATIONS)
    is_prefix = (
        bool(applied_ids)
        and len(applied_ids) <= len(known_ids)
        and applied_ids == known_ids[: len(applied_ids)]
        and migration_head == applied_ids[-1]
    )
    known_checksums = {item.migration_id: item.checksum for item in MIGRATIONS}
    checksums_valid = is_prefix and all(
        known_checksums.get(str(row[0])) == str(row[1]) for row in rows
    )
    return checksums_valid, is_prefix


def _fingerprint_state(
    connection: sqlite3.Connection,
    *,
    migration_head: str,
    stored_fingerprint: str,
    computed_fingerprint: str,
) -> tuple[bool, bool]:
    row = connection.execute(
        """
        SELECT schema_fingerprint, schema_definition_hash
        FROM schema_fingerprints
        WHERE migration_head = ?
        """,
        (migration_head,),
    ).fetchone()
    if row is None:
        return False, False
    expected_definition_hash = expected_schema_definition_hash(
        migration_head,
        current_schema_definition=SCHEMA,
    )
    fingerprint_valid = (
        bool(stored_fingerprint)
        and stored_fingerprint == computed_fingerprint == str(row[0])
    )
    return (
        fingerprint_valid,
        expected_definition_hash is not None
        and str(row[1]) == expected_definition_hash,
    )


def _audit_warnings(
    *,
    schema_version: str,
    migration_head: str,
    credential_columns_absent: bool,
) -> tuple[str, ...]:
    warnings: list[str] = []
    if schema_version != DATABASE_SCHEMA_VERSION:
        warnings.append("Database schema version differs from this framework")
    if migration_head != MIGRATION_HEAD:
        warnings.append("Database requires migration in an isolated restored copy")
    if not credential_columns_absent:
        warnings.append("Credential-like schema columns are not allowed in backups")
    return tuple(warnings)


def _read_only_connection(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
    connection.execute("PRAGMA query_only = ON")
    return connection


def _require_database_file(path: Path) -> None:
    if not path.is_file():
        raise ValueError("database path must be an existing regular file")


def _safe_operation_paths(
    source_path: Path,
    destination_path: Path,
) -> tuple[Path, Path]:
    source_input = source_path.expanduser()
    destination_input = destination_path.expanduser()
    if source_input.is_symlink():
        raise DatabaseIntegrityError("source database must not be a symbolic link")
    if destination_input.is_symlink():
        raise DatabaseIntegrityError("destination must not be a symbolic link")
    return source_input.resolve(), destination_input.resolve()


def _require_distinct_new_destination(source: Path, destination: Path) -> None:
    _require_database_file(source)
    if source == destination:
        raise DatabaseIntegrityError("source and destination must be different")
    if destination.exists():
        raise DatabaseIntegrityError("destination already exists; overwrite is disabled")
    destination.parent.mkdir(parents=True, exist_ok=True)


def _copy_to_temporary(
    *,
    source: Path,
    destination: Path,
    pages_per_step: int,
    progress: BackupProgress | None,
) -> Path:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with (
            _read_only_connection(source) as source_connection,
            sqlite3.connect(temporary) as destination_connection,
        ):
            source_connection.backup(
                destination_connection,
                pages=pages_per_step,
                progress=progress,
            )
            destination_connection.execute("PRAGMA journal_mode = DELETE")
        with temporary.open("rb") as backup_file:
            os.fsync(backup_file.fileno())
        return temporary
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _publish_without_overwrite(temporary: Path, destination: Path) -> None:
    try:
        temporary.chmod(0o600)
        os.link(temporary, destination)
    except FileExistsError as error:
        raise DatabaseIntegrityError(
            "destination appeared during backup; overwrite is disabled"
        ) from error
    finally:
        temporary.unlink(missing_ok=True)


def _require_passed(report: DatabaseIntegrityReport, message: str) -> None:
    if not report.passed:
        raise DatabaseIntegrityError(f"{message} ({report.error_code})")


def _require_restorable(report: DatabaseIntegrityReport) -> None:
    if report.passed:
        return
    safe_for_forward_migration = all(
        (
            report.requires_migration,
            report.integrity_messages == ("ok",),
            not report.foreign_key_violations,
            report.migration_checksums_valid,
            report.migration_ledger_is_prefix,
            report.schema_fingerprint_valid,
            report.schema_definition_valid,
            report.credential_columns_absent,
            report.schema_version == DATABASE_SCHEMA_VERSION,
        )
    )
    if not safe_for_forward_migration:
        raise DatabaseIntegrityError(
            f"backup failed pre-restore audit ({report.error_code})"
        )


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source_file:
        for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


__all__ = [
    "DatabaseAuditStatus",
    "DatabaseBackupManifest",
    "DatabaseIntegrityReport",
    "DatabaseRestoreReport",
    "DatabaseTableCount",
    "ForeignKeyViolation",
    "SQLiteBackupService",
    "SQLiteIntegrityService",
    "database_backup_json",
    "database_integrity_json",
    "database_restore_json",
    "serialize_database_report",
]
