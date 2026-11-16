"""Bounded read-only disk preflight, not a reservation, quota or capture authority."""

import json
import os
import stat
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from tong_quant.data.storage.artifact_audit import _open_without_links
from tong_quant.domain.models import require_timezone
from tong_quant.version import ARTIFACT_CAPACITY_VERSION


@dataclass(frozen=True, slots=True)
class ArtifactCapacityPolicy:
    maximum_artifact_bytes: int
    maximum_retained_bytes: int
    minimum_free_bytes: int
    staging_headroom_bytes: int
    maximum_scan_entries: int = 10_000
    maximum_depth: int = 16

    def __post_init__(self) -> None:
        if any(type(value) is not int or not 0 < value <= 2**63 - 1
               for value in asdict(self).values()):
            raise ValueError("capacity limits must be positive bounded integers")
        if (
            self.maximum_artifact_bytes > self.maximum_retained_bytes
            or self.maximum_scan_entries > 100_000
            or self.maximum_depth > 32
        ):
            raise ValueError("capacity policy exceeds supported bounds")


class _Blocked(ValueError):
    """Only fixed internal codes may cross this exception boundary."""


@dataclass(slots=True)
class _Inventory:
    entries: int = 0
    files: int = 0
    directories: int = 0
    logical_bytes: int = 0
    records: list[tuple[object, ...]] = field(default_factory=list)


def _metadata(value: os.stat_result) -> tuple[int, ...]:
    return (value.st_dev, value.st_ino, value.st_mode, value.st_size,
            value.st_mtime_ns, value.st_ctime_ns, value.st_nlink)


def _space(fd: int) -> int:
    value = os.fstatvfs(fd)
    if (type(value.f_bavail) is not int or type(value.f_frsize) is not int
            or value.f_bavail < 0 or value.f_frsize <= 0):
        raise _Blocked("SPACE_UNKNOWN")
    return value.f_bavail * value.f_frsize


def _scan(
    fd: int, *, policy: ArtifactCapacityPolicy, inventory: _Inventory,
    device: int, depth: int, relative: bytes,
) -> None:
    before = os.fstat(fd)
    if not stat.S_ISDIR(before.st_mode) or before.st_dev != device:
        raise _Blocked("CROSS_DEVICE_OR_INVALID_DIRECTORY")
    observed: list[tuple[str, tuple[int, ...]]] = []
    with os.scandir(fd) as iterator:
        for entry in iterator:
            if inventory.entries >= policy.maximum_scan_entries:
                raise _Blocked("SCAN_ENTRY_LIMIT")
            inventory.entries += 1
            metadata = entry.stat(follow_symlinks=False)
            if metadata.st_dev != device:
                raise _Blocked("CROSS_DEVICE_ENTRY")
            identity = _metadata(metadata)
            reference = relative + b"/" + os.fsencode(entry.name)
            inventory.records.append((sha256(reference).hexdigest(), *identity))
            observed.append((entry.name, identity))
            if stat.S_ISDIR(metadata.st_mode):
                inventory.directories += 1
                if depth >= policy.maximum_depth:
                    raise _Blocked("SCAN_DEPTH_LIMIT")
                child = os.open(
                    entry.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK,
                    dir_fd=fd,
                )
                try:
                    if _metadata(os.fstat(child)) != identity:
                        raise _Blocked("SCAN_CHANGED")
                    _scan(child, policy=policy, inventory=inventory, device=device,
                          depth=depth + 1, relative=reference)
                finally:
                    os.close(child)
            elif stat.S_ISREG(metadata.st_mode) and metadata.st_size >= 0:
                inventory.files += 1
                # Count every name conservatively, even hard links and temporary files.
                inventory.logical_bytes += metadata.st_size
            else:
                raise _Blocked("UNSAFE_ENTRY")
    for name, identity in observed:
        if _metadata(os.stat(name, dir_fd=fd, follow_symlinks=False)) != identity:
            raise _Blocked("SCAN_CHANGED")
    if _metadata(os.fstat(fd)) != _metadata(before):
        raise _Blocked("SCAN_CHANGED")


def _hash(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             allow_nan=False).encode()).hexdigest()


