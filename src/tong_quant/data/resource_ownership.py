"""Cooperative ownership of an explicitly prepared local lock, not capture authority."""

import errno
import json
import os
import stat
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from types import ModuleType
from typing import Never

from tong_quant.data.storage.artifact_audit import _open_without_links
from tong_quant.version import RESOURCE_LOCK_VERSION

_fcntl: ModuleType | None
try:
    import fcntl as _platform_fcntl
except ImportError:
    _fcntl = None
else:
    _fcntl = _platform_fcntl

_release_uncertain = False


class ResourceLockErrorCode(StrEnum):
    UNSUPPORTED = "unsupported_platform"
    UNAVAILABLE = "lock_unavailable"
    UNSAFE = "unsafe_prepared_lock"
    IDENTITY_CHANGED = "lock_identity_changed"
    BUSY = "lock_busy"
    NOT_HELD = "lock_not_held"
    RELEASE_UNCERTAIN = "lock_release_uncertain"


class ResourceLockError(RuntimeError):
    def __init__(self, code: ResourceLockErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


@dataclass(frozen=True, slots=True)
class PreparedResourceLock:
    path: Path = field(repr=False)
    device: int
    inode: int
    parent_device: int
    parent_inode: int
    owner_uid: int
    model_version: str = RESOURCE_LOCK_VERSION

    def __post_init__(self) -> None:
        if (
            not isinstance(self.path, Path) or not self.path.is_absolute()
            or ".." in self.path.parts or self.path.name in {"", ".", ".."}
            or any(type(value) is not int or value < 0 for value in (
                self.device, self.inode, self.parent_device, self.parent_inode, self.owner_uid
            ))
            or self.inode == 0 or self.parent_inode == 0
            or self.model_version != RESOURCE_LOCK_VERSION
        ):
            raise ResourceLockError(ResourceLockErrorCode.UNSAFE)

    @property
    def identity_hash(self) -> str:
        return sha256(json.dumps({
            "model_version": self.model_version, "device": self.device, "inode": self.inode,
            "parent_device": self.parent_device, "parent_inode": self.parent_inode,
            "owner_uid": self.owner_uid,
        }, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _supported() -> None:
    if _release_uncertain:
        raise ResourceLockError(ResourceLockErrorCode.RELEASE_UNCERTAIN)
    if _fcntl is None or not all(hasattr(os, name) for name in (
        "O_NOFOLLOW", "O_DIRECTORY", "O_NONBLOCK", "geteuid", "register_at_fork",
    )):
        raise ResourceLockError(ResourceLockErrorCode.UNSUPPORTED)


def _safe_file(value: os.stat_result) -> None:
    if (
        not stat.S_ISREG(value.st_mode) or value.st_size != 0 or value.st_nlink != 1
        or stat.S_IMODE(value.st_mode) != 0o600 or value.st_uid != os.geteuid()
    ):
        raise ResourceLockError(ResourceLockErrorCode.UNSAFE)


def _open_checked(path: Path) -> tuple[int, PreparedResourceLock]:
    parent_fd = _open_without_links(path.parent, directory=True)
    parent: int | None = parent_fd
    descriptor: int | None = None
    try:
        directory = os.fstat(parent_fd)
        if (not stat.S_ISDIR(directory.st_mode) or directory.st_uid != os.geteuid()
                or stat.S_IMODE(directory.st_mode) != 0o700):
            raise ResourceLockError(ResourceLockErrorCode.UNSAFE)
        descriptor = os.open(
            path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd,
        )
        os.set_inheritable(descriptor, False)
        value = os.fstat(descriptor)
        _safe_file(value)
        pin = PreparedResourceLock(path, value.st_dev, value.st_ino,
                                   directory.st_dev, directory.st_ino, value.st_uid)
        parent = None
        os.close(parent_fd)
        result, descriptor = descriptor, None
        return result, pin
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if parent is not None:
            os.close(parent)


_registry_guard = threading.RLock()


def inspect_prepared_lock(path: Path) -> PreparedResourceLock:
    """Read pins from an existing private empty file; never create or replace it.

    This is explicit preparation for review, not an automatic re-pin on retry.
    """
    _supported()
    if not isinstance(path, Path):
        raise ResourceLockError(ResourceLockErrorCode.UNSAFE)
    try:
        with _registry_guard:
            _supported()
            descriptor, pin = _open_checked(path.expanduser().absolute())
            try:
                return pin
            finally:
                os.close(descriptor)
    except (OSError, ValueError):
        raise ResourceLockError(ResourceLockErrorCode.UNAVAILABLE) from None


@dataclass(slots=True, repr=False)
class _LockState:
    prepared: PreparedResourceLock
    owner_pid: int
    descriptor: int | None = None
    active: bool = False
    invalidated: bool = False


_states: dict[int, _LockState] = {}


def _close_state(state: _LockState) -> bool:
    global _release_uncertain
    descriptor, state.descriptor = state.descriptor, None
    state.active = False
    state.invalidated = True
    if descriptor is not None:
        try:
            # Close only: LOCK_UN in a fork child could unlock the parent's shared description.
            os.close(descriptor)
        except OSError:
            _release_uncertain = True
            return False
    return True


def _before_fork() -> None:
    _registry_guard.acquire()


def _after_parent() -> None:
    _registry_guard.release()


def _after_child() -> None:
    global _registry_guard
    for state in _states.values():
        _close_state(state)
    _states.clear()
    _registry_guard = threading.RLock()


if hasattr(os, "register_at_fork"):
    os.register_at_fork(before=_before_fork, after_in_parent=_after_parent,
                        after_in_child=_after_child)


@dataclass(frozen=True, slots=True, repr=False)
class HeldResourceLock:
    _state: _LockState

    @property
    def identity_hash(self) -> str:
        return self._state.prepared.identity_hash

    def __reduce__(self) -> Never:
        raise TypeError("held resource ownership cannot be transferred")

    def validate(self) -> None:
        """Check this process/session and pinned namespace; no resource or capture approval."""
        global _release_uncertain
        with _registry_guard:
            _supported()
            state = self._state
            if (not state.active or state.invalidated or state.owner_pid != os.getpid()
                    or state.descriptor is None):
                raise ResourceLockError(ResourceLockErrorCode.NOT_HELD)
            temporary: int | None = None
            try:
                _safe_file(os.fstat(state.descriptor))
                temporary, current = _open_checked(state.prepared.path)
                value = os.fstat(state.descriptor)
                if (current != state.prepared
                        or (value.st_dev, value.st_ino) != (current.device, current.inode)):
                    raise ResourceLockError(ResourceLockErrorCode.IDENTITY_CHANGED)
            except ResourceLockError:
                state.invalidated = True
                raise
            except (OSError, ValueError):
                state.invalidated = True
                raise ResourceLockError(ResourceLockErrorCode.UNAVAILABLE) from None
            finally:
                if temporary is not None:
                    try:
                        os.close(temporary)
                    except OSError:
                        state.invalidated = True
                        _release_uncertain = True
                        raise ResourceLockError(ResourceLockErrorCode.RELEASE_UNCERTAIN) from None


@contextmanager
def hold_resource_lock(prepared: PreparedResourceLock) -> Iterator[HeldResourceLock]:
    """Try exclusive OS advisory ownership of one pinned, existing local inode."""
    _supported()
    if not isinstance(prepared, PreparedResourceLock):
        raise ResourceLockError(ResourceLockErrorCode.UNSAFE)
    prepared.__post_init__()
    state = _LockState(prepared, os.getpid())
    try:
        with _registry_guard:
            _supported()
            _states[id(state)] = state
            try:
                state.descriptor, actual = _open_checked(prepared.path)
            except (OSError, ValueError):
                raise ResourceLockError(ResourceLockErrorCode.UNAVAILABLE) from None
            if state.owner_pid != os.getpid():
                raise ResourceLockError(ResourceLockErrorCode.NOT_HELD)
            if actual != prepared:
                raise ResourceLockError(ResourceLockErrorCode.IDENTITY_CHANGED)
            if _fcntl is None:
                raise ResourceLockError(ResourceLockErrorCode.UNSUPPORTED)
            try:
                _fcntl.flock(state.descriptor, _fcntl.LOCK_EX | _fcntl.LOCK_NB)
            except OSError as error:
                code = (ResourceLockErrorCode.BUSY if error.errno in {errno.EAGAIN, errno.EACCES}
                        else ResourceLockErrorCode.UNAVAILABLE)
                raise ResourceLockError(code) from None
            state.active = True
            held = HeldResourceLock(state)
            held.validate()
        yield held
    finally:
        with _registry_guard:
            _states.pop(id(state), None)
            if not _close_state(state):
                raise ResourceLockError(ResourceLockErrorCode.RELEASE_UNCERTAIN) from None
