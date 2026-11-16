"""Local cooperative locking with prepared synthetic files; no collector integration."""

import errno
import os
import pickle
import selectors
import subprocess
import sys
from contextlib import contextmanager, suppress
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from tong_quant.data import resource_ownership as ownership
from tong_quant.data.resource_ownership import (
    ResourceLockError,
    ResourceLockErrorCode,
    hold_resource_lock,
    inspect_prepared_lock,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def prepared(tmp_path):
    directory = tmp_path / "private-coordinator"
    directory.mkdir(mode=0o700)
    path = directory / "prepared-empty.lock"
    path.touch(mode=0o600)
    return inspect_prepared_lock(path)


def test_lifetime_preserves_bytes_inode_and_closes_private_descriptor(prepared):
    assert prepared == inspect_prepared_lock(prepared.path)
    assert str(prepared.path) not in repr(prepared)
    with hold_resource_lock(prepared) as held:
        assert held.identity_hash == prepared.identity_hash
        assert held.validate() is None
        descriptor = held._state.descriptor
        assert os.get_inheritable(descriptor) is False
        with pytest.raises(TypeError):
            pickle.dumps(held)
    with pytest.raises(ResourceLockError) as error:
        held.validate()
    assert error.value.code is ResourceLockErrorCode.NOT_HELD
    with pytest.raises(OSError) as closed:
        os.fstat(descriptor)
    assert closed.value.errno == errno.EBADF
    assert prepared.path.read_bytes() == b""
    assert prepared == inspect_prepared_lock(prepared.path)
    assert not ownership._states


def test_same_process_nested_acquisition_is_busy_not_recursive(prepared):
    with hold_resource_lock(prepared) as held:
        with pytest.raises(ResourceLockError) as error, hold_resource_lock(prepared):
            pytest.fail("an independent open description must not share ownership")
        assert error.value.code is ResourceLockErrorCode.BUSY
        assert held.validate() is None
    with hold_resource_lock(prepared) as next_owner:
        assert next_owner.validate() is None


def test_body_error_releases_without_deleting_the_coordinator(prepared):
    with pytest.raises(ValueError, match="synthetic body"), hold_resource_lock(prepared):
        raise ValueError("synthetic body")
    assert prepared.path.exists()
    with hold_resource_lock(prepared) as held:
        assert held.validate() is None


@pytest.mark.parametrize("kind", ["body", "hardlink", "symlink", "directory", "fifo",
                                "mode", "parent_mode"])
def test_unsafe_preparation_is_not_repaired_or_created(prepared, kind):
    path = prepared.path
    if kind == "body":
        path.write_bytes(b"password=synthetic-sentinel")
    elif kind == "hardlink":
        os.link(path, path.parent / "second-name")
    elif kind == "symlink":
        path.rename(path.parent / "original")
        path.symlink_to(path.parent / "original")
    elif kind == "directory":
        path.unlink()
        path.mkdir(mode=0o700)
    elif kind == "fifo":
        path.unlink()
        os.mkfifo(path, mode=0o600)
    elif kind == "mode":
        path.chmod(0o644)
    else:
        path.parent.chmod(0o755)
    with pytest.raises(ResourceLockError) as error:
        inspect_prepared_lock(path)
    assert "synthetic-sentinel" not in str(error.value)
    with pytest.raises(ResourceLockError), hold_resource_lock(prepared):
        pytest.fail("unsafe file must not be silently repaired")


def test_parent_symlink_and_missing_file_do_not_create_anything(prepared):
    alias = prepared.path.parent.parent / "coordinator-alias"
    alias.symlink_to(prepared.path.parent, target_is_directory=True)
    with pytest.raises(ResourceLockError):
        inspect_prepared_lock(alias / prepared.path.name)
    prepared.path.unlink()
    with pytest.raises(ResourceLockError), hold_resource_lock(prepared):
        pytest.fail("missing coordinator must not be recreated")
    assert not prepared.path.exists()


def test_replaced_inode_is_rejected_without_repinning(prepared):
    original = prepared.path.parent / "original-retained.lock"
    prepared.path.rename(original)
    prepared.path.touch(mode=0o600)
    with pytest.raises(ResourceLockError) as error, hold_resource_lock(prepared):
        pytest.fail("replacement is not the approved inode")
    assert error.value.code is ResourceLockErrorCode.IDENTITY_CHANGED
    assert original.stat().st_ino == prepared.inode


def test_validation_failure_is_latched_until_context_exit(prepared):
    with hold_resource_lock(prepared) as held:
        prepared.path.chmod(0o644)
        with pytest.raises(ResourceLockError):
            held.validate()
        prepared.path.chmod(0o600)
        with pytest.raises(ResourceLockError) as error:
            held.validate()
        assert error.value.code is ResourceLockErrorCode.NOT_HELD
        with pytest.raises(ResourceLockError) as busy, hold_resource_lock(prepared):
            pytest.fail("invalidating the token must not release ownership early")
        assert busy.value.code is ResourceLockErrorCode.BUSY
    with hold_resource_lock(prepared) as new_owner:
        assert new_owner.validate() is None


def test_unlink_while_held_stays_missing_and_cannot_be_reacquired(prepared):
    with hold_resource_lock(prepared) as held:
        prepared.path.unlink()
        with pytest.raises(ResourceLockError):
            held.validate()
        with pytest.raises(ResourceLockError), hold_resource_lock(prepared):
            pytest.fail("never recreate an unlinked coordinator")
    assert not prepared.path.exists()


def test_pins_are_immutable_and_revalidated(prepared):
    with pytest.raises(FrozenInstanceError):
        prepared.inode = 0
    with pytest.raises(ResourceLockError):
        replace(prepared, inode=0)
    with pytest.raises(ResourceLockError):
        replace(prepared, model_version="unrecognized")
    with pytest.raises(ResourceLockError), hold_resource_lock(None):
        pytest.fail("untyped pin must be rejected")


def test_unsupported_platform_does_not_fall_back_to_a_thread_lock(prepared, monkeypatch):
    monkeypatch.setattr(ownership, "_fcntl", None)
    with pytest.raises(ResourceLockError) as error, hold_resource_lock(prepared):
        pytest.fail("unsupported platform must stay blocked")
    assert error.value.code is ResourceLockErrorCode.UNSUPPORTED


def test_foreign_owner_is_not_admitted(prepared, monkeypatch):
    uid = os.geteuid()
    monkeypatch.setattr(ownership.os, "geteuid", lambda: uid + 1)
    with pytest.raises(ResourceLockError) as error:
        inspect_prepared_lock(prepared.path)
    assert error.value.code is ResourceLockErrorCode.UNSAFE


def test_open_permission_error_is_unavailable_not_busy_and_never_echoed(prepared, monkeypatch):
    def denied(*args, **kwargs):
        raise PermissionError("password=synthetic-secret-sentinel")

    monkeypatch.setattr(ownership, "_open_checked", denied)
    with pytest.raises(ResourceLockError) as error, hold_resource_lock(prepared):
        pytest.fail("opening failure is not a contention observation")
    assert error.value.code is ResourceLockErrorCode.UNAVAILABLE
    assert "secret-sentinel" not in str(error.value)
    assert not ownership._states


def test_release_failure_is_explicit_not_a_claim_of_free_ownership(prepared, monkeypatch):
    monkeypatch.setattr(ownership, "_release_uncertain", False)
    manager = hold_resource_lock(prepared)
    held = manager.__enter__()
    descriptor = held._state.descriptor
    original = os.close

    def uncertain(fd):
        if fd == descriptor:
            raise OSError("synthetic-secret-sentinel")
        return original(fd)

    try:
        with monkeypatch.context() as local:
            local.setattr(ownership.os, "close", uncertain)
            with pytest.raises(ResourceLockError) as error:
                manager.__exit__(None, None, None)
        assert error.value.code is ResourceLockErrorCode.RELEASE_UNCERTAIN
        assert "secret-sentinel" not in str(error.value)
        with pytest.raises(ResourceLockError) as blocked, hold_resource_lock(prepared):
            pytest.fail("uncertain release must quarantine this process")
        assert blocked.value.code is ResourceLockErrorCode.RELEASE_UNCERTAIN
    finally:
        original(descriptor)
    with pytest.raises(ResourceLockError) as blocked, hold_resource_lock(prepared):
        pytest.fail("manual cleanup in a test cannot clear the production quarantine")
    assert blocked.value.code is ResourceLockErrorCode.RELEASE_UNCERTAIN
    with _other_holder(prepared):
        pass


_HOLDER = """
import sys
from pathlib import Path
from tong_quant.data.resource_ownership import inspect_prepared_lock, hold_resource_lock
pin = inspect_prepared_lock(Path(sys.argv[1]))
assert pin.identity_hash == sys.argv[2]
with hold_resource_lock(pin):
    print('HELD', flush=True)
    sys.stdin.readline()
"""


@contextmanager
def _other_holder(prepared):
    process = subprocess.Popen(
        [sys.executable, "-u", "-c", _HOLDER, str(prepared.path), prepared.identity_hash],
        cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True,
    )
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            assert selector.select(timeout=20), "holder did not reach the bounded handshake"
        assert process.stdout.readline().strip() == "HELD"
        yield process
    finally:
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=20)


