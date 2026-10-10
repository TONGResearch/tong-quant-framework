import json
import os
import shutil
import sqlite3
import stat
import tempfile
import zipfile
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path, PurePosixPath

from tong_quant.core.security import (
    contains_sensitive_assignment,
    reject_sensitive_structure,
)
from tong_quant.data.evidence_bundle import verify_provider_evidence_document
from tong_quant.data.evidence_horizon import (
    EvidenceHorizonPolicy,
    evaluate_provider_evidence_horizon,
    provider_evidence_horizon_json,
    required_provider_evidence_scopes,
)
from tong_quant.data.storage.engineering import SQLiteBackupService, SQLiteIntegrityService
from tong_quant.domain.models import require_timezone
from tong_quant.version import (
    PROVIDER_EVIDENCE_ARCHIVE_VERSION,
    PROVIDER_EVIDENCE_HORIZON_LEGACY_VERSION,
    PROVIDER_EVIDENCE_HORIZON_VERSION,
)

_MAX_ARCHIVE_ENTRIES = 10_000
_MAX_UNCOMPRESSED_BYTES = 512 * 1024 * 1024
_HISTORY_DATABASE_ENTRY = "data/provider-contract-monitor.sqlite3"
_HISTORY_TABLES = frozenset({"provider_contract_runs", "provider_contract_checks"})


@dataclass(frozen=True, slots=True)
class ProviderEvidenceArchiveManifest:
    archive_id: str
    artifact_file: str
    artifact_sha256: str
    artifact_size: int
    bundle_entry: str
    bundle_id: str
    horizon_entry: str
    horizon_report_id: str
    verified_at: datetime
    implementation_version: str = PROVIDER_EVIDENCE_ARCHIVE_VERSION

    def __post_init__(self) -> None:
        require_timezone(self.verified_at, "provider evidence archive verified_at")
        if len(self.archive_id) != 64 or len(self.artifact_sha256) != 64:
            raise ValueError("provider evidence archive identities must be SHA-256")
        if len(self.bundle_id) != 64 or len(self.horizon_report_id) != 64:
            raise ValueError("provider evidence document identities must be SHA-256")
        if self.artifact_size < 1:
            raise ValueError("provider evidence archive cannot be empty")
        if not self.implementation_version.strip():
            raise ValueError("provider evidence archive version is required")
        _require_safe_basename(self.artifact_file)
        if not self.artifact_file.endswith(".zip"):
            raise ValueError("provider evidence archive file must be a ZIP")
        _require_safe_member(self.bundle_entry)
        _require_safe_member(self.horizon_entry)
        expected = _stable_hash(_manifest_content(self, include_archive_id=False))
        if self.archive_id != expected:
            raise ValueError("provider evidence archive manifest hash does not match")


@dataclass(frozen=True, slots=True)
class ProviderEvidenceArchiveResult:
    manifest: ProviderEvidenceArchiveManifest
    artifact_path: Path
    manifest_path: Path


@dataclass(frozen=True, slots=True)
class ProviderEvidenceRestoreDrill:
    archive_id: str
    artifact_sha256: str
    source_audit_hash: str
    restored_audit_hash: str
    source_migration_head: str
    restored_migration_head: str
    restored_schema_fingerprint: str
    migration_applied: bool
    table_counts_match: bool
    contract_runs: int
    contract_checks: int
    baseline_manifests: int


@dataclass(frozen=True, slots=True)
class _InspectedArtifact:
    bundle_entry: str
    bundle_id: str
    horizon_entry: str
    horizon_report_id: str


