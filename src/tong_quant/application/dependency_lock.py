"""Verify a native pip-resolution snapshot without importing provider SDKs."""

import json
import platform
import re
import sys
import tomllib
from dataclasses import dataclass
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from tong_quant.core.security import reject_sensitive_structure
from tong_quant.version import DEPENDENCY_LOCK_VERSION, FRAMEWORK_VERSION


@dataclass(frozen=True, slots=True)
class DependencyLockCheck:
    artifact_integrity: bool
    environment_matches: bool
    manifest_hash: str | None
    mismatched_packages: tuple[str, ...] = ()
    error_code: str = ""


def dependency_specification_hash(root: Path, profile: str) -> str:
    if profile not in {"runtime", "dev"}:
        raise ValueError("unsupported lock profile")
    with (root / "pyproject.toml").open("rb") as source:
        raw = tomllib.load(source)
    project = raw["project"]
    if project["version"] != FRAMEWORK_VERSION:
        raise ValueError("project metadata version does not match framework")
    inputs = {
        "python": project["requires-python"],
        "runtime": sorted(project["dependencies"]),
        "dev": sorted(project["optional-dependencies"]["dev"]) if profile == "dev" else [],
        "build": sorted(raw["build-system"]["requires"]),
    }
    return sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()


def _packages(raw: object) -> list[dict[str, str]]:
    if not isinstance(raw, list) or not raw:
        raise ValueError("lock packages are required")
    packages = []
    names = set()
    for item in raw:
        if not isinstance(item, dict) or set(item) != {"name", "version", "sha256", "kind"}:
            raise ValueError("lock package schema is invalid")
        if not all(isinstance(value, str) for value in item.values()):
            raise ValueError("lock package fields must be text")
        if (
            not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", item["name"])
            or not re.fullmatch(r"[0-9][A-Za-z0-9.!+_-]*", item["version"])
            or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"])
            or item["kind"] not in {"wheel", "sdist"}
            or item["name"] in names
        ):
            raise ValueError("lock package identity or hash is invalid")
        names.add(item["name"])
        packages.append(dict(item))
    return sorted(packages, key=lambda item: item["name"])


def render_native_lock(packages: object, profile: str, target: dict[str, Any]) -> str:
    if profile not in {"runtime", "dev"} or (
        target.get("system") != "Darwin" or target.get("machine") != "arm64"
        or target.get("python") != "3.12"
    ):
        raise ValueError("unsupported native lock target")
    return (
        "# Generated from a native pip resolver report; do not edit pins or hashes.\n"
        f"# Profile: {profile}; target: macOS arm64 / CPython 3.12.\n"
        + "".join(
            f"{item['name']}=={item['version']} --hash=sha256:{item['sha256']}\n"
            for item in _packages(packages)
        )
    )


def _read_artifact(root: Path, relative: str) -> bytes:
    path = root / relative
    if path.is_symlink() or not path.resolve().is_relative_to(root) or path.stat().st_size > 2**20:
        raise ValueError("unsupported lock artifact path")
    return path.read_bytes()


def check_dependency_lock(root: Path, profile: str = "runtime") -> DependencyLockCheck:
    root = root.expanduser().resolve()
    digest = None
    try:
        if profile not in {"runtime", "dev"}:
            raise ValueError("unsupported lock profile")
        prefix = f"requirements/{profile}-macos-arm64-py312"
        content = _read_artifact(root, f"{prefix}.manifest.json")
        manifest = json.loads(content)
        reject_sensitive_structure(manifest)
        if (
            manifest["model_version"] != DEPENDENCY_LOCK_VERSION
            or manifest["framework_version"] != FRAMEWORK_VERSION
            or manifest["profile"] != profile
            or manifest["dependency_specification_hash"] != dependency_specification_hash(
                root, profile
            )
            or manifest["build_lock_sha256"] != sha256(
                _read_artifact(root, "requirements/build-py312.lock")
            ).hexdigest()
            or manifest["build_input_sha256"] != sha256(
                _read_artifact(root, "requirements/build.in")
            ).hexdigest()
        ):
            raise ValueError("lock input binding mismatch")
        packages = _packages(manifest["packages"])
        lock = _read_artifact(root, f"{prefix}.lock")
        if (
            lock.decode() != render_native_lock(packages, profile, manifest["target"])
            or sha256(lock).hexdigest() != manifest["lock_sha256"]
        ):
            raise ValueError("lock content binding mismatch")
        minimum = manifest["target"]["minimum_macos"]
        if (
            not isinstance(minimum, list) or len(minimum) != 2
            or any(type(value) is not int or value < 0 for value in minimum)
        ):
            raise ValueError("minimum macOS is invalid")
        digest = sha256(content).hexdigest()
        if (
            platform.system() != "Darwin" or platform.machine().lower() != "arm64"
            or sys.version_info[:2] != (3, 12)
        ):
            return DependencyLockCheck(True, False, digest, error_code="unsupported_lock_target")
        macos = tuple(int(part) for part in platform.mac_ver()[0].split(".")[:2])
        if macos < tuple(minimum):
            return DependencyLockCheck(True, False, digest, error_code="unsupported_lock_target")
        mismatched = []
        for package in packages:
            try:
                if version(package["name"]) != package["version"]:
                    mismatched.append(package["name"])
            except PackageNotFoundError:
                mismatched.append(package["name"])
        return DependencyLockCheck(
            True, not mismatched, digest, tuple(mismatched),
            "installed_versions_mismatch" if mismatched else "",
        )
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return DependencyLockCheck(False, False, digest, error_code="lock_artifact_invalid")
