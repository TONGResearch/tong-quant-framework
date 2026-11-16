"""Synthetic read-only capacity observations, not enforced storage quota evidence."""

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from tong_quant.data import artifact_capacity as capacity

NOW = datetime(2026, 11, 4, tzinfo=UTC)
ROOT = Path(__file__).resolve().parents[1]
POLICY = capacity.ArtifactCapacityPolicy(100, 1000, 50, 20)


@pytest.fixture
def archive(tmp_path, monkeypatch):
    root = tmp_path / "private-artifact-root"
    root.mkdir()
    monkeypatch.setattr(capacity.os, "fstatvfs", lambda _: SimpleNamespace(
        f_bavail=1000, f_frsize=1))
    return root


def inspect(root, *, policy=POLICY, planned_artifact_bytes=100, **kwargs):
    return capacity.inspect_artifact_capacity(
        root, policy=policy, planned_artifact_bytes=planned_artifact_bytes,
        clock=kwargs.pop("clock", lambda: NOW), **kwargs,
    )


def test_empty_root_is_only_within_declared_limits_not_authorized(archive):
    report = inspect(archive)
    assert report["status"] == "WITHIN_DECLARED_LIMITS"
    assert report["retained_logical_bytes"] == 0
    assert report["projected_retained_logical_bytes"] == 100
    assert report["required_free_bytes"] == 170
    assert report["scan_complete"] is True
    assert all(report[key] is False for key in (
        "space_reserved", "quota_enforced", "collection_authorized",
        "research_refresh_authorized", "execution_authorized",
    ))
    assert str(archive) not in json.dumps(report)
    assert report == inspect(archive)
    assert report == inspect(archive, clock=lambda: NOW.astimezone(timezone(timedelta(hours=8))))


def test_every_file_name_counts_without_database_or_extension_filter(archive):
    registered = archive / "sha256" / "aa"
    registered.mkdir(parents=True)
    (registered / "original.bin").write_bytes(b"x" * 100)
    (registered / ".abandoned.tmp").write_bytes(b"y" * 40)
    (archive / "unregistered-secret-sentinel.pdf").write_bytes(b"z" * 20)
    os.link(registered / "original.bin", archive / "adopted-hardlink")
    report = inspect(archive)
    assert report["retained_logical_bytes"] == 260
    assert report["observed_regular_files"] == 4
    assert report["observed_subdirectories"] == 2
    assert report["observed_entries"] == 6
    assert "secret-sentinel" not in json.dumps(report)
    assert "original.bin" not in json.dumps(report)


def test_empty_roots_do_not_share_an_inventory_identity(archive):
    another = archive.parent / "different-root"
    another.mkdir()
    first, second = inspect(archive), inspect(another)
    assert first["retained_logical_bytes"] == second["retained_logical_bytes"] == 0
    assert first["root_reference_hash"] != second["root_reference_hash"]
    assert first["inventory_hash"] != second["inventory_hash"]
    assert str(another) not in json.dumps(second)


def test_parallel_preflights_cannot_reserve_joint_headroom(archive):
    (archive / "retained.bin").write_bytes(b"x" * 800)
    policy = replace(POLICY, maximum_retained_bytes=950)
    with ThreadPoolExecutor(max_workers=2) as pool:
        reports = list(pool.map(lambda _: inspect(archive, policy=policy), range(2)))
    assert all(report["status"] == "WITHIN_DECLARED_LIMITS" for report in reports)
    assert all(report["projected_retained_logical_bytes"] == 900 for report in reports)
    assert policy.maximum_retained_bytes < 800 + 2 * 100
    assert all(report["space_reserved"] is False and report["quota_enforced"] is False
               and report["collection_authorized"] is False for report in reports)
    assert (archive / "retained.bin").stat().st_size == 800
    assert len(list(archive.iterdir())) == 1


@pytest.mark.parametrize("field,value", [
    ("maximum_artifact_bytes", 0), ("maximum_retained_bytes", -1),
    ("minimum_free_bytes", True), ("staging_headroom_bytes", 1.2),
    ("maximum_scan_entries", "100"), ("maximum_depth", None),
    ("minimum_free_bytes", 0), ("staging_headroom_bytes", 0),
    ("maximum_scan_entries", 100_001), ("maximum_depth", 33),
    ("maximum_artifact_bytes", 1001), ("minimum_free_bytes", 2**63),
])
def test_invalid_policy_rejected(field, value):
    with pytest.raises(ValueError):
        replace(POLICY, **{field: value})