def archive_provider_evidence_artifact(
    artifact: Path,
    destination: Path,
    *,
    verified_at: datetime,
    expected_sha256: str | None = None,
) -> ProviderEvidenceArchiveResult:
    require_timezone(verified_at, "provider evidence archive verified_at")
    if artifact.is_symlink() or not artifact.is_file():
        raise ValueError("provider evidence artifact must be a regular file")
    artifact_sha256 = _file_sha256(artifact)
    if expected_sha256 is not None and artifact_sha256 != expected_sha256:
        raise ValueError("provider evidence artifact SHA-256 does not match")
    inspected = _inspect_artifact(artifact)
    artifact_file = f"provider-contract-evidence-{artifact_sha256}.zip"
    values = _manifest_values(
        archive_id="",
        include_archive_id=False,
        artifact_file=artifact_file,
        artifact_sha256=artifact_sha256,
        artifact_size=artifact.stat().st_size,
        bundle_entry=inspected.bundle_entry,
        bundle_id=inspected.bundle_id,
        horizon_entry=inspected.horizon_entry,
        horizon_report_id=inspected.horizon_report_id,
        verified_at=verified_at,
        implementation_version=PROVIDER_EVIDENCE_ARCHIVE_VERSION,
    )
    manifest = ProviderEvidenceArchiveManifest(
        archive_id=_stable_hash(values),
        artifact_file=artifact_file,
        artifact_sha256=artifact_sha256,
        artifact_size=artifact.stat().st_size,
        bundle_entry=inspected.bundle_entry,
        bundle_id=inspected.bundle_id,
        horizon_entry=inspected.horizon_entry,
        horizon_report_id=inspected.horizon_report_id,
        verified_at=verified_at,
    )
    _prepare_destination(destination)
    artifact_path = destination / artifact_file
    _copy_idempotent(artifact, artifact_path, expected_sha256=artifact_sha256)
    manifest_path = destination / f"provider-evidence-archive-{manifest.archive_id}.json"
    _write_idempotent(
        manifest_path,
        serialize_provider_evidence_archive_manifest(manifest) + "\n",
    )
    return ProviderEvidenceArchiveResult(
        manifest=manifest,
        artifact_path=artifact_path,
        manifest_path=manifest_path,
    )


def verify_provider_evidence_archive(
    manifest_path: Path,
) -> ProviderEvidenceArchiveManifest:
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("provider evidence archive manifest must be a regular file")
    document = _read_json_bytes(manifest_path.read_bytes(), "archive manifest")
    reject_sensitive_structure(document, path="provider_evidence_archive")
    manifest = _manifest_from_document(document)
    artifact_path = manifest_path.parent / manifest.artifact_file
    if artifact_path.is_symlink() or not artifact_path.is_file():
        raise ValueError("archived provider evidence artifact is missing")
    if artifact_path.stat().st_size != manifest.artifact_size:
        raise ValueError("archived provider evidence artifact size does not match")
    if _file_sha256(artifact_path) != manifest.artifact_sha256:
        raise ValueError("archived provider evidence artifact SHA-256 does not match")
    inspected = _inspect_artifact(artifact_path)
    if (
        inspected.bundle_entry != manifest.bundle_entry
        or inspected.bundle_id != manifest.bundle_id
        or inspected.horizon_entry != manifest.horizon_entry
        or inspected.horizon_report_id != manifest.horizon_report_id
    ):
        raise ValueError("archived provider evidence identities do not match manifest")
    return manifest


