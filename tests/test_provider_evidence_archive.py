import json
import sqlite3
import stat
import subprocess
import sys
import zipfile
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import pytest

from tong_quant.data.evidence_archive import (
    archive_provider_evidence_artifact,
    drill_provider_evidence_archive,
    provider_evidence_archive_manifest_json,
    provider_evidence_restore_drill_json,
    verify_provider_evidence_archive,
)
from tong_quant.data.evidence_bundle import (
    ProviderEvidenceBundleExporter,
    provider_evidence_bundle_json,
)
from tong_quant.data.evidence_horizon import (
    evaluate_provider_evidence_horizon,
    provider_evidence_horizon_json,
)
from tong_quant.data.storage.engineering import SQLiteBackupService, SQLiteIntegrityService
from tong_quant.data.storage.sqlite import SQLiteStore

VERIFIED_AT = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)


def test_archive_is_content_addressed_idempotent_and_independently_verifiable(
    tmp_path: Path,
) -> None:
    artifact = _artifact(tmp_path)
    digest = sha256(artifact.read_bytes()).hexdigest()
    destination = tmp_path / "durable-copy"

    first = archive_provider_evidence_artifact(
        artifact,
        destination,
        verified_at=VERIFIED_AT,
        expected_sha256=digest,
    )
    second = archive_provider_evidence_artifact(
        artifact,
        destination,
        verified_at=VERIFIED_AT,
        expected_sha256=digest,
    )
    verified = verify_provider_evidence_archive(first.manifest_path)

    assert first == second
    assert verified == first.manifest
    assert first.artifact_path.name == f"provider-contract-evidence-{digest}.zip"
    assert stat.S_IMODE(first.artifact_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(first.manifest_path.stat().st_mode) == 0o600
    assert provider_evidence_archive_manifest_json(verified)["archive_id"] == (
        verified.archive_id
    )


def test_archive_rejects_digest_mismatch_and_unsafe_zip_member(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path)
    with pytest.raises(ValueError, match="SHA-256 does not match"):
        archive_provider_evidence_artifact(
            artifact,
            tmp_path / "digest-mismatch",
            verified_at=VERIFIED_AT,
            expected_sha256="0" * 64,
        )

    with zipfile.ZipFile(artifact, "a") as archive:
        archive.writestr("../escape.txt", "unsafe")
    with pytest.raises(ValueError, match="unsafe path"):
        archive_provider_evidence_artifact(
            artifact,
            tmp_path / "unsafe",
            verified_at=VERIFIED_AT,
        )


def test_archive_rejects_tampered_bundle_and_credential_json(tmp_path: Path) -> None:
    tampered = _artifact(tmp_path, name="tampered.zip", tamper_bundle=True)
    with pytest.raises(ValueError, match="hash does not match"):
        archive_provider_evidence_artifact(
            tampered,
            tmp_path / "tampered-copy",
            verified_at=VERIFIED_AT,
        )

    credential = _artifact(tmp_path, name="credential.zip")
    with zipfile.ZipFile(credential, "a") as archive:
        archive.writestr("provider-contract-artifacts/unsafe.json", '{"token":"x"}')
    with pytest.raises(ValueError, match="credential-like"):
        archive_provider_evidence_artifact(
            credential,
            tmp_path / "credential-copy",
            verified_at=VERIFIED_AT,
        )

    credential_text = _artifact(tmp_path, name="credential-text.zip")
    with zipfile.ZipFile(credential_text, "a") as archive:
        archive.writestr("provider-contract-artifacts/unsafe.md", "token=secret")
    with pytest.raises(ValueError, match="credential-like"):
        archive_provider_evidence_artifact(
            credential_text,
            tmp_path / "credential-text-copy",
            verified_at=VERIFIED_AT,
        )


def test_archive_rejects_missing_or_corrupt_history_database(tmp_path: Path) -> None:
    missing = _artifact(tmp_path, name="missing-history.zip", include_database=False)
    with pytest.raises(ValueError, match="requires contract history database"):
        archive_provider_evidence_artifact(
            missing,
            tmp_path / "missing-history-copy",
            verified_at=VERIFIED_AT,
        )

    corrupt = _artifact(
        tmp_path,
        name="corrupt-history.zip",
        database_override=b"not a SQLite database",
    )
    with pytest.raises(ValueError, match="contract history database is invalid"):
        archive_provider_evidence_artifact(
            corrupt,
            tmp_path / "corrupt-history-copy",
            verified_at=VERIFIED_AT,
        )

    empty = _artifact(tmp_path, name="empty-history.zip", database_override=b"")
    with pytest.raises(ValueError, match="contract history database is invalid"):
        archive_provider_evidence_artifact(
            empty,
            tmp_path / "empty-history-copy",
            verified_at=VERIFIED_AT,
        )

    unrelated_path = tmp_path / "unrelated.sqlite3"
    with sqlite3.connect(unrelated_path) as connection:
        connection.execute("CREATE TABLE unrelated (value TEXT)")
    unrelated = _artifact(
        tmp_path,
        name="unrelated-history.zip",
        database_override=unrelated_path.read_bytes(),
    )
    with pytest.raises(ValueError, match="contract history tables are missing"):
        archive_provider_evidence_artifact(
            unrelated,
            tmp_path / "unrelated-history-copy",
            verified_at=VERIFIED_AT,
        )


def test_archive_rejects_history_snapshot_missing_bundled_run(tmp_path: Path) -> None:
    empty_history = tmp_path / "empty-history.sqlite3"
    SQLiteStore(empty_history).initialize()
    empty_snapshot = tmp_path / "empty-history-snapshot.sqlite3"
    SQLiteBackupService(SQLiteIntegrityService()).create_backup(
        source_path=empty_history,
        destination_path=empty_snapshot,
    )
    artifact = _artifact(
        tmp_path,
        name="missing-bundled-run.zip",
        history_run=True,
        database_override=empty_snapshot.read_bytes(),
    )

    with pytest.raises(ValueError, match="omits bundled records"):
        archive_provider_evidence_artifact(
            artifact,
            tmp_path / "missing-bundled-run-copy",
            verified_at=VERIFIED_AT,
        )


def test_archive_cli_creates_and_verifies_manifest(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path)
    destination = tmp_path / "cli-copy"
    archive = subprocess.run(
        [
            sys.executable,
            "scripts/archive_provider_evidence.py",
            "archive",
            "--artifact",
            str(artifact),
            "--destination",
            str(destination),
            "--verified-at",
            VERIFIED_AT.isoformat(),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert archive.returncode == 0, archive.stderr
    manifest_path = next(destination.glob("provider-evidence-archive-*.json"))
    verify = subprocess.run(
        [
            sys.executable,
            "scripts/archive_provider_evidence.py",
            "verify",
            "--manifest",
            str(manifest_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert verify.returncode == 0, verify.stderr
    assert verify.stdout.strip() == verify_provider_evidence_archive(
        manifest_path
    ).archive_id


def test_restore_drill_preserves_history_and_emits_no_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact = _artifact(tmp_path, history_run=True)
    archived = archive_provider_evidence_artifact(
        artifact,
        tmp_path / "restore-copy",
        verified_at=VERIFIED_AT,
    )
    original_hash = sha256(archived.artifact_path.read_bytes()).hexdigest()
    monkeypatch.setattr("tong_quant.data.evidence_archive.tempfile.tempdir", str(tmp_path))

    first = drill_provider_evidence_archive(archived.manifest_path)
    second = drill_provider_evidence_archive(archived.manifest_path)
    safe_report = provider_evidence_restore_drill_json(first)

    assert first == second
    assert first.archive_id == archived.manifest.archive_id
    assert first.source_audit_hash == first.restored_audit_hash
    assert first.table_counts_match is True
    assert first.migration_applied is False
    assert first.contract_runs == 1
    assert first.contract_checks == 0
    assert first.baseline_manifests == 0
    assert str(tmp_path) not in json.dumps(safe_report)
    assert sha256(archived.artifact_path.read_bytes()).hexdigest() == original_hash
    assert list(tmp_path.glob("provider-evidence-restore-*")) == []

    cli = subprocess.run(
        [
            sys.executable,
            "scripts/archive_provider_evidence.py",
            "restore-drill",
            "--manifest",
            str(archived.manifest_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert cli.returncode == 0, cli.stderr
    assert json.loads(cli.stdout) == safe_report


def test_restore_drill_rejects_tampered_archive(tmp_path: Path) -> None:
    archived = archive_provider_evidence_artifact(
        _artifact(tmp_path),
        tmp_path / "tampered-restore-copy",
        verified_at=VERIFIED_AT,
    )
    archived.artifact_path.write_bytes(b"tampered")

    with pytest.raises(ValueError, match="artifact size does not match"):
        drill_provider_evidence_archive(archived.manifest_path)

    cli = subprocess.run(
        [
            sys.executable,
            "scripts/archive_provider_evidence.py",
            "restore-drill",
            "--manifest",
            str(archived.manifest_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert cli.returncode != 0
    assert "Provider evidence restore drill failed: ValueError" in cli.stderr
    assert str(tmp_path) not in cli.stderr


def _artifact(
    tmp_path: Path,
    *,
    name: str = "provider-artifact.zip",
    tamper_bundle: bool = False,
    include_database: bool = True,
    database_override: bytes | None = None,
    history_run: bool = False,
) -> Path:
    database = tmp_path / f"{name}.sqlite3"
    SQLiteStore(database).initialize()
    if history_run:
        with sqlite3.connect(database) as connection:
            connection.execute(
                """
                INSERT INTO provider_contract_runs (
                    run_id, started_at, completed_at, status,
                    implementation_version, generated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "fixture-run",
                    VERIFIED_AT.isoformat(),
                    VERIFIED_AT.isoformat(),
                    "healthy",
                    "fixture-v1",
                    VERIFIED_AT.isoformat(),
                ),
            )
    snapshot = tmp_path / f"{name}.snapshot.sqlite3"
    SQLiteBackupService(SQLiteIntegrityService()).create_backup(
        source_path=database,
        destination_path=snapshot,
    )
    bundle = ProviderEvidenceBundleExporter().export(snapshot, as_of=VERIFIED_AT)
    bundle_document = provider_evidence_bundle_json(bundle)
    horizon_document = provider_evidence_horizon_json(
        evaluate_provider_evidence_horizon(bundle_document)
    )
    if tamper_bundle:
        bundle_document["framework_version"] = "tampered"
    artifact = tmp_path / name
    with zipfile.ZipFile(artifact, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "provider-contract-artifacts/"
            f"provider-evidence-bundle-{bundle.bundle_id}.json",
            json.dumps(bundle_document, sort_keys=True),
        )
        archive.writestr(
            "provider-contract-artifacts/"
            f"provider-evidence-horizon-{horizon_document['report_id']}.json",
            json.dumps(horizon_document, sort_keys=True),
        )
        archive.writestr(
            "provider-contract-artifacts/provider-health.json",
            json.dumps({"status": "degraded"}),
        )
        if include_database:
            archive.writestr(
                "data/provider-contract-monitor.sqlite3",
                snapshot.read_bytes() if database_override is None else database_override,
            )
    return artifact
