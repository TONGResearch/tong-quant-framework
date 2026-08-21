import json
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from hashlib import sha256

from tong_quant.domain.enums import (
    AvailabilityPrecision,
    DataTrustLevel,
    PITReadinessClassification,
)
from tong_quant.domain.models import require_timezone
from tong_quant.version import (
    DATABASE_SCHEMA_VERSION,
    EVIDENCE_READINESS_VERSION,
    FRAMEWORK_VERSION,
)


class EvidenceArtifactRole(StrEnum):
    READINESS_DASHBOARD = "readiness_dashboard"
    READINESS_GAP = "readiness_gap"
    PROVIDER_CAPABILITIES = "provider_capabilities"
    QUALITY_AUDIT = "quality_audit"
    OPERATIONAL_DATABASE = "operational_database"
    SUPPORTING_DOCUMENT = "supporting_document"


class EvidenceArtifactStatus(StrEnum):
    AVAILABLE = "available"
    STALE = "stale"
    MISSING = "missing"


class EvidenceConclusionCause(StrEnum):
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    OBSERVED_QUALITY_FAILURE = "observed_quality_failure"
    EXTERNAL_PROVIDER_RESTRICTION = "external_provider_restriction"
    MIXED = "mixed"
    SUFFICIENT_FOR_REVIEW = "sufficient_for_review"


@dataclass(frozen=True, slots=True)
class EvidenceArtifact:
    artifact_id: str
    role: EvidenceArtifactRole
    source_path: str
    status: EvidenceArtifactStatus
    content_hash: str
    observed_at: datetime | None
    model_versions: tuple[str, ...]
    datasets: tuple[str, ...]
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if len(self.artifact_id) != 64:
            raise ValueError("evidence artifact ID must be a SHA-256 digest")
        if not self.source_path.strip():
            raise ValueError("evidence artifact source path is required")
        if self.status is EvidenceArtifactStatus.MISSING:
            if self.content_hash or self.observed_at is not None:
                raise ValueError("missing evidence artifact cannot claim content")
        elif len(self.content_hash) != 64:
            raise ValueError("available evidence artifact requires a content hash")
        if self.observed_at is not None:
            require_timezone(self.observed_at, "evidence artifact observed_at")
        if tuple(sorted(set(self.model_versions))) != self.model_versions:
            raise ValueError("evidence artifact versions must be sorted and unique")
        if tuple(sorted(set(self.datasets))) != self.datasets:
            raise ValueError("evidence artifact datasets must be sorted and unique")


@dataclass(frozen=True, slots=True)
class OperationalDatasetEvidence:
    dataset: str
    contract_check_count: int = 0
    contract_observation_days: float = 0
    baseline_count: int = 0
    baseline_continuity_ratio: float | None = None
    baseline_field_coverage_ratio: float | None = None
    baseline_success_ratio: float | None = None
    artifact_capture_count: int = 0
    artifact_failure_count: int = 0
    calibration_completed_count: int = 0
    calibration_unavailable_count: int = 0
    calibration_incompatible_count: int = 0
    provider_conflict_count: int = 0
    high_conflict_count: int = 0
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.dataset.strip():
            raise ValueError("operational evidence dataset is required")
        counts = (
            self.contract_check_count,
            self.baseline_count,
            self.artifact_capture_count,
            self.artifact_failure_count,
            self.calibration_completed_count,
            self.calibration_unavailable_count,
            self.calibration_incompatible_count,
            self.provider_conflict_count,
            self.high_conflict_count,
        )
        if min(counts) < 0 or self.contract_observation_days < 0:
            raise ValueError("operational evidence metrics cannot be negative")
        for value in (
            self.baseline_continuity_ratio,
            self.baseline_field_coverage_ratio,
            self.baseline_success_ratio,
        ):
            if value is not None and not 0 <= value <= 1:
                raise ValueError("operational evidence ratios must be between zero and one")
        if self.high_conflict_count > self.provider_conflict_count:
            raise ValueError("high conflicts cannot exceed all provider conflicts")