def drill_provider_evidence_archive(manifest_path: Path) -> ProviderEvidenceRestoreDrill:
    manifest = verify_provider_evidence_archive(manifest_path)
    artifact_path = manifest_path.parent / manifest.artifact_file
    with tempfile.TemporaryDirectory(prefix="provider-evidence-restore-") as directory:
        backup_path = Path(directory) / "provider-history.sqlite3"
        restored_path = Path(directory) / "restored.sqlite3"
        try:
            with (
                zipfile.ZipFile(artifact_path) as archive,
                archive.open(_HISTORY_DATABASE_ENTRY) as source,
                backup_path.open("xb") as backup,
            ):
                shutil.copyfileobj(source, backup)
        except (KeyError, zipfile.BadZipFile) as error:
            raise ValueError("provider evidence artifact changed during restore drill") from error
        backup_path.chmod(0o600)
        if _file_sha256(artifact_path) != manifest.artifact_sha256:
            raise ValueError("provider evidence artifact changed during restore drill")

        integrity = SQLiteIntegrityService()
        source_report = integrity.audit(backup_path)
        restored = SQLiteBackupService(integrity_service=integrity).dry_run_restore(
            backup_path=backup_path,
            destination_path=restored_path,
        )
        independent_report = integrity.audit(restored_path)
        if (
            not independent_report.passed
            or independent_report.audit_hash != restored.restored_audit_hash
        ):
            raise ValueError("provider evidence restored database failed independent audit")
        if _file_sha256(artifact_path) != manifest.artifact_sha256:
            raise ValueError("provider evidence artifact changed during restore drill")
        counts = {item.table: item.rows for item in independent_report.table_counts}
        return ProviderEvidenceRestoreDrill(
            archive_id=manifest.archive_id,
            artifact_sha256=manifest.artifact_sha256,
            source_audit_hash=source_report.audit_hash,
            restored_audit_hash=independent_report.audit_hash,
            source_migration_head=source_report.migration_head,
            restored_migration_head=independent_report.migration_head,
            restored_schema_fingerprint=independent_report.schema_fingerprint,
            migration_applied=restored.migration_applied,
            table_counts_match=restored.common_table_counts_match,
            contract_runs=counts["provider_contract_runs"],
            contract_checks=counts["provider_contract_checks"],
            baseline_manifests=counts["provider_baseline_manifests"],
        )


def provider_evidence_restore_drill_json(
    report: ProviderEvidenceRestoreDrill,
) -> dict[str, object]:
    return {
        "archive_id": report.archive_id,
        "artifact_sha256": report.artifact_sha256,
        "source_audit_hash": report.source_audit_hash,
        "restored_audit_hash": report.restored_audit_hash,
        "source_migration_head": report.source_migration_head,
        "restored_migration_head": report.restored_migration_head,
        "restored_schema_fingerprint": report.restored_schema_fingerprint,
        "migration_applied": report.migration_applied,
        "table_counts_match": report.table_counts_match,
        "contract_runs": report.contract_runs,
        "contract_checks": report.contract_checks,
        "baseline_manifests": report.baseline_manifests,
    }


def provider_evidence_archive_manifest_json(
    manifest: ProviderEvidenceArchiveManifest,
) -> dict[str, object]:
    return _manifest_content(manifest, include_archive_id=True)


def serialize_provider_evidence_archive_manifest(
    manifest: ProviderEvidenceArchiveManifest,
) -> str:
    return json.dumps(
        provider_evidence_archive_manifest_json(manifest),
        indent=2,
        sort_keys=True,
    )


