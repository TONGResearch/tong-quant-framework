from pathlib import Path

import pytest

from tong_quant.governance import (
    audit_project_governance,
    load_project_governance,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
GOVERNANCE_PATH = PROJECT_ROOT / "config/project-governance.toml"


def test_canonical_project_governance_is_consistent() -> None:
    governance = load_project_governance(GOVERNANCE_PATH)
    report = audit_project_governance(PROJECT_ROOT)

    assert report.is_consistent
    assert governance.freeze.trading_related_development is True
    assert governance.readiness.pit == "unsuitable"
    assert tuple(
        item.package_id for item in governance.work_packages if item.status == "ready"
    ) == ("WP-OPS-001",)
    assert next(
        item for item in governance.work_packages if item.package_id == "WP-DATA-001"
    ).status == "completed"
    assert next(
        item for item in governance.work_packages if item.package_id == "WP-DB-001"
    ).status == "completed"
    assert next(
        item for item in governance.work_packages if item.package_id == "WP-DATA-002"
    ).status == "completed"
    assert next(
        item for item in governance.work_packages if item.package_id == "WP-DATA-003"
    ).status == "completed"


def test_governance_rejects_disabled_trading_freeze(tmp_path: Path) -> None:
    text = GOVERNANCE_PATH.read_text(encoding="utf-8").replace(
        "trading_related_development = true",
        "trading_related_development = false",
    )
    path = tmp_path / "unsafe-governance.toml"
    path.write_text(text, encoding="utf-8")

    with pytest.raises(ValueError, match="trading development freeze"):
        load_project_governance(path)


def test_governance_audit_detects_version_drift(tmp_path: Path) -> None:
    text = GOVERNANCE_PATH.read_text(encoding="utf-8").replace(
        'framework_version = "0.8.0"',
        'framework_version = "9.9.9"',
    )
    path = tmp_path / "version-drift.toml"
    path.write_text(text, encoding="utf-8")

    report = audit_project_governance(PROJECT_ROOT, governance_path=path)
    checks = {check.name: check for check in report.checks}

    assert report.is_consistent is False
    assert checks["framework_version"].passed is False


def test_governance_audit_detects_missing_work_package_document(
    tmp_path: Path,
) -> None:
    text = GOVERNANCE_PATH.read_text(encoding="utf-8").replace(
        'document = "docs/work-packages/wp-data-001.md"',
        'document = "docs/work-packages/missing.md"',
    )
    path = tmp_path / "missing-package.toml"
    path.write_text(text, encoding="utf-8")

    report = audit_project_governance(PROJECT_ROOT, governance_path=path)
    checks = {check.name: check for check in report.checks}

    assert report.is_consistent is False
    assert checks["work_package:WP-DATA-001"].passed is False


def test_governance_rejects_unknown_work_package_dependency(tmp_path: Path) -> None:
    text = GOVERNANCE_PATH.read_text(encoding="utf-8").replace(
        'depends_on = ["WP-DATA-001"]',
        'depends_on = ["WP-UNKNOWN-999"]',
        1,
    )
    path = tmp_path / "unknown-dependency.toml"
    path.write_text(text, encoding="utf-8")

    with pytest.raises(ValueError, match="unknown work package dependencies"):
        load_project_governance(path)
