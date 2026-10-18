"""Offline host diagnostics, not a trading or production-readiness gate."""

import io
import json
import re
import subprocess
import sys
import tarfile
import tomllib
from collections.abc import Sequence
from contextlib import suppress
from dataclasses import asdict
from datetime import UTC, datetime
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import tong_quant
from tong_quant.application.dependency_lock import check_dependency_lock
from tong_quant.config.settings import Settings, load_settings
from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.storage.engineering import SQLiteIntegrityService
from tong_quant.governance.audit import audit_project_governance
from tong_quant.version import DEPLOYMENT_PREFLIGHT_VERSION, FRAMEWORK_VERSION


def _run(command: Sequence[str], root: Path) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            command, cwd=root, capture_output=True, text=True, timeout=30, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def _package_hash(root: Path) -> str:
    if root.is_symlink() or not root.is_dir():
        raise ValueError("package directory is unavailable")
    if any(path.is_symlink() for path in root.rglob("*")):
        raise ValueError("package source symlinks are unsupported")
    files = sorted(root.rglob("*.py"))
    if not files:
        raise ValueError("package contains no Python sources")
    identities = []
    for path in files:
        identities.append((
            path.relative_to(root).as_posix(), sha256(path.read_bytes()).hexdigest(),
        ))
    return sha256(json.dumps(identities, separators=(",", ":")).encode()).hexdigest()


def _relative_to_root(path: Path, root: Path) -> Path:
    expanded = path.expanduser()
    return expanded if expanded.is_absolute() else root / expanded


def _committed_package_hash(root: Path, commit: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-c", "core.fsmonitor=false", "-C", str(root), "archive",
             "--format=tar", commit, "src/tong_quant"],
            capture_output=True, timeout=30, check=False,
        )
        if result.returncode != 0 or len(result.stdout) > 32 * 1024 * 1024:
            return None
        identities = []
        with tarfile.open(fileobj=io.BytesIO(result.stdout), mode="r:") as archive:
            for member in archive:
                if member.issym() or member.islnk():
                    return None
                if not member.isfile() or not member.name.endswith(".py"):
                    continue
                relative = Path(member.name).relative_to("src/tong_quant")
                if ".." in relative.parts or member.size > 8 * 1024 * 1024:
                    return None
                stream = archive.extractfile(member)
                if stream is None:
                    return None
                with stream:
                    identities.append((relative.as_posix(), sha256(stream.read()).hexdigest()))
        if not identities:
            return None
        return sha256(json.dumps(sorted(identities), separators=(",", ":")).encode()).hexdigest()
    except (OSError, ValueError, tarfile.TarError, subprocess.SubprocessError):
        return None


