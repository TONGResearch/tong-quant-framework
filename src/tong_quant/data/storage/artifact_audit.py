"""Read-only verification of registered provider bytes, not a recovery approval."""

import json
import os
import sqlite3
import stat
from contextlib import ExitStack, closing
from hashlib import sha256
from pathlib import Path

from tong_quant.version import ARTIFACT_AUDIT_VERSION


def audit_provider_artifacts(
    database_path: Path,
    artifact_root: Path,
    *,
    max_records: int = 10_000,
    max_file_bytes: int = 64 * 1024 * 1024,
    max_total_bytes: int = 512 * 1024 * 1024,
) -> dict[str, object]:
    """Audit one registry read snapshot; never initialize, repair, or copy data."""
    for limit in (max_records, max_file_bytes, max_total_bytes):
        if type(limit) is not int or limit < 1:
            raise ValueError("artifact audit limits must be positive integers")
    try:
        database = database_path.expanduser().absolute()
        descriptor = _open_without_links(database)
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise ValueError("database must be a regular file")
        finally:
            os.close(descriptor)
        with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as connection:
            connection.execute("PRAGMA query_only = ON")
            connection.execute("BEGIN")
            rows = connection.execute(
                """SELECT artifact_id, content_hash, media_type, byte_size, storage_key
                   FROM provider_artifacts ORDER BY artifact_id LIMIT ?""",
                (max_records + 1,),
            ).fetchall()
    except (OSError, ValueError, sqlite3.Error):
        return _report((), "registry_unreadable", "", False)
    return _audit_rows(
        rows, artifact_root, max_records=max_records,
        max_file_bytes=max_file_bytes, max_total_bytes=max_total_bytes,
    )


def audit_provider_artifact_selection(
    rows: tuple[tuple[object, ...], ...],
    artifact_root: Path,
    *,
    max_records: int = 10_000,
    max_file_bytes: int = 64 * 1024 * 1024,
    max_total_bytes: int = 512 * 1024 * 1024,
) -> dict[str, object]:
    """Verify explicit caller-selected registry rows, NOT the whole registry."""
    for limit in (max_records, max_file_bytes, max_total_bytes):
        if type(limit) is not int or limit < 1:
            raise ValueError("artifact audit limits must be positive integers")
    result = _audit_rows(
        rows, artifact_root, max_records=max_records,
        max_file_bytes=max_file_bytes, max_total_bytes=max_total_bytes,
    )
    result.pop("report_hash")
    result["registry_scope"] = "caller_selected_rows_only"
    result["selection_hash"] = result.pop("registry_hash")
    result["selection_scan_complete"] = result.pop("registry_scan_complete")
    result["selected_count"] = result.pop("registered_count")
    result["selected_artifacts_verified"] = result.pop("registered_artifacts_verified")
    result["report_hash"] = sha256(
        json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return result


def _audit_rows(
    rows: list[tuple[object, ...]] | tuple[tuple[object, ...], ...],
    artifact_root: Path,
    *,
    max_records: int,
    max_file_bytes: int,
    max_total_bytes: int,
) -> dict[str, object]:
    if len(rows) > max_records:
        return _report((), "record_limit_exceeded", "", False)

    entries: list[dict[str, object]] = []
    registry_hash = sha256()
    remaining = max_total_bytes
    for row in rows:
        # Hash references, not paths, source URLs, subjects or raw payloads.
        encoded = json.dumps(
            row, separators=(",", ":"), ensure_ascii=True,
            default=lambda value: {"blob_sha256": sha256(value).hexdigest()},
        ).encode()
        reference_hash = sha256(encoded).hexdigest()
        registry_hash.update(bytes.fromhex(reference_hash))
        _, content_hash, media_type, size, key = row
        code = "invalid_metadata"
        verified_bytes = 0
        if (
            isinstance(content_hash, str)
            and len(content_hash) == 64
            and all(char in "0123456789abcdef" for char in content_hash)
            and isinstance(media_type, str)
            and type(size) is int
            and size > 0
        ):
            extension = ".pdf" if media_type.split(";", 1)[0].strip().lower() == (
                "application/pdf"
            ) else ".bin"
            expected_key = f"sha256/{content_hash[:2]}/{content_hash}{extension}"
            if key != expected_key:
                code = "invalid_storage_key"
            elif size > max_file_bytes or size > remaining:
                code = "byte_limit_exceeded"
            else:
                remaining -= size
                code = _verify_file(artifact_root.expanduser().absolute() / key, size, content_hash)
                if code == "verified":
                    verified_bytes = size
        entries.append({
            "reference_hash": reference_hash,
            "status": code,
            "verified_bytes": verified_bytes,
        })
    return _report(tuple(entries), "", registry_hash.hexdigest(), True)


def _open_without_links(path: Path, *, directory: bool = False) -> int:
    """Anchor every component with no-follow directory descriptors (POSIX)."""
    with ExitStack() as stack:
        parent = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        stack.callback(os.close, parent)
        for part in path.parts[1:-1]:
            if part in {".", ".."}:
                raise ValueError("path traversal is forbidden")
            parent = os.open(
                part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent
            )
            stack.callback(os.close, parent)
        if path.name in {"", ".", ".."}:
            raise ValueError("file path is required")
        return os.open(
            path.name,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | (os.O_DIRECTORY if directory else 0),
            dir_fd=parent,
        )


def _verify_file(path: Path, expected_size: int, expected_hash: str) -> str:
    try:
        with os.fdopen(_open_without_links(path), "rb") as handle:
            before = os.fstat(handle.fileno())
            if not stat.S_ISREG(before.st_mode):
                return "not_regular_file"
            if before.st_size != expected_size:
                return "size_mismatch"
            digest = sha256()
            remaining = expected_size + 1
            while remaining:
                chunk = handle.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                digest.update(chunk)
                remaining -= len(chunk)
            after = os.fstat(handle.fileno())
            if (
                before.st_size, before.st_mtime_ns, before.st_ctime_ns
            ) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                return "file_changed_during_audit"
            if remaining != 1 or digest.hexdigest() != expected_hash:
                return "content_mismatch"
            return "verified"
    except FileNotFoundError:
        return "missing_file"
    except (OSError, ValueError):
        return "unsafe_or_unreadable_file"


def _report(
    entries: tuple[dict[str, object], ...],
    error_code: str,
    registry_hash: str,
    registry_scan_complete: bool,
) -> dict[str, object]:
    document: dict[str, object] = {
        "model_version": ARTIFACT_AUDIT_VERSION,
        "registry_hash": registry_hash,
        "registry_scan_complete": registry_scan_complete,
        "registered_count": len(entries),
        "verified_count": sum(item["status"] == "verified" for item in entries),
        "registered_artifacts_verified": bool(entries) and not error_code and all(
            item["status"] == "verified" for item in entries
        ),
        "error_code": error_code,
        "entries": list(entries),
        "limitations": [
            "Registered provider artifacts only; unregistered files are not inventoried.",
            "No database integrity, full database content or backup/restore verification.",
            "Registry snapshot and file reads are not one atomic cross-store snapshot.",
            "Quiesce writers and repeat on the restored destination before recovery review.",
            "Byte identity does not authenticate provider content, PIT quality or encryption.",
            "No readiness or execution authorization is granted.",
        ],
    }
    document["report_hash"] = sha256(
        json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return document
