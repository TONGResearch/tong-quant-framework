import json
import sqlite3
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tong_quant.data.evidence_readiness import (
    DatasetEvidenceInput,
    EvidenceArtifact,
    EvidenceArtifactRole,
    EvidenceArtifactStatus,
    EvidenceConclusionCause,
    EvidenceReadinessEvaluator,
    OperationalDatasetEvidence,
    stable_evidence_hash,
)
from tong_quant.data.evidence_sources import (
    EvidenceSourcePaths,
    load_evidence_sources,
)
from tong_quant.domain.enums import (
    AvailabilityPrecision,
    DataTrustLevel,
    PITReadinessClassification,
)

NOW = datetime(2026, 8, 22, tzinfo=UTC)
COMMIT = "7e680f1dbd130b5d8e5c73df2bea829984cd08a8"


def test_evidence_report_is_deterministic_and_cannot_promote_automatically() -> None:
    artifact = _artifact(EvidenceArtifactStatus.AVAILABLE)
    item = _input(
        artifact.artifact_id,
        operational=OperationalDatasetEvidence(
            dataset="fundamentals",
            contract_check_count=10,
            contract_observation_days=90,
            baseline_count=1,
            baseline_continuity_ratio=0.95,
            baseline_field_coverage_ratio=0.99,
            baseline_success_ratio=0.98,
        ),
    )
    evaluator = EvidenceReadinessEvaluator()

    first = _evaluate(evaluator, (artifact,), (item,))
    second = _evaluate(evaluator, (artifact,), (item,))

    assert first.report_id == second.report_id
    assert first.decisions[0].proposed_classification is (
        PITReadinessClassification.USABLE
    )
    assert first.decisions[0].effective_classification is (
        PITReadinessClassification.UNSUITABLE
    )
    assert first.decisions[0].promotion_review_eligible is True
    assert first.historical_replay_ready is False
    assert first.trading_freeze_remains is True


def test_missing_measurements_and_provider_restrictions_remain_explicit() -> None:
    artifact = _artifact(EvidenceArtifactStatus.STALE)
    item = replace(
        _input(artifact.artifact_id),
        coverage_percent=None,
        provider_consistency_score=None,
        secondary_status="unavailable",
        capability_status="permission_restricted",
    )

    decision = _evaluate(
        EvidenceReadinessEvaluator(),
        (artifact,),
        (item,),
    ).decisions[0]

    measured = next(gate for gate in decision.gates if gate.name == "coverage_measured")
    assert measured.observed == "unknown"
    assert decision.proposed_classification is PITReadinessClassification.UNSUITABLE
    assert decision.cause is EvidenceConclusionCause.MIXED
    assert any("artifacts_fresh" in blocker for blocker in decision.blockers)
    assert any("secondary_available" in blocker for blocker in decision.blockers)


def test_report_hash_rejects_tampering() -> None:
    artifact = _artifact(EvidenceArtifactStatus.AVAILABLE)
    report = _evaluate(
        EvidenceReadinessEvaluator(),
        (artifact,),
        (_input(artifact.artifact_id),),
    )

    with pytest.raises(ValueError, match="hash does not match"):
        replace(report, source_tree_hash="f" * 64)