@dataclass(frozen=True, slots=True)
class DatasetEvidenceInput:
    dataset: str
    current_classification: PITReadinessClassification
    current_readiness_score: float
    trust_level: DataTrustLevel
    availability_precision: AvailabilityPrecision
    coverage_percent: float | None
    historical_continuity_score: float | None
    provider_consistency_score: float | None
    required_field_completeness: float | None
    date_validity: float | None
    primary_records: int | None
    secondary_status: str
    capability_status: str
    evidence_artifact_ids: tuple[str, ...]
    limitations: tuple[str, ...]
    missing_requirements: tuple[str, ...]
    operational: OperationalDatasetEvidence

    def __post_init__(self) -> None:
        if not self.dataset.strip():
            raise ValueError("dataset evidence identity is required")
        for value in (
            self.current_readiness_score,
            self.coverage_percent,
            self.historical_continuity_score,
            self.provider_consistency_score,
            self.required_field_completeness,
            self.date_validity,
        ):
            if value is not None and not 0 <= value <= 100:
                raise ValueError("dataset evidence scores must be between zero and 100")
        if self.primary_records is not None and self.primary_records < 0:
            raise ValueError("dataset evidence record count cannot be negative")
        if self.operational.dataset != self.dataset:
            raise ValueError("operational evidence belongs to another dataset")
        if len(self.evidence_artifact_ids) != len(set(self.evidence_artifact_ids)):
            raise ValueError("dataset evidence artifact references must be unique")


@dataclass(frozen=True, slots=True)
class EvidenceReadinessPolicy:
    artifact_stale_days: int = 45
    minimum_observation_days: int = 84
    minimum_contract_checks: int = 8
    caution_coverage_percent: float = 60
    caution_continuity_score: float = 60
    caution_consistency_score: float = 70
    caution_field_completeness: float = 90
    usable_coverage_percent: float = 90
    usable_continuity_score: float = 80
    usable_consistency_score: float = 85
    usable_field_completeness: float = 98
    version: str = EVIDENCE_READINESS_VERSION

    def __post_init__(self) -> None:
        if min(
            self.artifact_stale_days,
            self.minimum_observation_days,
            self.minimum_contract_checks,
        ) < 1:
            raise ValueError("evidence readiness policy intervals must be positive")
        thresholds = (
            self.caution_coverage_percent,
            self.caution_continuity_score,
            self.caution_consistency_score,
            self.caution_field_completeness,
            self.usable_coverage_percent,
            self.usable_continuity_score,
            self.usable_consistency_score,
            self.usable_field_completeness,
        )
        if any(not 0 <= value <= 100 for value in thresholds):
            raise ValueError("evidence readiness thresholds must be between zero and 100")
        if not self.version.strip():
            raise ValueError("evidence readiness policy version is required")


@dataclass(frozen=True, slots=True)
class EvidenceReadinessGate:
    name: str
    passed: bool
    observed: str
    required: str
    evidence_artifact_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.observed.strip() or not self.required.strip():
            raise ValueError("evidence readiness gate fields are required")


@dataclass(frozen=True, slots=True)
class DatasetEvidenceDecision:
    dataset: str
    current_classification: PITReadinessClassification
    proposed_classification: PITReadinessClassification
    effective_classification: PITReadinessClassification
    mechanical_score: float
    cause: EvidenceConclusionCause
    promotion_review_eligible: bool
    gates: tuple[EvidenceReadinessGate, ...]
    evidence_artifact_ids: tuple[str, ...]
    evidence: DatasetEvidenceInput
    blockers: tuple[str, ...]
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.dataset.strip() or not 0 <= self.mechanical_score <= 100:
            raise ValueError("dataset evidence decision is invalid")
        if self.effective_classification is not self.current_classification:
            raise ValueError("evidence reassessment cannot change effective classification")
        if self.evidence.dataset != self.dataset:
            raise ValueError("evidence decision contains another dataset's evidence")
        if self.promotion_review_eligible and (
            self.proposed_classification is self.current_classification
        ):
            raise ValueError("promotion review requires a proposed classification change")