def _inspect_artifact(path: Path) -> _InspectedArtifact:
    if not zipfile.is_zipfile(path):
        raise ValueError("provider evidence artifact must be a ZIP archive")
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if not infos or len(infos) > _MAX_ARCHIVE_ENTRIES:
                raise ValueError("provider evidence artifact entry count is invalid")
            names = tuple(item.filename for item in infos)
            if len(names) != len(set(names)):
                raise ValueError("provider evidence artifact contains duplicate entries")
            if names.count(_HISTORY_DATABASE_ENTRY) != 1:
                raise ValueError("provider evidence artifact requires contract history database")
            total_size = 0
            for info in infos:
                _require_safe_member(info.filename)
                if info.flag_bits & 0x1:
                    raise ValueError("provider evidence artifact cannot be encrypted")
                mode = info.external_attr >> 16
                if stat.S_ISLNK(mode):
                    raise ValueError("provider evidence artifact cannot contain links")
                total_size += info.file_size
            if total_size > _MAX_UNCOMPRESSED_BYTES:
                raise ValueError("provider evidence artifact is too large to verify")

            json_documents: dict[str, dict[str, object]] = {}
            for name in names:
                if not name.endswith(".json"):
                    if name.endswith((".md", ".txt")):
                        try:
                            text = archive.read(name).decode("utf-8")
                        except UnicodeDecodeError as error:
                            raise ValueError(
                                "provider evidence text artifact must be UTF-8"
                            ) from error
                        if contains_sensitive_assignment(text):
                            raise ValueError(
                                "provider evidence text contains credential-like data"
                            )
                    continue
                document = _read_json_bytes(archive.read(name), name)
                reject_sensitive_structure(document, path=f"artifact.{name}")
                json_documents[name] = document

            bundle_entries = tuple(
                name
                for name in json_documents
                if PurePosixPath(name).name.startswith("provider-evidence-bundle-")
            )
            horizon_entries = tuple(
                name
                for name in json_documents
                if PurePosixPath(name).name.startswith("provider-evidence-horizon-")
            )
            if len(bundle_entries) != 1 or len(horizon_entries) != 1:
                raise ValueError(
                    "provider evidence artifact requires one bundle and one horizon report"
                )
            bundle_entry = bundle_entries[0]
            horizon_entry = horizon_entries[0]
            bundle_document = json_documents[bundle_entry]
            horizon_document = json_documents[horizon_entry]
            verify_provider_evidence_document(bundle_document)
            _verify_history_database(archive, bundle_document)
            report_version = _required_text(horizon_document, "implementation_version")
            if report_version == PROVIDER_EVIDENCE_HORIZON_LEGACY_VERSION:
                policy = EvidenceHorizonPolicy(
                    required_scopes=required_provider_evidence_scopes(),
                    require_scheduled_provenance=False,
                    version=PROVIDER_EVIDENCE_HORIZON_LEGACY_VERSION,
                )
            elif report_version == PROVIDER_EVIDENCE_HORIZON_VERSION:
                policy = None
            else:
                raise ValueError("provider evidence horizon version is unsupported")
            expected_horizon = provider_evidence_horizon_json(
                evaluate_provider_evidence_horizon(
                    bundle_document,
                    policy=policy,
                    report_version=report_version,
                )
            )
            if horizon_document != expected_horizon:
                raise ValueError(
                    "provider evidence horizon report cannot be reconstructed"
                )
            bundle_id = _required_text(bundle_document, "bundle_id")
            horizon_report_id = _required_text(horizon_document, "report_id")
            if not PurePosixPath(bundle_entry).name.endswith(f"{bundle_id}.json"):
                raise ValueError("provider evidence bundle filename does not match identity")
            if not PurePosixPath(horizon_entry).name.endswith(
                f"{horizon_report_id}.json"
            ):
                raise ValueError("provider evidence horizon filename does not match identity")
            return _InspectedArtifact(
                bundle_entry=bundle_entry,
                bundle_id=bundle_id,
                horizon_entry=horizon_entry,
                horizon_report_id=horizon_report_id,
            )
    except zipfile.BadZipFile as error:
        raise ValueError("provider evidence artifact ZIP is invalid") from error


def _verify_history_database(
    archive: zipfile.ZipFile,
    bundle_document: dict[str, object],
) -> None:
    with tempfile.NamedTemporaryFile(prefix="provider-history-", suffix=".sqlite3") as temporary:
        with archive.open(_HISTORY_DATABASE_ENTRY) as source:
            shutil.copyfileobj(source, temporary)
        temporary.flush()
        temporary.seek(0)
        if temporary.read(16) != b"SQLite format 3\x00":
            raise ValueError("provider evidence contract history database is invalid")
        try:
            uri = f"{Path(temporary.name).as_uri()}?mode=ro&immutable=1"
            with closing(sqlite3.connect(uri, uri=True)) as connection:
                result = tuple(row[0] for row in connection.execute("PRAGMA integrity_check"))
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    )
                }
                missing_history = any(
                    connection.execute(
                        f"SELECT 1 FROM {table} WHERE {column} = ?",
                        (identity,),
                    ).fetchone()
                    is None
                    for table, column, identities in _bundle_history_ids(bundle_document)
                    for identity in identities
                )
        except sqlite3.DatabaseError as error:
            raise ValueError("provider evidence contract history database is invalid") from error
        if result != ("ok",):
            raise ValueError("provider evidence contract history database failed integrity check")
        if not tables >= _HISTORY_TABLES:
            raise ValueError("provider evidence contract history tables are missing")
        if missing_history:
            raise ValueError("provider evidence history database omits bundled records")


