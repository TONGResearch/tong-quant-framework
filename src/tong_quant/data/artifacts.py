import os
import tempfile
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import ClassVar, Protocol

from tong_quant.data.providers.contracts import ProviderArtifact
from tong_quant.version import ARTIFACT_STORAGE_VERSION


@dataclass(frozen=True, slots=True)
class StoredProviderArtifact:
    """A publication receipt; created is not an exclusive ownership or deletion lease."""

    artifact: ProviderArtifact
    storage_key: str
    created: bool

    def __post_init__(self) -> None:
        key = Path(self.storage_key)
        if key.is_absolute() or ".." in key.parts or not self.storage_key.strip():
            raise ValueError("artifact storage keys must be safe relative paths")


class ProviderArtifactStore(Protocol):
    def put(self, artifact: ProviderArtifact) -> StoredProviderArtifact: ...

    def discard(self, stored: StoredProviderArtifact) -> None:
        """Abandon the attempt without deleting bytes other writers may have adopted."""
        ...


@dataclass(frozen=True, slots=True)
class FileSystemArtifactStore:
    """Content-addressed bytes are shared; rollback never proves exclusive ownership."""

    model_version: ClassVar[str] = ARTIFACT_STORAGE_VERSION
    root: Path

    def read_content(self, content_hash: str, media_type: str, *, max_bytes: int) -> bytes:
        if len(content_hash) != 64 or any(c not in "0123456789abcdef" for c in content_hash):
            raise ValueError("artifact read requires a lowercase SHA-256 digest")
        if type(max_bytes) is not int or not 0 < max_bytes <= 50 * 1024 * 1024:
            raise ValueError("artifact read requires a bounded size limit")
        root = self.root.expanduser()
        destination = root / "sha256" / content_hash[:2] / (content_hash + _extension(media_type))
        if root.is_symlink() or destination.is_symlink():
            raise ValueError("artifact read refuses symbolic links")
        if not destination.resolve().is_relative_to(root.resolve()):
            raise ValueError("artifact read escapes storage root")
        with destination.open("rb") as handle:
            content = handle.read(max_bytes + 1)
        if len(content) > max_bytes or sha256(content).hexdigest() != content_hash:
            raise ValueError("artifact read failed size or content-hash verification")
        return content

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
        """Abandon this attempt, not shared bytes; reference-safe garbage collection is separate."""
        # Another process or database may have adopted even a newly created file.
        # Keep unregistered content for audited reconciliation; never delete on rollback.
        return None


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