@dataclass(frozen=True, slots=True)
class EvidenceReadinessReport:
    report_id: str
    assessed_at: datetime
    git_commit: str
    configuration_hash: str
    source_tree_hash: str
    migration_head: str
    artifacts: tuple[EvidenceArtifact, ...]
    decisions: tuple[DatasetEvidenceDecision, ...]
    current_overall_classification: PITReadinessClassification
    proposed_overall_classification: PITReadinessClassification
    effective_overall_classification: PITReadinessClassification
    historical_replay_ready: bool
    trading_freeze_remains: bool
    policy: EvidenceReadinessPolicy
    framework_version: str = FRAMEWORK_VERSION
    database_schema_version: str = DATABASE_SCHEMA_VERSION
    implementation_version: str = EVIDENCE_READINESS_VERSION

    def __post_init__(self) -> None:
        require_timezone(self.assessed_at, "evidence readiness assessed_at")
        if len(self.report_id) != 64:
            raise ValueError("evidence readiness report ID must be a SHA-256 digest")
        if len(self.git_commit) < 7:
            raise ValueError("evidence readiness report requires a Git commit")
        if any(len(value) != 64 for value in (self.configuration_hash, self.source_tree_hash)):
            raise ValueError("evidence readiness hashes must be SHA-256 digests")
        if not self.migration_head.strip() or not self.decisions:
            raise ValueError("evidence readiness report identity and decisions are required")
        if tuple(sorted(item.dataset for item in self.decisions)) != tuple(
            item.dataset for item in self.decisions
        ):
            raise ValueError("evidence readiness decisions must be sorted by dataset")
        if self.effective_overall_classification is not self.current_overall_classification:
            raise ValueError("evidence report cannot automatically change overall readiness")
        if self.historical_replay_ready or not self.trading_freeze_remains:
            raise ValueError("evidence reassessment cannot unlock replay or trading")
        expected = _stable_hash(_report_content(self, include_report_id=False))
        if self.report_id != expected:
            raise ValueError("evidence readiness report hash does not match content")


@dataclass(frozen=True, slots=True)
class EvidenceReadinessEvaluator:
    policy: EvidenceReadinessPolicy = EvidenceReadinessPolicy()

    def evaluate(
        self,
        *,
        assessed_at: datetime,
        git_commit: str,
        configuration_hash: str,
        source_tree_hash: str,
        migration_head: str,
        artifacts: tuple[EvidenceArtifact, ...],
        inputs: tuple[DatasetEvidenceInput, ...],
    ) -> EvidenceReadinessReport:
        require_timezone(assessed_at, "evidence readiness assessed_at")
        artifact_by_id = {item.artifact_id: item for item in artifacts}
        if len(artifact_by_id) != len(artifacts):
            raise ValueError("evidence readiness artifacts must be unique")
        if any(
            artifact_id not in artifact_by_id
            for item in inputs
            for artifact_id in item.evidence_artifact_ids
        ):
            raise ValueError("dataset evidence references an unknown artifact")
        decisions = tuple(
            sorted(
                (
                    _decision(item, artifact_by_id, self.policy)
                    for item in inputs
                ),
                key=lambda item: item.dataset,
            )
        )
        current = _worst(tuple(item.current_classification for item in decisions))
        proposed = _worst(tuple(item.proposed_classification for item in decisions))
        sorted_artifacts = tuple(
            sorted(artifacts, key=lambda item: (item.role, item.source_path))
        )
        report_id = _stable_hash(
            _report_values_content(
                report_id="",
                include_report_id=False,
                assessed_at=assessed_at,
                git_commit=git_commit,
                configuration_hash=configuration_hash,
                source_tree_hash=source_tree_hash,
                migration_head=migration_head,
                artifacts=sorted_artifacts,
                decisions=decisions,
                current_overall_classification=current,
                proposed_overall_classification=proposed,
                effective_overall_classification=current,
                historical_replay_ready=False,
                trading_freeze_remains=True,
                policy=self.policy,
                framework_version=FRAMEWORK_VERSION,
                database_schema_version=DATABASE_SCHEMA_VERSION,
                implementation_version=EVIDENCE_READINESS_VERSION,
            )
        )
        return EvidenceReadinessReport(
            report_id=report_id,
            assessed_at=assessed_at,
            git_commit=git_commit,
            configuration_hash=configuration_hash,
            source_tree_hash=source_tree_hash,
            migration_head=migration_head,
            artifacts=sorted_artifacts,
            decisions=decisions,
            current_overall_classification=current,
            proposed_overall_classification=proposed,
            effective_overall_classification=current,
            historical_replay_ready=False,
            trading_freeze_remains=True,
            policy=self.policy,
        )


def evidence_readiness_json(report: EvidenceReadinessReport) -> dict[str, object]:
    return _report_content(report, include_report_id=True)


def serialize_evidence_readiness(report: EvidenceReadinessReport) -> str:
    return json.dumps(evidence_readiness_json(report), indent=2, sort_keys=True)