def run_deployment_preflight(
    project_root: Path,
    *,
    config_path: Path | None = None,
    overrides: Sequence[Path] = (),
    database: Path | None = None,
) -> dict[str, object]:
    root = project_root.expanduser().resolve()
    checks: list[dict[str, object]] = []

    def record(name: str, passed: bool, failure_code: str) -> None:
        checks.append({"name": name, "passed": passed, "code": "ok" if passed else failure_code})

    record("python_runtime", sys.version_info[:2] == (3, 12), "python_3_12_required")
    try:
        installed_version = version("tong-quant-framework")
    except PackageNotFoundError:
        installed_version = None
    record("installed_version", installed_version == FRAMEWORK_VERSION, "package_version_mismatch")
    dependencies = _run(
        [sys.executable, "-m", "pip", "--disable-pip-version-check", "--no-cache-dir", "check"],
        root,
    )
    record(
        "dependency_health", dependencies is not None and dependencies.returncode == 0,
        "dependency_check_failed_or_unavailable",
    )
    dependency_lock = check_dependency_lock(root)
    record(
        "dependency_lock_integrity", dependency_lock.artifact_integrity, "dependency_lock_invalid",
    )
    record(
        "locked_runtime_versions", dependency_lock.environment_matches,
        "locked_environment_mismatch_or_unsupported",
    )

    git = ["git", "-c", "core.fsmonitor=false", "-C", str(root)]
    git_root = _run([*git, "rev-parse", "--show-toplevel"], root)
    git_head = _run([*git, "rev-parse", "HEAD"], root)
    commit = None
    if (
        git_root is not None and git_root.returncode == 0
        and Path(git_root.stdout.strip()).resolve() == root
        and git_head is not None and git_head.returncode == 0
        and re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", git_head.stdout.strip())
    ):
        commit = git_head.stdout.strip()
    record("git_identity", commit is not None, "git_identity_unavailable")
    state = _run([*git, "status", "--porcelain=v1", "-z", "--untracked-files=normal"], root)
    record(
        "clean_checkout", commit is not None and state is not None
        and state.returncode == 0 and not state.stdout,
        "checkout_dirty_or_unavailable",
    )

    source_hash = runtime_hash = None
    try:
        source_hash = _package_hash(root / "src/tong_quant")
        runtime_hash = _package_hash(Path(tong_quant.__file__).resolve().parent)
    except (OSError, ValueError):
        pass
    record(
        "runtime_source_match", source_hash is not None and source_hash == runtime_hash,
        "runtime_source_mismatch_or_unavailable",
    )
    committed_hash = None if commit is None else _committed_package_hash(root, commit)
    record(
        "committed_source_match", committed_hash is not None and committed_hash == source_hash,
        "source_not_bound_to_commit",
    )

    settings: Settings | None = None
    configuration_hash = None
    try:
        paths = tuple(_relative_to_root(path, root) for path in (
            config_path or Path("config/default.toml"), *overrides,
        ))
        captured = []
        for path in paths:
            if path.is_symlink() or path.stat().st_size > 1024 * 1024:
                raise ValueError("configuration source is unsupported")
            content = path.read_bytes()
            reject_sensitive_structure(tomllib.loads(content.decode()), path="configuration")
            captured.append(content)
        loaded = load_settings(paths[0], *paths[1:])
        effective = json.loads(json.dumps(asdict(loaded), default=str, sort_keys=True))
        reject_sensitive_structure(effective, path="effective_configuration")
        if any(path.read_bytes() != content for path, content in zip(paths, captured, strict=True)):
            raise ValueError("configuration changed during inspection")
        configuration_hash = sha256(
            json.dumps(effective, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        settings = loaded
    except (OSError, ValueError, TypeError, KeyError):
        pass
    record("configuration", settings is not None, "configuration_invalid_or_sensitive")
    record(
        "execution_disabled", settings is not None and settings.execution.mode == "disabled"
        and settings.execution.allow_live_orders is False,
        "execution_must_remain_disabled",
    )
    record(
        "notifications_disabled",
        settings is not None and settings.notifications.mode == "disabled",
        "notifications_must_remain_disabled",
    )
    record(
        "strict_pit", settings is not None and settings.data.strict_point_in_time is True
        and settings.data.default_adjustment == "none", "strict_unadjusted_pit_required",
    )

    governance_ok = False
    with suppress(OSError, ValueError, TypeError, KeyError):
        governance_ok = audit_project_governance(root).is_consistent
    record("project_governance", governance_ok, "governance_invalid_or_inconsistent")

    database_hash = None
    database_ok = False
    if settings is not None:
        audit = SQLiteIntegrityService().audit(
            _relative_to_root(database or settings.data.database_path, root)
        )
        database_ok = audit.passed
        database_hash = audit.audit_hash
    record("database_integrity", database_ok, "database_missing_or_integrity_failed")
    report: dict[str, object] = {
        "scope": "offline_research_host_preflight",
        "model_version": DEPLOYMENT_PREFLIGHT_VERSION,
        "checked_at": datetime.now(UTC).isoformat(),
        "framework_version": FRAMEWORK_VERSION,
        "offline_preflight_passed": all(check["passed"] is True for check in checks),
        "production_readiness_assessed": False,
        "pit_readiness_assessed": False,
        "paper_trading_authorized": False,
        "live_execution_authorized": False,
        "git_commit": commit,
        "source_hash": source_hash,
        "runtime_hash": runtime_hash,
        "committed_source_hash": committed_hash,
        "effective_configuration_hash": configuration_hash,
        "dependency_lock_hash": dependency_lock.manifest_hash,
        "database_audit_hash": database_hash,
        "checks": checks,
    }
    reject_sensitive_structure(report)
    return report
