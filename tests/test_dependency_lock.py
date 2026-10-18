import copy
import json
import runpy
import shutil
import sys
from pathlib import Path

import pytest

from tong_quant.application import dependency_lock as locks
from tong_quant.version import FRAMEWORK_VERSION

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/compile_native_dependency_lock.py"


@pytest.fixture
def locked_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    shutil.copyfile("pyproject.toml", root / "pyproject.toml")
    shutil.copytree("requirements", root / "requirements")
    manifest = json.loads(
        (root / "requirements/runtime-macos-arm64-py312.manifest.json").read_text()
    )
    pins = {item["name"]: item["version"] for item in manifest["packages"]}
    monkeypatch.setattr(locks.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(locks.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(locks.platform, "mac_ver", lambda: ("14.0", (), ""))
    monkeypatch.setattr(locks, "version", lambda name: pins[name])
    return root


def test_locked_environment_has_bound_artifacts_and_exact_runtime_versions(
    locked_root: Path,
) -> None:
    result = locks.check_dependency_lock(locked_root)
    assert result.artifact_integrity is True
    assert result.environment_matches is True
    assert len(result.manifest_hash) == 64


@pytest.mark.parametrize("name", [
    "runtime-macos-arm64-py312.lock", "build-py312.lock", "build.in",
])
def test_changed_lock_or_build_input_fails_closed(locked_root: Path, name: str) -> None:
    path = locked_root / "requirements" / name
    path.write_text(path.read_text() + "\n# changed\n")
    result = locks.check_dependency_lock(locked_root)
    assert result.artifact_integrity is False
    assert result.environment_matches is False


def test_changed_project_dependency_specification_requires_a_new_lock(locked_root: Path) -> None:
    path = locked_root / "pyproject.toml"
    path.write_text(path.read_text().replace("pandas>=2.2,<4", "pandas>=3,<4"))
    assert locks.check_dependency_lock(locked_root).artifact_integrity is False


def test_project_metadata_version_drift_cannot_reuse_lock(locked_root: Path) -> None:
    path = locked_root / "pyproject.toml"
    path.write_text(path.read_text().replace('version = "0.8.0"', 'version = "0.9.0"'))
    assert locks.check_dependency_lock(locked_root).artifact_integrity is False


@pytest.mark.parametrize("system,machine,macos", [
    ("Linux", "aarch64", ""), ("Darwin", "x86_64", "14.0"), ("Darwin", "arm64", "13.0"),
])
def test_foreign_or_older_platform_cannot_reuse_native_lock(
    locked_root: Path, monkeypatch: pytest.MonkeyPatch, system: str, machine: str, macos: str,
) -> None:
    monkeypatch.setattr(locks.platform, "system", lambda: system)
    monkeypatch.setattr(locks.platform, "machine", lambda: machine)
    monkeypatch.setattr(locks.platform, "mac_ver", lambda: (macos, (), ""))
    result = locks.check_dependency_lock(locked_root)
    assert result.artifact_integrity is True
    assert result.environment_matches is False
    assert result.error_code == "unsupported_lock_target"


def test_compatible_but_different_package_version_is_still_drift(
    locked_root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = locks.version
    monkeypatch.setattr(
        locks, "version", lambda name: "3.0.4" if name == "pandas" else original(name),
    )
    result = locks.check_dependency_lock(locked_root)
    assert result.artifact_integrity is True
    assert result.environment_matches is False
    assert result.mismatched_packages == ("pandas",)


@pytest.mark.parametrize("change", ["omit_pin", "duplicate_pin", "bad_hash", "credential_field"])
def test_manifest_cannot_omit_pins_or_introduce_invalid_content(
    locked_root: Path, change: str,
) -> None:
    path = locked_root / "requirements/runtime-macos-arm64-py312.manifest.json"
    manifest = json.loads(path.read_text())
    if change == "omit_pin":
        manifest["packages"].pop()
    elif change == "duplicate_pin":
        manifest["packages"].append(dict(manifest["packages"][0]))
    elif change == "bad_hash":
        manifest["packages"][0]["sha256"] = "not-a-hash"
    else:
        manifest["token"] = ""
    path.write_text(json.dumps(manifest))
    assert locks.check_dependency_lock(locked_root).artifact_integrity is False


def test_lock_symlink_is_not_followed(locked_root: Path) -> None:
    path = locked_root / "requirements/runtime-macos-arm64-py312.lock"
    saved = path.with_suffix(".saved")
    path.rename(saved)
    path.symlink_to(saved)
    assert locks.check_dependency_lock(locked_root).artifact_integrity is False


def _report() -> dict:
    from packaging.requirements import Requirement

    requirements = ["akshare>=1.18,<2", "certifi>=2024.0", "pandas>=2.2,<4", "tushare>=1.4,<2"]
    versions = {"akshare": "1.18.64", "certifi": "2026.5.20",
                "pandas": "3.0.3", "tushare": "1.4.29"}
    packages = [{"metadata": {
        "name": "tong-quant-framework", "version": FRAMEWORK_VERSION,
        "requires_dist": requirements,
    }}]
    for value in requirements:
        name = Requirement(value).name
        version = versions[name]
        packages.append({
            "metadata": {"name": name, "version": version},
            "download_info": {
                "url": f"https://files.pythonhosted.org/packages/{name}-{version}-py3-none-any.whl",
                "archive_info": {"hashes": {"sha256": "a" * 64}},
            },
        })
    return {"version": "1", "environment": {
        "platform_system": "Darwin", "platform_machine": "arm64",
        "python_version": "3.12", "implementation_name": "cpython",
    }, "install": packages}


def test_native_compiler_is_deterministic_and_does_not_persist_download_urls(
    locked_root: Path,
) -> None:
    compiler = runpy.run_path(str(SCRIPT))["compile_report"]
    report = _report()
    left = compiler(locked_root, report, "runtime")
    right_report = copy.deepcopy(report)
    right_report["install"].reverse()
    right = compiler(locked_root, right_report, "runtime")
    assert left == right
    assert "pythonhosted" not in json.dumps(left)


@pytest.mark.parametrize("change", [
    "missing_root_pin", "different_roots", "different_host", "url", "foreign_wheel",
])
def test_native_compiler_rejects_wrong_scope_or_unapproved_source(
    locked_root: Path, change: str,
) -> None:
    compiler = runpy.run_path(str(SCRIPT))["compile_report"]
    report = _report()
    if change == "missing_root_pin":
        report["install"].pop()
    elif change == "different_roots":
        report["install"][0]["metadata"]["requires_dist"].pop()
    elif change == "different_host":
        report["environment"]["platform_machine"] = "x86_64"
    elif change == "url":
        report["install"][1]["download_info"]["url"] = "https://example.invalid/package.whl"
    else:
        report["install"][1]["download_info"]["url"] = (
            "https://files.pythonhosted.org/packages/akshare-1.18.64-cp312-cp312-win_amd64.whl"
        )
    with pytest.raises(ValueError):
        compiler(locked_root, report, "runtime")


def test_compiler_cli_preserves_existing_artifacts_and_cleans_its_partial_output(
    locked_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    namespace = runpy.run_path(str(SCRIPT))
    report = tmp_path / "resolution.json"
    report.write_text(json.dumps(_report()))
    output = tmp_path / "staged"
    output.mkdir()
    manifest = output / "runtime-macos-arm64-py312.manifest.json"
    manifest.write_text("existing reviewed manifest")
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--project-root", str(locked_root),
        "--profile", "runtime", "--report", str(report), "--output-dir", str(output)])
    with pytest.raises(SystemExit):
        namespace["main"]()
    assert manifest.read_text() == "existing reviewed manifest"
    assert not (output / "runtime-macos-arm64-py312.lock").exists()