def render_evidence_readiness_markdown(report: EvidenceReadinessReport) -> str:
    lines = [
        "# Evidence-Backed PIT Readiness Reassessment",
        "",
        f"- Report ID: `{report.report_id}`",
        f"- Assessed at: `{report.assessed_at.isoformat()}`",
        f"- Git commit: `{report.git_commit}`",
        f"- Framework/schema: `{report.framework_version}` / "
        f"`{report.database_schema_version}`",
        f"- Migration head: `{report.migration_head}`",
        f"- Current overall: `{report.current_overall_classification.value}`",
        f"- Proposed overall: `{report.proposed_overall_classification.value}`",
        f"- Effective overall: `{report.effective_overall_classification.value}`",
        "- Historical Replay ready: `false`",
        "- Trading freeze remains: `true`",
        "",
        "## Dataset Decisions",
        "",
        "| Dataset | Current | Proposed | Effective | Score | Cause | Review |",
        "|---|---|---|---|---:|---|---|",
    ]
    for decision in report.decisions:
        lines.append(
            f"| {decision.dataset} | {decision.current_classification.value} | "
            f"{decision.proposed_classification.value} | "
            f"{decision.effective_classification.value} | "
            f"{decision.mechanical_score:.2f} | {decision.cause.value} | "
            f"{'eligible' if decision.promotion_review_eligible else 'not eligible'} |"
        )
    lines.extend(["", "## Evidence Inventory", ""])
    for artifact in report.artifacts:
        observed = artifact.observed_at.isoformat() if artifact.observed_at else "unknown"
        lines.append(
            f"- `{artifact.role.value}` `{artifact.status.value}`: "
            f"`{artifact.source_path}`; observed `{observed}`; "
            f"hash `{artifact.content_hash or 'missing'}`"
        )
    lines.extend(["", "## Blockers", ""])
    for decision in report.decisions:
        lines.append(f"### {decision.dataset}")
        lines.append("")
        for blocker in decision.blockers:
            lines.append(f"- {blocker}")
        lines.append("")
    lines.extend(
        [
            "This report is evidence for human governance review. It does not "
            "change provider trust, PIT classification, Historical Replay "
            "eligibility, Portfolio authority, Notification behavior, or any "
            "trading boundary.",
            "",
        ]
    )
    return "\n".join(lines)


