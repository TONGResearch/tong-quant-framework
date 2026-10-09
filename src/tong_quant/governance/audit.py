import tomllib
from dataclasses import dataclass
from pathlib import Path

from tong_quant.config.settings import load_settings
from tong_quant.data.storage.migrations import MIGRATION_HEAD
from tong_quant.governance.models import (
    ProjectGovernance,
    project_governance_from_dict,
)
from tong_quant.version import DATABASE_SCHEMA_VERSION, FRAMEWORK_VERSION


@dataclass(frozen=True, slots=True)
class GovernanceCheck:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True, slots=True)
class GovernanceReport:
    checks: tuple[GovernanceCheck, ...]

    @property
    def is_consistent(self) -> bool:
        return all(check.passed for check in self.checks)


def load_project_governance(path: Path) -> ProjectGovernance:
    with path.open("rb") as config_file:
        raw = tomllib.load(config_file)
    return project_governance_from_dict(raw)


def audit_project_governance(
    project_root: Path,
    *,
    governance_path: Path | None = None,
) -> GovernanceReport:
    config_path = governance_path or project_root / "config/project-governance.toml"
    governance = load_project_governance(config_path)
    settings = load_settings(project_root / "config/default.toml")
    status_path = project_root / governance.baseline.canonical_status_document
    status_text = status_path.read_text(encoding="utf-8") if status_path.exists() else ""
    checks = [
        _equal_check(
            "framework_version",
            governance.baseline.framework_version,
            FRAMEWORK_VERSION,
        ),
        _equal_check(
            "database_schema_version",
            governance.baseline.database_schema_version,
            DATABASE_SCHEMA_VERSION,
        ),
        _equal_check(
            "migration_head",
            governance.baseline.migration_head,
            MIGRATION_HEAD,
        ),
        _equal_check(
            "execution_mode",
            settings.execution.mode,
            governance.freeze.required_execution_mode,
        ),
        _equal_check(
            "allow_live_orders",
            settings.execution.allow_live_orders,
            governance.freeze.allow_live_orders,
        ),
        _equal_check(
            "notification_mode",
            settings.notifications.mode,
            governance.freeze.required_notification_mode,
        ),
        _exists_check(
            project_root,
            governance.baseline.canonical_status_document,
            "canonical_status_document",
        ),
    ]
    status_markers = (
        ("framework_version", governance.baseline.framework_version),
        ("database_schema_version", governance.baseline.database_schema_version),
        ("migration_head", governance.baseline.migration_head),
        ("pit_readiness", governance.readiness.pit.upper()),
    )
    checks.extend(
        GovernanceCheck(
            name=f"status_marker:{name}",
            passed=marker in status_text,
            detail=(
                f"PROJECT_STATUS contains {marker}"
                if marker in status_text
                else f"PROJECT_STATUS is missing {marker}"
            ),
        )
        for name, marker in status_markers
    )
    checks.extend(
        GovernanceCheck(
            name=f"status_command:{command}",
            passed=command in status_text,
            detail=(
                "required command is documented"
                if command in status_text
                else "required command is missing from PROJECT_STATUS"
            ),
        )
        for command in governance.quality.required_commands
    )
    checks.extend(
        _exists_check(project_root, document, f"required_document:{document}")
        for document in governance.quality.required_documents
    )
    for work_package in governance.work_packages:
        check = _exists_check(
            project_root,
            work_package.document,
            f"work_package:{work_package.package_id}",
        )
        if check.passed:
            content = (project_root / work_package.document).read_text(encoding="utf-8")
            marker = f"Work Package: {work_package.package_id}"
            status_marker = f"Status: `{work_package.status}`"
            check = GovernanceCheck(
                name=check.name,
                passed=marker in content and status_marker in content,
                detail=(
                    f"contains {marker} and {status_marker}"
                    if marker in content and status_marker in content
                    else f"missing {marker} or {status_marker}"
                ),
            )
        checks.append(check)

    ci_path = project_root / ".github/workflows/ci.yml"
    ci_text = ci_path.read_text(encoding="utf-8") if ci_path.exists() else ""
    governance_command = "python scripts/check_project_governance.py"
    checks.append(
        GovernanceCheck(
            name="ci_governance_check",
            passed=governance_command in ci_text,
            detail=(
                "governance audit is enforced by CI"
                if governance_command in ci_text
                else "CI does not run the governance audit"
            ),
        )
    )
    checks.extend(
        _workflow_runtime_check(
            project_root,
            ".github/workflows/ci.yml",
            (
                "runs-on: ubuntu-24.04",
                "actions/checkout@v5",
                "actions/setup-python@v6",
            ),
        )
    )
    checks.extend(
        _workflow_runtime_check(
            project_root,
            ".github/workflows/provider-contract-monitor.yml",
            (
                "runs-on: ubuntu-24.04",
                "actions/checkout@v5",
                "actions/setup-python@v6",
                "actions/cache/restore@v5",
                "actions/cache/save@v5",
                "actions/upload-artifact@v6",
            ),
        )
    )
    return GovernanceReport(checks=tuple(checks))


def _equal_check(name: str, actual: object, expected: object) -> GovernanceCheck:
    return GovernanceCheck(
        name=name,
        passed=actual == expected,
        detail=f"actual={actual!r}, expected={expected!r}",
    )


def _exists_check(
    project_root: Path,
    relative_path: Path,
    name: str,
) -> GovernanceCheck:
    exists = (project_root / relative_path).is_file()
    return GovernanceCheck(
        name=name,
        passed=exists,
        detail=f"{relative_path} {'exists' if exists else 'is missing'}",
    )


def _workflow_runtime_check(
    project_root: Path,
    relative_path: str,
    required_markers: tuple[str, ...],
) -> tuple[GovernanceCheck, ...]:
    path = project_root / relative_path
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    checks = [
        GovernanceCheck(
            name=f"workflow_runtime:{relative_path}:{marker}",
            passed=marker in text,
            detail=(
                f"workflow contains {marker}"
                if marker in text
                else f"workflow is missing {marker}"
            ),
        )
        for marker in required_markers
    ]
    checks.append(
        GovernanceCheck(
            name=f"workflow_runtime:{relative_path}:no_moving_runner",
            passed="ubuntu-latest" not in text,
            detail=(
                "workflow runner is explicitly pinned"
                if "ubuntu-latest" not in text
                else "workflow uses the moving ubuntu-latest runner"
            ),
        )
    )
    return tuple(checks)


__all__ = [
    "GovernanceCheck",
    "GovernanceReport",
    "audit_project_governance",
    "load_project_governance",
]