def test_independent_processes_exclude_each_other_and_release_normally(prepared):
    with _other_holder(prepared) as process:
        with pytest.raises(ResourceLockError) as error, hold_resource_lock(prepared):
            pytest.fail("another process already owns this inode")
        assert error.value.code is ResourceLockErrorCode.BUSY
        process.stdin.write("release\n")
        process.stdin.flush()
        assert process.wait(timeout=20) == 0
    with hold_resource_lock(prepared) as held:
        assert held.validate() is None


def test_os_releases_after_holder_crash_without_deleting_or_repinning(prepared):
    with _other_holder(prepared) as process:
        process.kill()
        process.wait(timeout=20)
    assert prepared == inspect_prepared_lock(prepared.path)
    with hold_resource_lock(prepared) as held:
        assert held.validate() is None


@pytest.mark.skipif(not hasattr(os, "fork"), reason="local POSIX fork contract")
def test_fork_child_closes_inherited_lock_and_cannot_unlock_parent(prepared):
    manager = hold_resource_lock(prepared)
    held = manager.__enter__()
    descriptor = held._state.descriptor
    read_fd, write_fd = os.pipe()
    child: int | None = None
    reaped = False
    try:
        child = os.fork()
        if child == 0:
            os.close(read_fd)
            try:
                try:
                    held.validate()
                except ResourceLockError as error:
                    assert error.code is ResourceLockErrorCode.NOT_HELD
                else:
                    raise AssertionError("child inherited a usable token")
                try:
                    os.fstat(descriptor)
                except OSError as error:
                    assert error.errno == errno.EBADF
                else:
                    raise AssertionError("child retained the parent's coordinator descriptor")
                manager.__exit__(None, None, None)
                os.write(write_fd, b"OK")
                os._exit(0)
            except BaseException:
                os.write(write_fd, b"FAIL")
                os._exit(1)
        os.close(write_fd)
        write_fd = -1
        with selectors.DefaultSelector() as selector:
            selector.register(read_fd, selectors.EVENT_READ)
            assert selector.select(timeout=20), "fork child handshake timed out"
        assert os.read(read_fd, 4) == b"OK"
        _, status = os.waitpid(child, 0)
        reaped = True
        assert os.waitstatus_to_exitcode(status) == 0
        with pytest.raises(ResourceLockError) as error, hold_resource_lock(prepared):
            pytest.fail("child exit must not unlock the parent's description")
        assert error.value.code is ResourceLockErrorCode.BUSY
        assert held.validate() is None
    finally:
        if child not in {None, 0} and not reaped:
            with suppress(ProcessLookupError):
                os.kill(child, 9)
            os.waitpid(child, 0)
        os.close(read_fd)
        if write_fd >= 0:
            os.close(write_fd)
        manager.__exit__(None, None, None)
    with hold_resource_lock(prepared) as after:
        assert after.validate() is None