def _decision(
    item: DatasetEvidenceInput,
    artifacts: dict[str, EvidenceArtifact],
    policy: EvidenceReadinessPolicy,
) -> DatasetEvidenceDecision:
    referenced = tuple(artifacts[item_id] for item_id in item.evidence_artifact_ids)
    available_artifacts = tuple(
        artifact for artifact in referenced if artifact.status is EvidenceArtifactStatus.AVAILABLE
    )
    fresh = bool(referenced) and len(available_artifacts) == len(referenced)
    secondary_available = item.secondary_status.lower() in {"available", "completed"}
    capability_available = item.capability_status.lower() in {
        "available",
        "degraded",
        "completed",
    }
    operational = item.operational
    operational_history = (
        operational.contract_check_count >= policy.minimum_contract_checks
        and operational.contract_observation_days >= policy.minimum_observation_days
        and (operational.baseline_continuity_ratio or 0) >= 0.75
        and (operational.baseline_field_coverage_ratio or 0) >= 0.90
    )
    gates = (
        _gate(
            "artifacts_fresh",
            fresh,
            _artifact_status_text(referenced),
            "all available",
            item,
        ),
        _score_gate(
            "coverage_measured",
            item.coverage_percent,
            0,
            item,
            measured=True,
        ),
        _score_gate(
            "coverage_caution",
            item.coverage_percent,
            policy.caution_coverage_percent,
            item,
        ),
        _score_gate(
            "continuity_caution",
            item.historical_continuity_score,
            policy.caution_continuity_score,
            item,
        ),
        _score_gate(
            "consistency_caution",
            item.provider_consistency_score,
            policy.caution_consistency_score,
            item,
        ),
        _score_gate(
            "field_completeness",
            item.required_field_completeness,
            policy.caution_field_completeness,
            item,
        ),
        _gate(
            "secondary_available",
            secondary_available,
            item.secondary_status or "unknown",
            "available",
            item,
        ),
        _gate(
            "capability_available",
            capability_available,
            item.capability_status or "unknown",
            "available or degraded",
            item,
        ),
        _gate(
            "trust_caution",
            _trust_rank(item.trust_level) >= _trust_rank(DataTrustLevel.MEDIUM),
            item.trust_level.value,
            "medium or stronger",
            item,
        ),
        _gate(
            "operational_history",
            operational_history,
            (
                f"{operational.contract_check_count} checks/"
                f"{operational.contract_observation_days:.1f} days"
            ),
            (
                f">={policy.minimum_contract_checks} checks/"
                f"{policy.minimum_observation_days} days with baseline coverage"
            ),
            item,
        ),
        _gate(
            "no_high_conflicts",
            operational.high_conflict_count == 0,
            str(operational.high_conflict_count),
            "0",
            item,
        ),
    )
    caution = all(
        gate.passed
        for gate in gates
        if gate.name
        in {
            "coverage_measured",
            "coverage_caution",
            "continuity_caution",
            "consistency_caution",
            "field_completeness",
            "secondary_available",
            "capability_available",
            "trust_caution",
            "no_high_conflicts",
        }
    )
    usable = caution and all(
        (
            _at_least(item.coverage_percent, policy.usable_coverage_percent),
            _at_least(item.historical_continuity_score, policy.usable_continuity_score),
            _at_least(item.provider_consistency_score, policy.usable_consistency_score),
            _at_least(item.required_field_completeness, policy.usable_field_completeness),
            _trust_rank(item.trust_level) >= _trust_rank(DataTrustLevel.HIGH),
            item.availability_precision
            in {AvailabilityPrecision.EXACT, AvailabilityPrecision.DATE_ONLY},
            fresh,
            operational_history,
        )
    )
    proposed = (
        PITReadinessClassification.USABLE
        if usable
        else PITReadinessClassification.CAUTION
        if caution
        else PITReadinessClassification.UNSUITABLE
    )
    artifact_blockers = (
        ("Current evidence artifacts are stale or missing",) if not fresh else ()
    )
    blockers = tuple(
        dict.fromkeys(
            (
                *(
                    f"Gate failed: {gate.name} "
                    f"({gate.observed}; requires {gate.required})"
                    for gate in gates
                    if not gate.passed
                ),
                *item.missing_requirements,
                *artifact_blockers,
            )
        )
    )
    missing_evidence = any(
        not gate.passed
        for gate in gates
        if gate.name in {"artifacts_fresh", "coverage_measured", "operational_history"}
    )
    observed_failure = any(
        not gate.passed
        for gate in gates
        if gate.name
        in {
            "coverage_caution",
            "continuity_caution",
            "field_completeness",
            "no_high_conflicts",
        }
        and gate.observed not in {"unknown", "N/A"}
    )
    restricted = not secondary_available or not capability_available
    cause = _cause(missing_evidence, observed_failure, restricted, proposed)
    score = _mechanical_score(item, operational_history)
    promotion_review = (
        proposed is not item.current_classification
        and fresh
        and operational_history
        and not blockers
    )
    return DatasetEvidenceDecision(
        dataset=item.dataset,
        current_classification=item.current_classification,
        proposed_classification=proposed,
        effective_classification=item.current_classification,
        mechanical_score=score,
        cause=cause,
        promotion_review_eligible=promotion_review,
        gates=gates,
        evidence_artifact_ids=item.evidence_artifact_ids,
        evidence=item,
        blockers=blockers,
        limitations=tuple(dict.fromkeys((*item.limitations, *operational.limitations))),
    )


def _gate(
    name: str,
    passed: bool,
    observed: str,
    required: str,
    item: DatasetEvidenceInput,
) -> EvidenceReadinessGate:
    return EvidenceReadinessGate(
        name,
        passed,
        observed or "unknown",
        required,
        item.evidence_artifact_ids,
    )


def _score_gate(
    name: str,
    value: float | None,
    threshold: float,
    item: DatasetEvidenceInput,
    *,
    measured: bool = False,
) -> EvidenceReadinessGate:
    passed = value is not None if measured else _at_least(value, threshold)
    required = "measured" if measured else f">={threshold:.2f}"
    return _gate(name, passed, "unknown" if value is None else f"{value:.2f}", required, item)


def _mechanical_score(item: DatasetEvidenceInput, operational_history: bool) -> float:
    values = (
        (item.coverage_percent or 0, 0.25),
        (item.historical_continuity_score or 0, 0.25),
        (item.provider_consistency_score or 0, 0.20),
        (item.required_field_completeness or 0, 0.15),
        (_trust_rank(item.trust_level) / 4 * 100, 0.10),
        (100 if operational_history else 0, 0.05),
    )
    return round(sum(value * weight for value, weight in values), 2)