@pytest.mark.parametrize("planned", [0, -1, True, 1.5, "100", 2**63])
def test_invalid_planned_bound_rejected_before_io(archive, monkeypatch, planned):
    def forbidden(*args, **kwargs):
        raise AssertionError("invalid input must not touch the filesystem")

    monkeypatch.setattr(capacity, "_open_without_links", forbidden)
    with pytest.raises(ValueError):
        inspect(archive, planned_artifact_bytes=planned)


def test_policy_immutable_and_revalidated(archive):
    with pytest.raises(FrozenInstanceError):
        POLICY.minimum_free_bytes = 1
    invalid = replace(POLICY)
    object.__setattr__(invalid, "minimum_free_bytes", 0)
    with pytest.raises(ValueError):
        inspect(archive, policy=invalid)


def test_quota_equality_and_planned_file_limit_are_explicit(archive):
    (archive / "existing").write_bytes(b"x" * 900)
    assert inspect(archive)["status"] == "WITHIN_DECLARED_LIMITS"
    (archive / "existing").write_bytes(b"x" * 901)
    assert inspect(archive)["reason_codes"] == ["RETAINED_BUDGET_LIMIT"]
    report = inspect(archive, planned_artifact_bytes=101)
    assert report["reason_codes"] == ["PLANNED_ARTIFACT_LIMIT", "RETAINED_BUDGET_LIMIT"]
    assert report["retained_logical_bytes"] == 901


def test_free_reserve_and_staging_equality_are_conservative(archive, monkeypatch):
    available = [170, 170]
    monkeypatch.setattr(capacity.os, "fstatvfs", lambda _: SimpleNamespace(
        f_bavail=available.pop(0), f_frsize=1))
    assert inspect(archive)["status"] == "WITHIN_DECLARED_LIMITS"
    available[:] = [1000, 169]
    report = inspect(archive)
    assert report["reason_codes"] == ["FREE_SPACE_LIMIT"]
    assert report["available_free_bytes"] == 169
    available[:] = [169, 1000]
    assert inspect(archive)["available_free_bytes"] == 169


@pytest.mark.parametrize("available,unit", [(-1, 1), (10, 0), (True, 1), (10, 1.5)])
def test_unknown_space_is_not_favorable_zero_or_success(archive, monkeypatch, available, unit):
    monkeypatch.setattr(capacity.os, "fstatvfs", lambda _: SimpleNamespace(
        f_bavail=available, f_frsize=unit))
    report = inspect(archive)
    assert report["reason_codes"] == ["SPACE_UNKNOWN"]
    assert report["scan_complete"] is False
    assert report["retained_logical_bytes"] is None
    assert report["available_free_bytes"] is None


@pytest.mark.parametrize("kind", ["file_link", "directory_link", "fifo"])
def test_special_entries_block_without_following_or_opening(archive, kind):
    target = archive.parent / "outside-secret-sentinel"
    if kind == "directory_link":
        target.mkdir()
        (target / "not-counted").write_bytes(b"x" * 5000)
        (archive / "link").symlink_to(target, target_is_directory=True)
    elif kind == "file_link":
        target.write_bytes(b"x" * 5000)
        (archive / "link").symlink_to(target)
    else:
        os.mkfifo(archive / "pipe")
    report = inspect(archive)
    assert report["status"] == "BLOCKED"
    assert report["reason_codes"] == ["UNSAFE_ENTRY"]
    assert report["scan_complete"] is False
    assert report["retained_logical_bytes"] is None
    assert "secret-sentinel" not in json.dumps(report)


def test_root_and_ancestor_links_missing_paths_and_regular_root_are_unknown(archive):
    alias = archive.parent / "alias"
    alias.symlink_to(archive, target_is_directory=True)
    child = archive / "child"
    child.mkdir()
    regular = archive / "file"
    regular.write_bytes(b"retained")
    missing = archive / "missing"
    for root in (alias, alias / "child", regular, missing, archive / ".." / archive.name):
        report = inspect(root)
        assert report["status"] == "UNKNOWN"
        assert report["retained_logical_bytes"] is None
    assert not missing.exists()


def test_entry_and_depth_limits_never_call_partial_usage_complete(archive):
    (archive / "first").write_bytes(b"x" * 10)
    (archive / "second").write_bytes(b"x" * 10)
    report = inspect(archive, policy=replace(POLICY, maximum_scan_entries=1))
    assert report["reason_codes"] == ["SCAN_ENTRY_LIMIT"]
    assert report["observed_entries"] == 1
    assert report["retained_logical_bytes"] is None
    (archive / "one" / "two").mkdir(parents=True)
    report = inspect(archive, policy=replace(POLICY, maximum_depth=1))
    assert report["reason_codes"] == ["SCAN_DEPTH_LIMIT"]
    assert report["scan_complete"] is False