def _bundle_history_ids(
    document: dict[str, object],
) -> tuple[tuple[str, str, frozenset[str]], ...]:
    tables = document.get("tables")
    if not isinstance(tables, list):
        raise ValueError("provider evidence bundle tables are invalid")
    identities: list[tuple[str, str, frozenset[str]]] = []
    for table, column in (
        ("provider_contract_runs", "run_id"),
        ("provider_contract_checks", "check_id"),
        ("provider_baseline_manifests", "manifest_id"),
    ):
        matches = [item for item in tables if isinstance(item, dict) and item.get("table") == table]
        if len(matches) > 1:
            raise ValueError("provider evidence bundle has duplicate history tables")
        if not matches:
            continue
        snapshot = matches[0]
        columns = snapshot.get("columns")
        rows = snapshot.get("rows")
        if not isinstance(columns, list) or column not in columns or not isinstance(rows, list):
            raise ValueError("provider evidence bundle history table is invalid")
        index = columns.index(column)
        values: set[str] = set()
        for row in rows:
            if not isinstance(row, list) or not isinstance(row[index], str):
                raise ValueError("provider evidence bundle history identity is invalid")
            values.add(row[index])
        identities.append((table, column, frozenset(values)))
    return tuple(identities)


def _prepare_destination(destination: Path) -> None:
    if destination.is_symlink():
        raise ValueError("provider evidence archive destination cannot be a link")
    destination.mkdir(parents=True, exist_ok=True)
    if not destination.is_dir():
        raise ValueError("provider evidence archive destination must be a directory")


