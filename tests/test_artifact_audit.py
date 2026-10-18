import json
import os
import sqlite3
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

import pytest

from tong_quant.data.storage.artifact_audit import audit_provider_artifacts
from tong_quant.data.storage.sqlite import SQLiteStore

ROOT = Path(__file__).resolve().parents[1]
CONTENT = b"synthetic retained evidence"
DIGEST = sha256(CONTENT).hexdigest()
KEY = f"sha256/{DIGEST[:2]}/{DIGEST}.bin"


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    database = tmp_path / "source.sqlite3"
    # The audit intentionally supports the registry without migrating its database.
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE provider_artifacts (artifact_id TEXT PRIMARY KEY, "
            "content_hash TEXT, media_type TEXT, byte_size INTEGER, storage_key TEXT)"
        )
        connection.execute(
            "INSERT INTO provider_artifacts VALUES (?, ?, ?, ?, ?)",
            ("a" * 64, DIGEST, "application/json", len(CONTENT), KEY),
        )
    root = tmp_path / "artifacts"
    artifact = root / KEY
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(CONTENT)
    return database, root, artifact


def _status(report: dict[str, object]) -> str:
    entries = report["entries"]
    assert isinstance(entries, list)
    return str(entries[0]["status"])


def test_deterministic_read_only_audit(tmp_path: Path) -> None:
    database, root, artifact = _fixture(tmp_path)
    before = database.read_bytes(), artifact.read_bytes(), artifact.stat().st_mode
    report = audit_provider_artifacts(database, root)
    assert report == audit_provider_artifacts(database, root)
    assert report["registered_artifacts_verified"] is True
    assert report["registered_count"] == report["verified_count"] == 1
    assert _status(report) == "verified"
    assert (database.read_bytes(), artifact.read_bytes(), artifact.stat().st_mode) == before
    assert str(tmp_path) not in json.dumps(report)
    assert KEY not in json.dumps(report)
    destination = tmp_path / "destination"
    destination.mkdir()
    relocated_database, relocated_root, _ = _fixture(destination)
    assert audit_provider_artifacts(relocated_database, relocated_root) == report


@pytest.mark.parametrize("damage", ["missing", "same_size", "wrong_size", "directory", "fifo"])
def test_incomplete_artifacts_remain_visible(tmp_path: Path, damage: str) -> None:
    database, root, artifact = _fixture(tmp_path)
    artifact.unlink()
    if damage == "same_size":
        artifact.write_bytes(b"x" * len(CONTENT))
    elif damage == "wrong_size":
        artifact.write_bytes(b"x")
    elif damage == "directory":
        artifact.mkdir()
    elif damage == "fifo":
        os.mkfifo(artifact)
    report = audit_provider_artifacts(database, root)
    assert report["registered_artifacts_verified"] is False
    assert report["registered_count"] == 1
    assert report["verified_count"] == 0
    assert _status(report) in {
        "missing_file", "content_mismatch", "size_mismatch", "not_regular_file",
        "unsafe_or_unreadable_file",
    }


@pytest.mark.parametrize("location", ["database", "root", "directory", "file"])
def test_rejects_symlink_components(tmp_path: Path, location: str) -> None:
    database, root, artifact = _fixture(tmp_path)
    original = {"database": database, "root": root, "directory": artifact.parent,
                "file": artifact}[location]
    moved = original.with_name(original.name + "-actual")
    original.rename(moved)
    original.symlink_to(moved, target_is_directory=moved.is_dir())
    report = audit_provider_artifacts(database, root)
    assert report["registered_artifacts_verified"] is False
    if location == "database":
        assert report["error_code"] == "registry_unreadable"


@pytest.mark.parametrize(
    "key", ["../../outside", "/private/outside", "token=synthetic-redaction-sentinel"]
)
def test_untrusted_paths_are_never_opened_or_rendered(tmp_path: Path, key: str) -> None:
    database, root, _ = _fixture(tmp_path)
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE provider_artifacts SET storage_key = ?", (key,))
    report = audit_provider_artifacts(database, root)
    assert _status(report) == "invalid_storage_key"
    assert key not in json.dumps(report)


def test_blob_metadata_is_invalid_not_a_crash(tmp_path: Path) -> None:
    database, root, _ = _fixture(tmp_path)
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE provider_artifacts SET content_hash = ?", (b"invalid",))
    assert _status(audit_provider_artifacts(database, root)) == "invalid_metadata"


def test_record_and_byte_limits_fail_closed(tmp_path: Path) -> None:
    database, root, _ = _fixture(tmp_path)
    for limits in ({"max_file_bytes": 1}, {"max_total_bytes": 1}):
        assert _status(audit_provider_artifacts(database, root, **limits)) == "byte_limit_exceeded"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO provider_artifacts SELECT ?, content_hash, media_type, byte_size, "
            "storage_key FROM provider_artifacts", ("b" * 64,),
        )
    report = audit_provider_artifacts(database, root, max_records=1)
    assert report["error_code"] == "record_limit_exceeded"
    assert report["registry_scan_complete"] is False
    assert report["registered_artifacts_verified"] is False
    partial = audit_provider_artifacts(database, root, max_total_bytes=len(CONTENT))
    assert partial["registered_count"] == 2
    assert partial["verified_count"] == 1
    assert partial["registered_artifacts_verified"] is False


@pytest.mark.parametrize("value", [0, -1, True])
def test_invalid_limits_rejected(tmp_path: Path, value: int) -> None:
    with pytest.raises(ValueError, match="positive integers"):
        audit_provider_artifacts(tmp_path / "missing", tmp_path, max_records=value)


def test_missing_database_never_created(tmp_path: Path) -> None:
    database = tmp_path / "missing.sqlite3"
    report = audit_provider_artifacts(database, tmp_path)
    assert report["error_code"] == "registry_unreadable"
    assert not database.exists()


def test_empty_real_registry_is_not_recovery_approval(tmp_path: Path) -> None:
    database = tmp_path / "current.sqlite3"
    SQLiteStore(database).initialize()
    before = database.read_bytes()
    report = audit_provider_artifacts(database, tmp_path)
    assert report["registry_scan_complete"] is True
    assert report["registered_count"] == 0
    assert report["registered_artifacts_verified"] is False
    assert database.read_bytes() == before


def test_cli_passes_and_wrong_root_fails_without_writes(tmp_path: Path) -> None:
    database, root, _ = _fixture(tmp_path)
    command = [sys.executable, str(ROOT / "scripts/audit_provider_artifacts.py"),
               "--database", str(database), "--artifact-root"]
    passed = subprocess.run([*command, str(root)], capture_output=True, text=True, check=False)
    failed = subprocess.run(
        [*command, str(tmp_path / "wrong")], capture_output=True, text=True, check=False
    )
    assert passed.returncode == 0
    assert json.loads(passed.stdout)["registered_artifacts_verified"] is True
    assert failed.returncode == 2
    assert json.loads(failed.stdout)["registered_artifacts_verified"] is False
    assert not (tmp_path / "wrong").exists()