def _cause(
    missing: bool,
    observed_failure: bool,
    restricted: bool,
    proposed: PITReadinessClassification,
) -> EvidenceConclusionCause:
    active = sum((missing, observed_failure, restricted))
    if active > 1:
        return EvidenceConclusionCause.MIXED
    if restricted:
        return EvidenceConclusionCause.EXTERNAL_PROVIDER_RESTRICTION
    if observed_failure:
        return EvidenceConclusionCause.OBSERVED_QUALITY_FAILURE
    if missing:
        return EvidenceConclusionCause.INSUFFICIENT_EVIDENCE
    if proposed is not PITReadinessClassification.UNSUITABLE:
        return EvidenceConclusionCause.SUFFICIENT_FOR_REVIEW
    return EvidenceConclusionCause.INSUFFICIENT_EVIDENCE


def _artifact_status_text(artifacts: tuple[EvidenceArtifact, ...]) -> str:
    if not artifacts:
        return "none"
    return ",".join(sorted({item.status.value for item in artifacts}))


def _at_least(value: float | None, threshold: float) -> bool:
    return value is not None and value >= threshold


def _trust_rank(value: DataTrustLevel) -> int:
    return {
        DataTrustLevel.UNKNOWN: 0,
        DataTrustLevel.LOW: 1,
        DataTrustLevel.MEDIUM: 2,
        DataTrustLevel.HIGH: 3,
        DataTrustLevel.VERIFIED: 4,
    }[value]


def _worst(
    values: tuple[PITReadinessClassification, ...],
) -> PITReadinessClassification:
    rank = {
        PITReadinessClassification.USABLE: 0,
        PITReadinessClassification.CAUTION: 1,
        PITReadinessClassification.UNSUITABLE: 2,
    }
    return max(values, key=rank.__getitem__)


def _report_content(
    report: EvidenceReadinessReport,
    *,
    include_report_id: bool,
) -> dict[str, object]:
    return _report_values_content(
        report_id=report.report_id,
        include_report_id=include_report_id,
        assessed_at=report.assessed_at,
        git_commit=report.git_commit,
        configuration_hash=report.configuration_hash,
        source_tree_hash=report.source_tree_hash,
        migration_head=report.migration_head,
        artifacts=report.artifacts,
        decisions=report.decisions,
        current_overall_classification=report.current_overall_classification,
        proposed_overall_classification=report.proposed_overall_classification,
        effective_overall_classification=report.effective_overall_classification,
        historical_replay_ready=report.historical_replay_ready,
        trading_freeze_remains=report.trading_freeze_remains,
        policy=report.policy,
        framework_version=report.framework_version,
        database_schema_version=report.database_schema_version,
        implementation_version=report.implementation_version,
    )


def _report_values_content(
    *,
    report_id: str,
    include_report_id: bool,
    assessed_at: datetime,
    git_commit: str,
    configuration_hash: str,
    source_tree_hash: str,
    migration_head: str,
    artifacts: tuple[EvidenceArtifact, ...],
    decisions: tuple[DatasetEvidenceDecision, ...],
    current_overall_classification: PITReadinessClassification,
    proposed_overall_classification: PITReadinessClassification,
    effective_overall_classification: PITReadinessClassification,
    historical_replay_ready: bool,
    trading_freeze_remains: bool,
    policy: EvidenceReadinessPolicy,
    framework_version: str,
    database_schema_version: str,
    implementation_version: str,
) -> dict[str, object]:
    document: dict[str, object] = {
        "assessed_at": assessed_at.isoformat(),
        "git_commit": git_commit,
        "configuration_hash": configuration_hash,
        "source_tree_hash": source_tree_hash,
        "migration_head": migration_head,
        "framework_version": framework_version,
        "database_schema_version": database_schema_version,
        "implementation_version": implementation_version,
        "artifacts": [_artifact_document(item) for item in artifacts],
        "decisions": [_decision_document(item) for item in decisions],
        "current_overall_classification": current_overall_classification.value,
        "proposed_overall_classification": proposed_overall_classification.value,
        "effective_overall_classification": effective_overall_classification.value,
        "historical_replay_ready": historical_replay_ready,
        "trading_freeze_remains": trading_freeze_remains,
        "policy": _policy_document(policy),
    }
    if include_report_id:
        document["report_id"] = report_id
    return document