def _copy_idempotent(source: Path, target: Path, *, expected_sha256: str) -> None:
    if target.is_symlink():
        raise ValueError("provider evidence archive target cannot be a link")
    if target.exists():
        if not target.is_file() or _file_sha256(target) != expected_sha256:
            raise ValueError("provider evidence archive identity collision")
        target.chmod(0o600)
        return
    temporary_path: Path | None = None
    linked_target = False
    try:
        with tempfile.NamedTemporaryFile(
            mode="w+b",
            dir=target.parent,
            prefix=".provider-evidence-",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            with source.open("rb") as source_file:
                shutil.copyfileobj(source_file, temporary)
            temporary.flush()
            os.fsync(temporary.fileno())
        temporary_path.chmod(0o600)
        try:
            os.link(temporary_path, target)
            linked_target = True
        except FileExistsError:
            if target.is_symlink() or _file_sha256(target) != expected_sha256:
                raise ValueError("provider evidence archive identity collision") from None
        if _file_sha256(target) != expected_sha256:
            if linked_target:
                target.unlink(missing_ok=True)
            raise ValueError("provider evidence archive copy failed verification")
        target.chmod(0o600)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _write_idempotent(path: Path, content: str) -> None:
    if path.is_symlink():
        raise ValueError("provider evidence archive manifest cannot be a link")
    if path.exists():
        if not path.is_file() or path.read_text(encoding="utf-8") != content:
            raise ValueError("provider evidence archive manifest identity collision")
        path.chmod(0o600)
        return
    encoded = content.encode("utf-8")
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w+b",
            dir=path.parent,
            prefix=".provider-evidence-manifest-",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(encoded)
            temporary.flush()
            os.fsync(temporary.fileno())
        temporary_path.chmod(0o600)
        try:
            os.link(temporary_path, path)
        except FileExistsError:
            if path.is_symlink() or path.read_bytes() != encoded:
                raise ValueError(
                    "provider evidence archive manifest identity collision"
                ) from None
        path.chmod(0o600)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _manifest_from_document(document: dict[str, object]) -> ProviderEvidenceArchiveManifest:
    return ProviderEvidenceArchiveManifest(
        archive_id=_required_text(document, "archive_id"),
        artifact_file=_required_text(document, "artifact_file"),
        artifact_sha256=_required_text(document, "artifact_sha256"),
        artifact_size=_required_int(document, "artifact_size"),
        bundle_entry=_required_text(document, "bundle_entry"),
        bundle_id=_required_text(document, "bundle_id"),
        horizon_entry=_required_text(document, "horizon_entry"),
        horizon_report_id=_required_text(document, "horizon_report_id"),
        verified_at=_required_datetime(document, "verified_at"),
        implementation_version=_required_text(document, "implementation_version"),
    )


def _manifest_content(
    manifest: ProviderEvidenceArchiveManifest,
    *,
    include_archive_id: bool,
) -> dict[str, object]:
    return _manifest_values(
        archive_id=manifest.archive_id,
        include_archive_id=include_archive_id,
        artifact_file=manifest.artifact_file,
        artifact_sha256=manifest.artifact_sha256,
        artifact_size=manifest.artifact_size,
        bundle_entry=manifest.bundle_entry,
        bundle_id=manifest.bundle_id,
        horizon_entry=manifest.horizon_entry,
        horizon_report_id=manifest.horizon_report_id,
        verified_at=manifest.verified_at,
        implementation_version=manifest.implementation_version,
    )


def _manifest_values(
    *,
    archive_id: str,
    include_archive_id: bool,
    artifact_file: str,
    artifact_sha256: str,
    artifact_size: int,
    bundle_entry: str,
    bundle_id: str,
    horizon_entry: str,
    horizon_report_id: str,
    verified_at: datetime,
    implementation_version: str,
) -> dict[str, object]:
    document: dict[str, object] = {
        "artifact_file": artifact_file,
        "artifact_sha256": artifact_sha256,
        "artifact_size": artifact_size,
        "bundle_entry": bundle_entry,
        "bundle_id": bundle_id,
        "horizon_entry": horizon_entry,
        "horizon_report_id": horizon_report_id,
        "verified_at": verified_at.isoformat(),
        "implementation_version": implementation_version,
    }
    if include_archive_id:
        document["archive_id"] = archive_id
    return document


def _read_json_bytes(raw: bytes, label: str) -> dict[str, object]:
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} is not valid UTF-8 JSON") from error
    if not isinstance(document, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return document


def _require_safe_member(name: str) -> None:
    if not name or "\\" in name:
        raise ValueError("provider evidence artifact contains an unsafe path")
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("provider evidence artifact contains an unsafe path")


def _require_safe_basename(name: str) -> None:
    if (
        not name
        or name in {".", ".."}
        or "/" in name
        or "\\" in name
        or (len(name) >= 2 and name[1] == ":")
        or Path(name).name != name
    ):
        raise ValueError("provider evidence archive file must be a safe basename")


def _required_text(document: dict[str, object], field: str) -> str:
    value = document.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"provider evidence archive requires {field}")
    return value


def _required_int(document: dict[str, object], field: str) -> int:
    value = document.get(field)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"provider evidence archive requires integer {field}")
    return value


def _required_datetime(document: dict[str, object], field: str) -> datetime:
    value = _required_text(document, field)
    parsed = datetime.fromisoformat(value)
    require_timezone(parsed, f"provider evidence archive {field}")
    return parsed


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_hash(document: dict[str, object]) -> str:
    return sha256(
        json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


__all__ = [
    "ProviderEvidenceArchiveManifest",
    "ProviderEvidenceArchiveResult",
    "ProviderEvidenceRestoreDrill",
    "archive_provider_evidence_artifact",
    "drill_provider_evidence_archive",
    "provider_evidence_archive_manifest_json",
    "provider_evidence_restore_drill_json",
    "serialize_provider_evidence_archive_manifest",
    "verify_provider_evidence_archive",
]