def test_source_loader_preserves_stale_and_missing_evidence(tmp_path: Path) -> None:
    paths = _source_paths(tmp_path)
    generated_at = "2026-06-21T08:37:38+00:00"
    _write_json(
        paths.readiness_dashboard,
        {
            "generated_at": generated_at,
            "model_version": "dashboard-v1",
            "datasets": [
                {
                    "dataset": "fundamentals",
                    "coverage_percent": None,
                    "historical_continuity_score": 50,
                    "provider_consistency_score": None,
                    "primary_records": 10,
                    "secondary_status": "unavailable",
                    "trust_level": "medium",
                    "availability_precision": "date_only",
                    "pit_readiness": {
                        "classification": "unsuitable",
                        "readiness_score": 20,
                    },
                    "known_limitations": ["coverage is unmeasurable"],
                }
            ],
        },
    )
    _write_json(
        paths.readiness_gap,
        {
            "generated_at": generated_at,
            "datasets": [
                {
                    "dataset": "fundamentals",
                    "current_classification": "unsuitable",
                    "missing_requirements": ["secondary evidence"],
                }
            ],
        },
    )
    _write_json(
        paths.quality_audit,
        {
            "generated_at": generated_at,
            "datasets": [
                {
                    "dataset": "fundamentals",
                    "required_field_completeness": 0.95,
                    "date_validity": 1.0,
                    "limitations": [],
                }
            ],
        },
    )
    _write_json(
        paths.provider_capabilities,
        {
            "generated_at": "2026-07-03T03:15:17+00:00",
            "datasets": [
                {
                    "dataset": "fundamentals",
                    "status": "permission_restricted",
                    "reason": "provider account tier",
                }
            ],
        },
    )

    loaded = load_evidence_sources(paths, assessed_at=NOW)
    statuses = {artifact.role: artifact.status for artifact in loaded.artifacts}
    fundamentals = next(item for item in loaded.inputs if item.dataset == "fundamentals")

    assert statuses[EvidenceArtifactRole.READINESS_DASHBOARD] is (
        EvidenceArtifactStatus.STALE
    )
    assert statuses[EvidenceArtifactRole.OPERATIONAL_DATABASE] is (
        EvidenceArtifactStatus.MISSING
    )
    assert fundamentals.coverage_percent is None
    assert fundamentals.operational.contract_check_count == 0
    assert len(fundamentals.evidence_artifact_ids) == len(loaded.artifacts)
    assert any(item.dataset == "global_daily_bars" for item in loaded.inputs)


def test_later_capability_evidence_supersedes_old_missing_token_message(
    tmp_path: Path,
) -> None:
    paths = _source_paths(tmp_path)
    generated_at = "2026-08-20T00:00:00+00:00"
    _write_json(
        paths.readiness_dashboard,
        {
            "generated_at": generated_at,
            "datasets": [
                {
                    "dataset": "fundamentals",
                    "known_limitations": [
                        "secondary provider unavailable: TUSHARE_TOKEN is not configured"
                    ],
                }
            ],
        },
    )
    _write_json(paths.readiness_gap, {"generated_at": generated_at, "datasets": []})
    _write_json(paths.quality_audit, {"generated_at": generated_at, "datasets": []})
    _write_json(
        paths.provider_capabilities,
        {
            "generated_at": generated_at,
            "environment": {"configured": True},
            "datasets": [
                {
                    "dataset": "fundamentals",
                    "status": "unavailable",
                    "reason": "account permission is insufficient",
                }
            ],
        },
    )

    loaded = load_evidence_sources(paths, assessed_at=NOW)
    fundamentals = next(item for item in loaded.inputs if item.dataset == "fundamentals")

    assert "TUSHARE_TOKEN is not configured" not in " ".join(
        fundamentals.limitations
    )
    assert "superseded" in " ".join(fundamentals.limitations)
    assert "account permission is insufficient" in " ".join(
        fundamentals.limitations
    )


def test_source_loader_fails_closed_for_malformed_json(tmp_path: Path) -> None:
    paths = _source_paths(tmp_path)
    paths.readiness_dashboard.parent.mkdir(parents=True, exist_ok=True)
    paths.readiness_dashboard.write_text("{broken", encoding="utf-8")

    with pytest.raises(ValueError, match="malformed"):
        load_evidence_sources(paths, assessed_at=NOW)


def test_empty_operational_database_is_not_treated_as_observation_history(
    tmp_path: Path,
) -> None:
    paths = _source_paths(tmp_path)
    paths.operational_database.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(paths.operational_database):
        pass

    loaded = load_evidence_sources(paths, assessed_at=NOW)
    operational_artifact = next(
        item
        for item in loaded.artifacts
        if item.role is EvidenceArtifactRole.OPERATIONAL_DATABASE
    )
    daily_bars = next(
        item for item in loaded.inputs if item.dataset == "global_daily_bars"
    )

    assert operational_artifact.status is EvidenceArtifactStatus.AVAILABLE
    assert operational_artifact.content_hash == stable_evidence_hash({})
    assert daily_bars.operational.contract_check_count == 0
    assert daily_bars.operational.contract_observation_days == 0