def _artifact_document(item: EvidenceArtifact) -> dict[str, object]:
    return {
        "artifact_id": item.artifact_id,
        "role": item.role.value,
        "source_path": item.source_path,
        "status": item.status.value,
        "content_hash": item.content_hash,
        "observed_at": None if item.observed_at is None else item.observed_at.isoformat(),
        "model_versions": list(item.model_versions),
        "datasets": list(item.datasets),
        "limitations": list(item.limitations),
    }


def _decision_document(item: DatasetEvidenceDecision) -> dict[str, object]:
    return {
        "dataset": item.dataset,
        "current_classification": item.current_classification.value,
        "proposed_classification": item.proposed_classification.value,
        "effective_classification": item.effective_classification.value,
        "mechanical_score": item.mechanical_score,
        "cause": item.cause.value,
        "promotion_review_eligible": item.promotion_review_eligible,
        "gates": [
            {
                "name": gate.name,
                "passed": gate.passed,
                "observed": gate.observed,
                "required": gate.required,
                "evidence_artifact_ids": list(gate.evidence_artifact_ids),
            }
            for gate in item.gates
        ],
        "evidence_artifact_ids": list(item.evidence_artifact_ids),
        "evidence": _input_document(item.evidence),
        "blockers": list(item.blockers),
        "limitations": list(item.limitations),
    }


def _input_document(item: DatasetEvidenceInput) -> dict[str, object]:
    operational = item.operational
    return {
        "current_readiness_score": item.current_readiness_score,
        "trust_level": item.trust_level.value,
        "availability_precision": item.availability_precision.value,
        "coverage_percent": item.coverage_percent,
        "historical_continuity_score": item.historical_continuity_score,
        "provider_consistency_score": item.provider_consistency_score,
        "required_field_completeness": item.required_field_completeness,
        "date_validity": item.date_validity,
        "primary_records": item.primary_records,
        "secondary_status": item.secondary_status,
        "capability_status": item.capability_status,
        "missing_requirements": list(item.missing_requirements),
        "operational": {
            "contract_check_count": operational.contract_check_count,
            "contract_observation_days": operational.contract_observation_days,
            "baseline_count": operational.baseline_count,
            "baseline_continuity_ratio": operational.baseline_continuity_ratio,
            "baseline_field_coverage_ratio": (
                operational.baseline_field_coverage_ratio
            ),
            "baseline_success_ratio": operational.baseline_success_ratio,
            "artifact_capture_count": operational.artifact_capture_count,
            "artifact_failure_count": operational.artifact_failure_count,
            "calibration_completed_count": operational.calibration_completed_count,
            "calibration_unavailable_count": (
                operational.calibration_unavailable_count
            ),
            "calibration_incompatible_count": (
                operational.calibration_incompatible_count
            ),
            "provider_conflict_count": operational.provider_conflict_count,
            "high_conflict_count": operational.high_conflict_count,
        },
    }


def _policy_document(policy: EvidenceReadinessPolicy) -> dict[str, object]:
    return {
        "artifact_stale_days": policy.artifact_stale_days,
        "minimum_observation_days": policy.minimum_observation_days,
        "minimum_contract_checks": policy.minimum_contract_checks,
        "caution_coverage_percent": policy.caution_coverage_percent,
        "caution_continuity_score": policy.caution_continuity_score,
        "caution_consistency_score": policy.caution_consistency_score,
        "caution_field_completeness": policy.caution_field_completeness,
        "usable_coverage_percent": policy.usable_coverage_percent,
        "usable_continuity_score": policy.usable_continuity_score,
        "usable_consistency_score": policy.usable_consistency_score,
        "usable_field_completeness": policy.usable_field_completeness,
        "version": policy.version,
    }


def stable_evidence_hash(value: object) -> str:
    return _stable_hash(value)


def _stable_hash(value: object) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


__all__ = [
    "DatasetEvidenceDecision",
    "DatasetEvidenceInput",
    "EvidenceArtifact",
    "EvidenceArtifactRole",
    "EvidenceArtifactStatus",
    "EvidenceConclusionCause",
    "EvidenceReadinessEvaluator",
    "EvidenceReadinessGate",
    "EvidenceReadinessPolicy",
    "EvidenceReadinessReport",
    "OperationalDatasetEvidence",
    "evidence_readiness_json",
    "render_evidence_readiness_markdown",
    "serialize_evidence_readiness",
    "stable_evidence_hash",
]
