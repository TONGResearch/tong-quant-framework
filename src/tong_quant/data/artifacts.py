import os
import tempfile
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from tong_quant.data.providers.contracts import ProviderArtifact


@dataclass(frozen=True, slots=True)
class StoredProviderArtifact:
    artifact: ProviderArtifact
    storage_key: str
    created: bool

    def __post_init__(self) -> None:
        key = Path(self.storage_key)
        if key.is_absolute() or ".." in key.parts or not self.storage_key.strip():
            raise ValueError("artifact storage keys must be safe relative paths")


class ProviderArtifactStore(Protocol):
    def put(self, artifact: ProviderArtifact) -> StoredProviderArtifact: ...

    def discard(self, stored: StoredProviderArtifact) -> None: ...


@dataclass(frozen=True, slots=True)
class FileSystemArtifactStore:
    root: Path

    def put(self, artifact: ProviderArtifact) -> StoredProviderArtifact:
        root = self.root.expanduser()
        if root.is_symlink():
            raise ValueError("artifact root must not be a symbolic link")
        root.mkdir(parents=True, exist_ok=True)
        extension = _extension(artifact.media_type)
        storage_key = (
            f"sha256/{artifact.content_hash[:2]}/{artifact.content_hash}{extension}"
        )
        destination = root / storage_key
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.is_symlink():
            raise ValueError("artifact destination must not be a symbolic link")
        if destination.exists():
            _verify_existing(destination, artifact)
            return StoredProviderArtifact(artifact, storage_key, created=False)

        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{artifact.content_hash}.",
            suffix=".tmp",
            dir=destination.parent,
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as artifact_file:
                artifact_file.write(artifact.content)
                artifact_file.flush()
                os.fsync(artifact_file.fileno())
            temporary.chmod(0o600)
            try:
                os.link(temporary, destination)
                created = True
            except FileExistsError:
                _verify_existing(destination, artifact)
                created = False
            return StoredProviderArtifact(artifact, storage_key, created=created)
        finally:
            temporary.unlink(missing_ok=True)

    def discard(self, stored: StoredProviderArtifact) -> None:
        if not stored.created:
            return
        destination = self.root.expanduser() / stored.storage_key
        if destination.is_symlink():
            raise ValueError("artifact cleanup refuses symbolic links")
        if destination.exists() and _file_hash(destination) == stored.artifact.content_hash:
            destination.unlink()


def _verify_existing(path: Path, artifact: ProviderArtifact) -> None:
    if not path.is_file() or _file_hash(path) != artifact.content_hash:
        raise ValueError("content-addressed artifact path contains different bytes")
    path.chmod(0o600)


def _file_hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as artifact_file:
        for chunk in iter(lambda: artifact_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _extension(media_type: str) -> str:
    normalized = media_type.split(";", 1)[0].strip().lower()
    return ".pdf" if normalized == "application/pdf" else ".bin"


__all__ = [
    "FileSystemArtifactStore",
    "ProviderArtifactStore",
    "StoredProviderArtifact",
]
