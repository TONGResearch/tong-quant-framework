import json
import os
import shutil
import stat
import tempfile
import zipfile
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
    evaluate_provider_evidence_horizon,
    provider_evidence_horizon_json,
)
from tong_quant.domain.models import require_timezone
from tong_quant.version import PROVIDER_EVIDENCE_ARCHIVE_VERSION

_MAX_ARCHIVE_ENTRIES = 10_000
_MAX_UNCOMPRESSED_BYTES = 512 * 1024 * 1024


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
            expected_horizon = provider_evidence_horizon_json(
                evaluate_provider_evidence_horizon(bundle_document)
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
    "archive_provider_evidence_artifact",
    "provider_evidence_archive_manifest_json",
    "serialize_provider_evidence_archive_manifest",
    "verify_provider_evidence_archive",
]
