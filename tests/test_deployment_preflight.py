import io
import json
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from tong_quant import __main__
from tong_quant.application import deployment_preflight as preflight
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.version import FRAMEWORK_VERSION


@pytest.fixture
def host(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "project"
    (root / "config").mkdir(parents=True)
    shutil.copyfile("config/default.toml", root / "config/default.toml")
    store = SQLiteStore(root / "data/tong_quant.sqlite3")
    store.initialize()
    monkeypatch.setattr(preflight, "version", lambda name: FRAMEWORK_VERSION)
    monkeypatch.setattr(preflight, "check_dependency_lock", lambda path: SimpleNamespace(
        artifact_integrity=True, environment_matches=True, manifest_hash="d" * 64,
    ))
    monkeypatch.setattr(preflight, "_package_hash", lambda path: "a" * 64)
    monkeypatch.setattr(preflight, "_committed_package_hash", lambda path, commit: "a" * 64)
    monkeypatch.setattr(
        preflight, "audit_project_governance", lambda path: SimpleNamespace(is_consistent=True),
    )

    def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        del cwd
        result = ""
        if "--show-toplevel" in command:
            result = str(root)
        elif "HEAD" in command:
            result = "b" * 40
        return subprocess.CompletedProcess(command, 0, result, "")

    monkeypatch.setattr(preflight, "_run", run)
    return root


def _checks(report: dict[str, object]) -> dict[str, bool]:
    return {item["name"]: item["passed"] for item in report["checks"]}


def test_offline_success_never_authorizes_trading_or_promotes_readiness(host: Path) -> None:
    before = (host / "data/tong_quant.sqlite3").read_bytes()
    report = preflight.run_deployment_preflight(host)
    assert report["offline_preflight_passed"] is True
    assert report["live_execution_authorized"] is False
    assert report["paper_trading_authorized"] is False
    assert report["pit_readiness_assessed"] is False
    assert report["production_readiness_assessed"] is False
    assert (host / "data/tong_quant.sqlite3").read_bytes() == before
    assert str(host) not in json.dumps(report)


@pytest.mark.parametrize(
    ("override", "check"),
    [
        ('[execution]\nmode="paper"', "execution_disabled"),
        ('[execution]\nmode="automatic"\nallow_live_orders=true', "execution_disabled"),
        ('[notifications]\nmode="preview"', "notifications_disabled"),
        ('[data]\nstrict_point_in_time=false', "strict_pit"),
        ('[data]\ndefault_adjustment="qfq"', "strict_pit"),
    ],
)
def test_unsafe_effective_config_blocks_host_check(
    host: Path, override: str, check: str,
) -> None:
    (host / "override.toml").write_text(override)
    report = preflight.run_deployment_preflight(host, overrides=[Path("override.toml")])
    assert _checks(report)[check] is False
    assert report["offline_preflight_passed"] is False


def test_credential_fields_in_config_are_rejected_without_rendering_contents(host: Path) -> None:
    (host / "override.toml").write_text('[provider_auth]\ntoken=""')
    report = preflight.run_deployment_preflight(host, overrides=[Path("override.toml")])
    assert _checks(report)["configuration"] is False
    assert report["effective_configuration_hash"] is None
    assert "provider_auth" not in json.dumps(report)


def test_dirty_git_output_is_not_rendered(host: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original = preflight._run

    def run(command: list[str], root: Path) -> subprocess.CompletedProcess[str] | None:
        if "status" in command:
            return subprocess.CompletedProcess(command, 0, " M private-file-name\0", "")
        return original(command, root)

    monkeypatch.setattr(preflight, "_run", run)
    report = preflight.run_deployment_preflight(host)
    assert _checks(report)["clean_checkout"] is False
    assert "private-file-name" not in json.dumps(report)


def test_dependency_failure_is_not_a_provider_failure(
    host: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = preflight._run

    def run(command: list[str], root: Path) -> subprocess.CompletedProcess[str] | None:
        if "pip" in command:
            return subprocess.CompletedProcess(command, 1, "private diagnostic", "private error")
        return original(command, root)

    monkeypatch.setattr(preflight, "_run", run)
    report = preflight.run_deployment_preflight(host)
    assert _checks(report)["dependency_health"] is False
    assert "private" not in json.dumps(report)


def test_runtime_byte_mismatch_blocks_even_when_versions_match(
    host: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        preflight, "_package_hash", lambda path: "a" * 64 if host in path.parents else "b" * 64,
    )
    report = preflight.run_deployment_preflight(host)
    assert _checks(report)["installed_version"] is True
    assert _checks(report)["runtime_source_match"] is False


def test_missing_database_is_not_created(host: Path) -> None:
    missing = host / "absent/database.sqlite3"
    report = preflight.run_deployment_preflight(host, database=missing)
    assert _checks(report)["database_integrity"] is False
    assert not missing.parent.exists()


def test_configuration_fingerprint_includes_effective_environment(
    host: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TONG_QUANT_ENVIRONMENT", "development")
    first = preflight.run_deployment_preflight(host)
    monkeypatch.setenv("TONG_QUANT_ENVIRONMENT", "research-host")
    second = preflight.run_deployment_preflight(host)
    assert first["effective_configuration_hash"] != second["effective_configuration_hash"]


def test_bounded_command_timeout_returns_no_raw_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    def timeout(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired("private command", 30, output="private output")

    monkeypatch.setattr(subprocess, "run", timeout)
    assert preflight._run(["unused"], Path.cwd()) is None


def test_package_hash_includes_source_content_and_rejects_symlink_directories(
    tmp_path: Path,
) -> None:
    package = tmp_path / "package"
    package.mkdir()
    source = package / "__init__.py"
    source.write_text("VALUE = 1\n")
    first = preflight._package_hash(package)
    source.write_text("VALUE = 2\n")
    assert preflight._package_hash(package) != first
    (package / "linked").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError, match="symlinks"):
        preflight._package_hash(package)


def test_module_status_accepts_explicit_project_root_outside_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    root = Path.cwd()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["tong-quant", "status", "--project-root", str(root)])
    __main__.main()
    output = capsys.readouterr().out
    assert "Execution mode: disabled" in output
    assert "Notification mode: disabled" in output


def test_module_preflight_requires_explicit_root(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["tong-quant", "preflight"])
    with pytest.raises(SystemExit) as error:
        __main__.main()
    assert error.value.code == 2
    assert "explicit --project-root" in capsys.readouterr().err


@pytest.mark.parametrize("passed", [False, True])
def test_module_preflight_exit_codes_are_separate_from_trading_authorization(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], passed: bool,
) -> None:
    report = {"offline_preflight_passed": passed, "live_execution_authorized": False}
    monkeypatch.setattr(preflight, "run_deployment_preflight", lambda *args, **kwargs: report)
    monkeypatch.setattr(sys, "argv", ["tong-quant", "preflight", "--project-root", "/unused"])
    with pytest.raises(SystemExit) as error:
        __main__.main()
    assert error.value.code == (0 if passed else 2)
    assert json.loads(capsys.readouterr().out)["live_execution_authorized"] is False


def test_governance_failure_is_reported_without_raw_exception(
    host: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(path: Path) -> None:
        raise ValueError("private governance detail")

    monkeypatch.setattr(preflight, "audit_project_governance", fail)
    report = preflight.run_deployment_preflight(host)
    assert _checks(report)["project_governance"] is False
    assert "private" not in json.dumps(report)


def test_configuration_changed_during_read_fails_closed(
    host: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = preflight.load_settings

    def load(path: Path, *overrides: Path) -> object:
        settings = original(path, *overrides)
        path.write_text(path.read_text() + "\n# concurrent change\n")
        return settings

    monkeypatch.setattr(preflight, "load_settings", load)
    report = preflight.run_deployment_preflight(host)
    assert _checks(report)["configuration"] is False
    assert report["effective_configuration_hash"] is None


def test_matching_runtime_and_checkout_cannot_replace_commit_binding(
    host: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(preflight, "_committed_package_hash", lambda path, commit: "c" * 64)
    report = preflight.run_deployment_preflight(host)
    assert _checks(report)["runtime_source_match"] is True
    assert _checks(report)["committed_source_match"] is False
    assert report["offline_preflight_passed"] is False


def test_committed_source_hash_matches_bytes_without_extracting_archive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    package = tmp_path / "src/tong_quant"
    package.mkdir(parents=True)
    (package / "__init__.py").write_bytes(b"VALUE = 1\n")
    content = io.BytesIO()
    with tarfile.open(fileobj=content, mode="w") as archive:
        archive.add(package, arcname="src/tong_quant")

    def archive_result(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess([], 0, content.getvalue(), b"")

    monkeypatch.setattr(subprocess, "run", archive_result)
    assert preflight._committed_package_hash(tmp_path, "a" * 40) == preflight._package_hash(package)
    (package / "uncommitted.py").write_text("NEW = True\n")
    assert preflight._committed_package_hash(tmp_path, "a" * 40) != preflight._package_hash(package)