def test_operational_database_aggregates_history_without_writing(
    tmp_path: Path,
) -> None:
    paths = _source_paths(tmp_path)
    with sqlite3.connect(paths.operational_database) as connection:
        connection.executescript(
            """
            CREATE TABLE provider_contract_checks (
                check_id TEXT PRIMARY KEY,
                dataset TEXT NOT NULL,
                checked_at TEXT NOT NULL
            );
            CREATE TABLE provider_calibration_attempts (
                attempt_id TEXT PRIMARY KEY,
                dataset TEXT NOT NULL,
                status TEXT NOT NULL,
                as_of TEXT NOT NULL
            );
            """
        )
        connection.executemany(
            "INSERT INTO provider_contract_checks VALUES (?, ?, ?)",
            (
                ("one", "daily_bars", "2026-05-01T00:00:00+00:00"),
                ("two", "daily_bars", "2026-08-01T00:00:00+00:00"),
            ),
        )
        connection.executemany(
            "INSERT INTO provider_calibration_attempts VALUES (?, ?, ?, ?)",
            (
                (
                    "completed",
                    "daily_bars",
                    "completed",
                    "2026-08-01T00:00:00+00:00",
                ),
                (
                    "unavailable",
                    "daily_bars",
                    "unavailable",
                    "2026-08-02T00:00:00+00:00",
                ),
            ),
        )

    loaded = load_evidence_sources(paths, assessed_at=NOW)
    daily_bars = next(
        item for item in loaded.inputs if item.dataset == "global_daily_bars"
    )

    assert daily_bars.operational.contract_check_count == 2
    assert daily_bars.operational.contract_observation_days == 92
    assert daily_bars.operational.calibration_completed_count == 1
    assert daily_bars.operational.calibration_unavailable_count == 1


def _evaluate(
    evaluator: EvidenceReadinessEvaluator,
    artifacts: tuple[EvidenceArtifact, ...],
    inputs: tuple[DatasetEvidenceInput, ...],
):
    return evaluator.evaluate(
        assessed_at=NOW,
        git_commit=COMMIT,
        configuration_hash="a" * 64,
        source_tree_hash="b" * 64,
        migration_head="0008_provider_calibration_attempts",
        artifacts=artifacts,
        inputs=inputs,
    )


def _artifact(status: EvidenceArtifactStatus) -> EvidenceArtifact:
    return EvidenceArtifact(
        artifact_id=stable_evidence_hash({"artifact": "test"}),
        role=EvidenceArtifactRole.READINESS_DASHBOARD,
        source_path="test/readiness.json",
        status=status,
        content_hash="c" * 64,
        observed_at=NOW,
        model_versions=("test-v1",),
        datasets=("fundamentals",),
    )


def _input(
    artifact_id: str,
    *,
    operational: OperationalDatasetEvidence | None = None,
) -> DatasetEvidenceInput:
    return DatasetEvidenceInput(
        dataset="fundamentals",
        current_classification=PITReadinessClassification.UNSUITABLE,
        current_readiness_score=20,
        trust_level=DataTrustLevel.HIGH,
        availability_precision=AvailabilityPrecision.EXACT,
        coverage_percent=100,
        historical_continuity_score=100,
        provider_consistency_score=100,
        required_field_completeness=100,
        date_validity=100,
        primary_records=100,
        secondary_status="available",
        capability_status="available",
        evidence_artifact_ids=(artifact_id,),
        limitations=(),
        missing_requirements=(),
        operational=operational or OperationalDatasetEvidence(dataset="fundamentals"),
    )


def _source_paths(root: Path) -> EvidenceSourcePaths:
    return EvidenceSourcePaths(
        readiness_dashboard=root / "dashboard.json",
        readiness_gap=root / "gap.json",
        quality_audit=root / "quality.json",
        provider_capabilities=root / "capabilities.json",
        operational_database=root / "operational.sqlite3",
    )


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