def inspect_artifact_capacity(
    artifact_root: Path,
    *,
    policy: ArtifactCapacityPolicy,
    planned_artifact_bytes: int,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> dict[str, Any]:
    """Observe an existing single-volume root without opening file contents or writing.

    A planned byte bound is caller-declared, not a measured future download size.
    Passing this diagnostic does not reserve space or constrain existing writers.
    """
    if not isinstance(policy, ArtifactCapacityPolicy):
        raise ValueError("explicit capacity policy is required")
    policy.__post_init__()
    if type(planned_artifact_bytes) is not int or not 0 < planned_artifact_bytes <= 2**63 - 1:
        raise ValueError("planned artifact bytes must be a positive bounded integer")
    started = clock()
    require_timezone(started, "capacity inspection timestamp")
    inventory = _Inventory()
    report: dict[str, Any] = {
        "model_version": ARTIFACT_CAPACITY_VERSION,
        "inspection_started_at": started.astimezone(UTC).isoformat(),
        "policy": asdict(policy),
        "policy_hash": _hash({"model_version": ARTIFACT_CAPACITY_VERSION, **asdict(policy)}),
        "planned_artifact_bytes": planned_artifact_bytes,
        "status": "UNKNOWN",
        "reason_codes": [],
        "scan_complete": False,
        "retained_logical_bytes": None,
        "projected_retained_logical_bytes": None,
        "available_free_bytes": None,
        "required_free_bytes": (
            planned_artifact_bytes + policy.staging_headroom_bytes + policy.minimum_free_bytes
        ),
        "inventory_hash": None,
        "root_reference_hash": None,
        "space_reserved": False,
        "quota_enforced": False,
        "collection_authorized": False,
        "research_refresh_authorized": False,
        "execution_authorized": False,
        "limitations": [
            "Current filesystem observation, not a historical or atomic storage snapshot.",
            "All regular names count: registered, unregistered, temporary and hard-linked files.",
            "Logical file lengths are not physical blocks, metadata cost or database/WAL usage.",
            "No content, provider truth, PIT quality, encryption or write permission verified.",
            "Planned bytes/headroom do not bound transport or other concurrent writers.",
            "No reservation, enforced quota, garbage collection, checkpoint or capture activation.",
        ],
    }
    try:
        if not all(hasattr(os, name) for name in (
            "O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK", "fstatvfs",
        )):
            raise _Blocked("PLATFORM_UNSUPPORTED")
        path = artifact_root.expanduser().absolute()
        root = _open_without_links(path, directory=True)
        try:
            before = os.fstat(root)
            report["root_reference_hash"] = _hash(_metadata(before))
            free_before = _space(root)
            _scan(root, policy=policy, inventory=inventory, device=before.st_dev,
                  depth=0, relative=b"")
            free_after = _space(root)
            # Re-open through the no-follow chain to detect a moved/replaced root.
            again = _open_without_links(path, directory=True)
            try:
                if _metadata(os.fstat(again)) != _metadata(before):
                    raise _Blocked("SCAN_CHANGED")
            finally:
                os.close(again)
        finally:
            os.close(root)
        projected = inventory.logical_bytes + planned_artifact_bytes
        reasons = []
        if planned_artifact_bytes > policy.maximum_artifact_bytes:
            reasons.append("PLANNED_ARTIFACT_LIMIT")
        if projected > policy.maximum_retained_bytes:
            reasons.append("RETAINED_BUDGET_LIMIT")
        free = min(free_before, free_after)
        if free < report["required_free_bytes"]:
            reasons.append("FREE_SPACE_LIMIT")
        report.update(
            status="BLOCKED" if reasons else "WITHIN_DECLARED_LIMITS",
            reason_codes=reasons, scan_complete=True,
            retained_logical_bytes=inventory.logical_bytes,
            projected_retained_logical_bytes=projected,
            available_free_bytes=free,
            inventory_hash=_hash({"root": report["root_reference_hash"],
                                  "entries": sorted(inventory.records)}),
        )
    except _Blocked as error:
        report.update(status="BLOCKED", reason_codes=[str(error)])
    except (OSError, ValueError, RuntimeError):
        # Do not render exception strings, file names or local paths.
        report.update(status="UNKNOWN", reason_codes=["ROOT_OR_ENTRY_UNREADABLE"])
    report.update(
        observed_entries=inventory.entries, observed_regular_files=inventory.files,
        observed_subdirectories=inventory.directories,
        observed_logical_file_bytes=inventory.logical_bytes,
    )
    finished = clock()
    require_timezone(finished, "capacity inspection completion")
    if finished.astimezone(UTC) < started.astimezone(UTC):
        raise ValueError("capacity clock moved backwards")
    report["inspection_completed_at"] = finished.astimezone(UTC).isoformat()
    report["report_hash"] = _hash(report)
    return report