def test_files_changing_during_scan_remain_unknown_total(archive, monkeypatch):
    original = archive / "changing"
    original.write_bytes(b"first")
    real_stat = capacity.os.stat

    def changed(path, *args, **kwargs):
        if path == "changing":
            original.write_bytes(b"changed-after-observation")
        return real_stat(path, *args, **kwargs)

    monkeypatch.setattr(capacity.os, "stat", changed)
    report = inspect(archive)
    assert report["reason_codes"] == ["SCAN_CHANGED"]
    assert report["retained_logical_bytes"] is None
    assert report["inventory_hash"] is None


def test_replaced_root_and_unreadable_space_never_pass(archive, monkeypatch):
    real_space = capacity._space
    calls = []

    def replaced(fd):
        calls.append(fd)
        if len(calls) == 2:
            archive.rename(archive.parent / "moved")
            archive.mkdir()
        return real_space(fd)

    monkeypatch.setattr(capacity, "_space", replaced)
    assert inspect(archive)["reason_codes"] == ["SCAN_CHANGED"]

    def unavailable(fd):
        raise PermissionError("password=secret-sentinel-do-not-render")

    monkeypatch.setattr(capacity, "_space", unavailable)
    report = inspect(archive)
    assert report["status"] == "UNKNOWN"
    assert "secret-sentinel" not in json.dumps(report)


def test_no_content_reads_writes_or_descriptor_leaks(archive, monkeypatch):
    (archive / "data").mkdir()
    (archive / "data" / "retained").write_bytes(b"content")
    real_open, real_close = os.open, os.close
    descriptors = set()

    def readonly(path, flags, *args, **kwargs):
        assert not flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)
        assert flags & os.O_DIRECTORY
        result = real_open(path, flags, *args, **kwargs)
        descriptors.add(result)
        return result

    def closed(fd):
        descriptors.remove(fd)
        return real_close(fd)

    monkeypatch.setattr(capacity.os, "open", readonly)
    monkeypatch.setattr(capacity.os, "close", closed)
    assert inspect(archive)["status"] == "WITHIN_DECLARED_LIMITS"
    assert not descriptors
    assert inspect(archive, policy=replace(POLICY, maximum_depth=1))["scan_complete"]
    assert not descriptors
    (archive / "data" / "deeper").mkdir()
    assert inspect(archive, policy=replace(POLICY, maximum_depth=1))["scan_complete"] is False
    assert not descriptors


def test_unsupported_platform_is_an_explicit_non_success(archive, monkeypatch):
    monkeypatch.delattr(capacity.os, "O_NOFOLLOW")
    report = inspect(archive)
    assert report["reason_codes"] == ["PLATFORM_UNSUPPORTED"]
    assert report["scan_complete"] is False


def test_mounted_other_device_is_not_silently_combined(archive, monkeypatch):
    from contextlib import contextmanager

    device = archive.stat().st_dev

    @contextmanager
    def other_device(fd):
        yield iter([SimpleNamespace(stat=lambda **_: SimpleNamespace(st_dev=device + 1))])

    monkeypatch.setattr(capacity.os, "scandir", other_device)
    report = inspect(archive)
    assert report["reason_codes"] == ["CROSS_DEVICE_ENTRY"]
    assert report["retained_logical_bytes"] is None


def test_naive_and_reversed_clocks_are_invalid(archive):
    with pytest.raises(ValueError):
        inspect(archive, clock=lambda: NOW.replace(tzinfo=None))
    instants = [NOW, NOW - timedelta(seconds=1)]
    with pytest.raises(ValueError):
        inspect(archive, clock=lambda: instants.pop(0))


def test_cli_is_read_only_and_rejects_dangerous_flags_safely(archive):
    command = [sys.executable, str(ROOT / "scripts/inspect_artifact_capacity.py"),
               "--artifact-root", str(archive), "--maximum-artifact-bytes", "100",
               "--maximum-retained-bytes", "1000", "--minimum-free-bytes", "50",
               "--staging-headroom-bytes", "20", "--planned-artifact-bytes", "100"]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "WITHIN_DECLARED_LIMITS"
    assert str(archive) not in result.stdout
    assert not list(archive.iterdir())
    invalid = subprocess.run(command + ["--delete", "secret-sentinel"],
                             capture_output=True, text=True, check=False)
    assert invalid.returncode == 2
    assert "secret-sentinel" not in invalid.stderr
