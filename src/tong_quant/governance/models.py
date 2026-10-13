from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class GovernanceBaseline:
    framework_version: str
    database_schema_version: str
    migration_head: str
    current_phase: str
    canonical_status_document: Path


@dataclass(frozen=True, slots=True)
class FreezePolicy:
    live_trading_frozen: bool
    paper_trading_allowed: bool
    broker_sandbox_allowed: bool
    required_execution_mode: str
    allow_live_orders: bool
    required_notification_mode: str
    reason: str
    forbidden_capabilities: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.live_trading_frozen:
            raise ValueError("live trading freeze must remain enabled")
        if self.required_execution_mode != "disabled" or self.allow_live_orders:
            raise ValueError("governance must keep execution disabled and live orders off")
        if self.required_notification_mode != "disabled":
            raise ValueError("governance must keep notifications disabled by default")
        if not self.reason.strip() or not self.forbidden_capabilities:
            raise ValueError("freeze policy requires a reason and forbidden capabilities")


@dataclass(frozen=True, slots=True)
class ReadinessSnapshot:
    production: str
    research: str
    validation: str
    portfolio: str
    pit: str

    def __post_init__(self) -> None:
        if self.pit != "unsuitable":
            raise ValueError("PIT readiness cannot be promoted in governance configuration")
        if self.production != "not_ready":
            raise ValueError("production readiness must remain not_ready")


@dataclass(frozen=True, slots=True)
class QualityPolicy:
    required_commands: tuple[str, ...]
    required_documents: tuple[Path, ...]

    def __post_init__(self) -> None:
        if not self.required_commands or not self.required_documents:
            raise ValueError("quality policy requires commands and documents")
        if len(self.required_commands) != len(set(self.required_commands)):
            raise ValueError("quality commands must be unique")


@dataclass(frozen=True, slots=True)
class NextPhase:
    objective: str
    promotion_requirement: str


@dataclass(frozen=True, slots=True)
class WorkPackage:
    package_id: str
    title: str
    status: str
    document: Path
    depends_on: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.package_id.startswith("WP-"):
            raise ValueError("work package identifiers must start with WP-")
        if self.status not in {"ready", "planned", "blocked", "completed"}:
            raise ValueError(f"unsupported work package status: {self.status}")
        if not self.title.strip():
            raise ValueError("work package title is required")


@dataclass(frozen=True, slots=True)
class ProjectGovernance:
    baseline: GovernanceBaseline
    freeze: FreezePolicy
    readiness: ReadinessSnapshot
    quality: QualityPolicy
    next_phase: NextPhase
    work_packages: tuple[WorkPackage, ...]

    def __post_init__(self) -> None:
        identifiers = tuple(item.package_id for item in self.work_packages)
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("work package identifiers must be unique")
        known = set(identifiers)
        unknown = sorted(
            dependency
            for item in self.work_packages
            for dependency in item.depends_on
            if dependency not in known
        )
        if unknown:
            raise ValueError(f"unknown work package dependencies: {', '.join(unknown)}")
        if not any(item.status == "ready" for item in self.work_packages):
            raise ValueError("at least one work package must be ready")
        by_id = {item.package_id: item for item in self.work_packages}
        invalid_ready = sorted(
            item.package_id
            for item in self.work_packages
            if item.status == "ready"
            and any(by_id[dependency].status != "completed" for dependency in item.depends_on)
        )
        if invalid_ready:
            raise ValueError(
                "ready work packages have incomplete dependencies: "
                f"{', '.join(invalid_ready)}"
            )
        _validate_dependency_graph(self.work_packages)


def project_governance_from_dict(raw: dict[str, Any]) -> ProjectGovernance:
    baseline_raw = raw["baseline"]
    freeze_raw = raw["freeze"]
    readiness_raw = raw["readiness"]
    quality_raw = raw["quality"]
    next_phase_raw = raw["next_phase"]
    return ProjectGovernance(
        baseline=GovernanceBaseline(
            framework_version=str(baseline_raw["framework_version"]),
            database_schema_version=str(baseline_raw["database_schema_version"]),
            migration_head=str(baseline_raw["migration_head"]),
            current_phase=str(baseline_raw["current_phase"]),
            canonical_status_document=Path(baseline_raw["canonical_status_document"]),
        ),
        freeze=FreezePolicy(
            live_trading_frozen=bool(freeze_raw["live_trading_frozen"]),
            paper_trading_allowed=bool(freeze_raw["paper_trading_allowed"]),
            broker_sandbox_allowed=bool(freeze_raw["broker_sandbox_allowed"]),
            required_execution_mode=str(freeze_raw["required_execution_mode"]),
            allow_live_orders=bool(freeze_raw["allow_live_orders"]),
            required_notification_mode=str(
                freeze_raw["required_notification_mode"]
            ),
            reason=str(freeze_raw["reason"]),
            forbidden_capabilities=tuple(freeze_raw["forbidden_capabilities"]),
        ),
        readiness=ReadinessSnapshot(**readiness_raw),
        quality=QualityPolicy(
            required_commands=tuple(quality_raw["required_commands"]),
            required_documents=tuple(
                Path(item) for item in quality_raw["required_documents"]
            ),
        ),
        next_phase=NextPhase(**next_phase_raw),
        work_packages=tuple(
            WorkPackage(
                package_id=str(item["id"]),
                title=str(item["title"]),
                status=str(item["status"]),
                document=Path(item["document"]),
                depends_on=tuple(item["depends_on"]),
            )
            for item in raw["work_packages"]
        ),
    )


def _validate_dependency_graph(work_packages: tuple[WorkPackage, ...]) -> None:
    dependencies = {
        item.package_id: item.depends_on for item in work_packages
    }
    visiting: list[str] = []
    visited: set[str] = set()

    def visit(package_id: str) -> None:
        if package_id in visiting:
            cycle_start = visiting.index(package_id)
            cycle = (*visiting[cycle_start:], package_id)
            raise ValueError(f"work package dependency cycle: {' -> '.join(cycle)}")
        if package_id in visited:
            return
        visiting.append(package_id)
        for dependency in dependencies[package_id]:
            visit(dependency)
        visiting.pop()
        visited.add(package_id)

    for package_id in dependencies:
        visit(package_id)


__all__ = [
    "FreezePolicy",
    "GovernanceBaseline",
    "NextPhase",
    "ProjectGovernance",
    "QualityPolicy",
    "ReadinessSnapshot",
    "WorkPackage",
    "project_governance_from_dict",
]
