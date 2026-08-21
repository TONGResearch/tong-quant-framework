import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any

from tong_quant.data.evidence_readiness import (
    DatasetEvidenceInput,
    EvidenceArtifact,
    EvidenceArtifactRole,
    EvidenceArtifactStatus,
    EvidenceReadinessPolicy,
    OperationalDatasetEvidence,
    stable_evidence_hash,
)
from tong_quant.domain.enums import (
    AvailabilityPrecision,
    DataTrustLevel,
    PITReadinessClassification,
)
from tong_quant.domain.models import require_timezone


@dataclass(frozen=True, slots=True)
class EvidenceSourcePaths:
    readiness_dashboard: Path
    readiness_gap: Path
    quality_audit: Path
    provider_capabilities: Path
    operational_database: Path
    supporting_documents: tuple[Path, ...] = ()


@dataclass(frozen=True, slots=True)
class LoadedEvidence:
    artifacts: tuple[EvidenceArtifact, ...]
    inputs: tuple[DatasetEvidenceInput, ...]


def load_evidence_sources(
    paths: EvidenceSourcePaths,
    *,
    assessed_at: datetime,
    policy: EvidenceReadinessPolicy | None = None,
) -> LoadedEvidence:
    require_timezone(assessed_at, "evidence source assessed_at")
    effective_policy = policy or EvidenceReadinessPolicy()
    dashboard, dashboard_artifact = _load_json_artifact(
        paths.readiness_dashboard,
        EvidenceArtifactRole.READINESS_DASHBOARD,
        assessed_at,
        effective_policy,
    )
    gap, gap_artifact = _load_json_artifact(
        paths.readiness_gap,
        EvidenceArtifactRole.READINESS_GAP,
        assessed_at,
        effective_policy,
    )
    quality, quality_artifact = _load_json_artifact(
        paths.quality_audit,
        EvidenceArtifactRole.QUALITY_AUDIT,
        assessed_at,
        effective_policy,
    )
    capabilities, capabilities_artifact = _load_json_artifact(
        paths.provider_capabilities,
        EvidenceArtifactRole.PROVIDER_CAPABILITIES,
        assessed_at,
        effective_policy,
    )
    operational, operational_artifact = _load_operational_database(
        paths.operational_database,
        assessed_at=assessed_at,
        policy=effective_policy,
    )
    document_artifacts = tuple(
        _load_document_artifact(path) for path in paths.supporting_documents
    )
    artifacts = (
        dashboard_artifact,
        gap_artifact,
        quality_artifact,
        capabilities_artifact,
        operational_artifact,
        *document_artifacts,
    )
    inputs = _build_inputs(
        dashboard=dashboard,
        gap=gap,
        quality=quality,
        capabilities=capabilities,
        operational=operational,
        artifacts=artifacts,
    )
    return LoadedEvidence(
        artifacts=tuple(sorted(artifacts, key=lambda item: item.source_path)),
        inputs=inputs,
    )


def _load_json_artifact(
    path: Path,
    role: EvidenceArtifactRole,
    assessed_at: datetime,
    policy: EvidenceReadinessPolicy,
) -> tuple[dict[str, Any], EvidenceArtifact]:
    if not path.exists():
        return {}, _missing_artifact(path, role)
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"evidence source must be a regular file: {path}")
    raw = path.read_bytes()
    try:
        document = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"evidence JSON is malformed: {path}") from error
    if not isinstance(document, dict):
        raise ValueError(f"evidence JSON root must be an object: {path}")
    generated_at = _optional_datetime(document.get("generated_at"), path)
    status = EvidenceArtifactStatus.AVAILABLE
    if generated_at is None or assessed_at - generated_at > timedelta(
        days=policy.artifact_stale_days
    ):
        status = EvidenceArtifactStatus.STALE
    datasets = tuple(sorted(_dataset_names(document)))
    versions = tuple(sorted(_model_versions(document)))
    content_hash = sha256(raw).hexdigest()
    return document, _artifact(
        role=role,
        path=path,
        status=status,
        content_hash=content_hash,
        observed_at=generated_at,
        model_versions=versions,
        datasets=datasets,
        limitations=("Evidence timestamp is missing or outside freshness policy",)
        if status is EvidenceArtifactStatus.STALE
        else (),
    )


def _load_document_artifact(path: Path) -> EvidenceArtifact:
    if not path.exists():
        return _missing_artifact(path, EvidenceArtifactRole.SUPPORTING_DOCUMENT)
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"supporting evidence must be a regular file: {path}")
    raw = path.read_bytes()
    datasets = _document_datasets(path.name)
    return _artifact(
        role=EvidenceArtifactRole.SUPPORTING_DOCUMENT,
        path=path,
        status=EvidenceArtifactStatus.AVAILABLE,
        content_hash=sha256(raw).hexdigest(),
        observed_at=None,
        model_versions=(),
        datasets=datasets,
        limitations=("Supporting documentation is not operational evidence",),
    )


def _load_operational_database(
    path: Path,
    *,
    assessed_at: datetime,
    policy: EvidenceReadinessPolicy,
) -> tuple[dict[str, OperationalDatasetEvidence], EvidenceArtifact]:
    if not path.exists():
        artifact = _missing_artifact(path, EvidenceArtifactRole.OPERATIONAL_DATABASE)
        return {}, artifact
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"operational evidence must be a regular file: {path}")
    uri = f"file:{path.resolve()}?mode=ro"
    try:
        with sqlite3.connect(uri, uri=True) as connection:
            connection.row_factory = sqlite3.Row
            tables = _table_names(connection)
            rows = _operational_rows(connection, tables, assessed_at)
            content_hash = _operational_database_hash(connection, tables)
    except sqlite3.DatabaseError as error:
        raise ValueError(f"operational evidence database is invalid: {path}") from error
    observed_at = _latest_operational_time(connection_path=path)
    status = EvidenceArtifactStatus.AVAILABLE
    if observed_at is not None and assessed_at - observed_at > timedelta(
        days=policy.artifact_stale_days
    ):
        status = EvidenceArtifactStatus.STALE
    artifact = _artifact(
        role=EvidenceArtifactRole.OPERATIONAL_DATABASE,
        path=path,
        status=status,
        content_hash=content_hash,
        observed_at=observed_at,
        model_versions=(),
        datasets=tuple(sorted(rows)),
        limitations=(
            "Operational database hash covers all readiness-relevant logical rows",
            *(
                ("Latest operational observation is outside freshness policy",)
                if status is EvidenceArtifactStatus.STALE
                else ()
            ),
        ),
    )
    return rows, artifact


def _operational_rows(
    connection: sqlite3.Connection,
    tables: set[str],
    assessed_at: datetime,
) -> dict[str, OperationalDatasetEvidence]:
    datasets: dict[str, dict[str, object]] = {}
    if "provider_contract_checks" in tables:
        for row in connection.execute(
            """
            SELECT dataset, COUNT(*) AS check_count,
                   MIN(checked_at) AS first_checked,
                   MAX(checked_at) AS last_checked
            FROM provider_contract_checks
            WHERE checked_at <= ?
            GROUP BY dataset
            """,
            (assessed_at.isoformat(),),
        ):
            dataset = _canonical_dataset(str(row["dataset"]))
            first = datetime.fromisoformat(str(row["first_checked"]))
            last = datetime.fromisoformat(str(row["last_checked"]))
            values = datasets.setdefault(dataset, {})
            values["contract_check_count"] = int(row["check_count"])
            values["contract_observation_days"] = max(
                0.0, (last - first).total_seconds() / 86_400
            )
    if {"provider_baseline_entries", "provider_baseline_manifests"} <= tables:
        query = """
            SELECT entries.dataset, COUNT(*) AS baseline_count,
                   AVG(entries.continuity_ratio) AS continuity_ratio,
                   AVG(entries.field_coverage_ratio) AS field_coverage_ratio,
                   AVG(entries.successful_observation_ratio) AS success_ratio
            FROM provider_baseline_entries AS entries
            JOIN provider_baseline_manifests AS manifests
              ON manifests.manifest_id = entries.manifest_id
            WHERE manifests.generated_at <= ?
              AND manifests.generated_at = (
                  SELECT MAX(latest.generated_at)
                  FROM provider_baseline_manifests AS latest
                  JOIN provider_baseline_entries AS latest_entries
                    ON latest_entries.manifest_id = latest.manifest_id
                  WHERE latest_entries.dataset = entries.dataset
                    AND latest.generated_at <= ?
              )
            GROUP BY entries.dataset
        """
        for row in connection.execute(query, (assessed_at.isoformat(),) * 2):
            dataset = _canonical_dataset(str(row["dataset"]))
            values = datasets.setdefault(dataset, {})
            values["baseline_count"] = int(row["baseline_count"])
            values["baseline_continuity_ratio"] = float(row["continuity_ratio"])
            values["baseline_field_coverage_ratio"] = float(
                row["field_coverage_ratio"]
            )
            values["baseline_success_ratio"] = float(row["success_ratio"])
    if "provider_artifact_observations" in tables:
        for row in connection.execute(
            """
            SELECT dataset, COUNT(*) AS observation_count,
                   SUM(CASE WHEN status != 'captured' THEN 1 ELSE 0 END) AS failures
            FROM provider_artifact_observations
            WHERE retrieved_at <= ?
            GROUP BY dataset
            """,
            (assessed_at.isoformat(),),
        ):
            dataset = _canonical_dataset(str(row["dataset"]))
            values = datasets.setdefault(dataset, {})
            values["artifact_capture_count"] = int(row["observation_count"])
            values["artifact_failure_count"] = int(row["failures"] or 0)
    if "provider_calibration_attempts" in tables:
        for row in connection.execute(
            """
            SELECT dataset,
                   SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed,
                   SUM(CASE WHEN status = 'unavailable' THEN 1 ELSE 0 END) AS unavailable,
                   SUM(CASE WHEN status = 'incompatible' THEN 1 ELSE 0 END) AS incompatible
            FROM provider_calibration_attempts
            WHERE as_of <= ?
            GROUP BY dataset
            """,
            (assessed_at.isoformat(),),
        ):
            dataset = _canonical_dataset(str(row["dataset"]))
            values = datasets.setdefault(dataset, {})
            values["calibration_completed_count"] = int(row["completed"] or 0)
            values["calibration_unavailable_count"] = int(row["unavailable"] or 0)
            values["calibration_incompatible_count"] = int(row["incompatible"] or 0)
    if "provider_conflicts" in tables:
        for row in connection.execute(
            """
            SELECT dataset, COUNT(*) AS conflict_count,
                   SUM(CASE WHEN severity IN ('high', 'critical') THEN 1 ELSE 0 END)
                       AS high_conflicts
            FROM provider_conflicts
            WHERE detected_at <= ?
            GROUP BY dataset
            """,
            (assessed_at.isoformat(),),
        ):
            dataset = _canonical_dataset(str(row["dataset"]))
            values = datasets.setdefault(dataset, {})
            values["provider_conflict_count"] = int(row["conflict_count"])
            values["high_conflict_count"] = int(row["high_conflicts"] or 0)
    return {
        dataset: _operational_evidence(dataset, values)
        for dataset, values in sorted(datasets.items())
    }


def _operational_evidence(
    dataset: str,
    values: dict[str, object],
) -> OperationalDatasetEvidence:
    return OperationalDatasetEvidence(
        dataset=dataset,
        contract_check_count=_dict_int(values, "contract_check_count"),
        contract_observation_days=_dict_float(values, "contract_observation_days"),
        baseline_count=_dict_int(values, "baseline_count"),
        baseline_continuity_ratio=_dict_optional_float(
            values, "baseline_continuity_ratio"
        ),
        baseline_field_coverage_ratio=_dict_optional_float(
            values, "baseline_field_coverage_ratio"
        ),
        baseline_success_ratio=_dict_optional_float(values, "baseline_success_ratio"),
        artifact_capture_count=_dict_int(values, "artifact_capture_count"),
        artifact_failure_count=_dict_int(values, "artifact_failure_count"),
        calibration_completed_count=_dict_int(
            values, "calibration_completed_count"
        ),
        calibration_unavailable_count=_dict_int(
            values, "calibration_unavailable_count"
        ),
        calibration_incompatible_count=_dict_int(
            values, "calibration_incompatible_count"
        ),
        provider_conflict_count=_dict_int(values, "provider_conflict_count"),
        high_conflict_count=_dict_int(values, "high_conflict_count"),
    )


def _dict_int(values: dict[str, object], key: str) -> int:
    value = values.get(key, 0)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"operational metric {key} must be an integer")
    return value


def _dict_float(values: dict[str, object], key: str) -> float:
    value = values.get(key, 0.0)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"operational metric {key} must be numeric")
    return float(value)


def _dict_optional_float(values: dict[str, object], key: str) -> float | None:
    value = values.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"operational metric {key} must be numeric")
    return float(value)


def _build_inputs(
    *,
    dashboard: dict[str, Any],
    gap: dict[str, Any],
    quality: dict[str, Any],
    capabilities: dict[str, Any],
    operational: dict[str, OperationalDatasetEvidence],
    artifacts: tuple[EvidenceArtifact, ...],
) -> tuple[DatasetEvidenceInput, ...]:
    dashboard_rows = _rows_by_dataset(dashboard)
    gap_rows = _rows_by_dataset(gap)
    quality_rows = _rows_by_dataset(quality)
    capability_rows = _rows_by_dataset(capabilities)
    dataset_names = set(dashboard_rows) | set(gap_rows) | set(quality_rows)
    dataset_names |= set(capability_rows) | set(operational)
    dataset_names.add("global_daily_bars")
    inputs: list[DatasetEvidenceInput] = []
    for dataset in sorted(dataset_names):
        readiness = dashboard_rows.get(dataset, {})
        pit = _mapping(readiness.get("pit_readiness"))
        quality_row = quality_rows.get(dataset, {})
        gap_row = gap_rows.get(dataset, {})
        capability_row = capability_rows.get(dataset, {})
        operational_row = operational.get(
            dataset, OperationalDatasetEvidence(dataset=dataset)
        )
        evidence_ids = tuple(
            item.artifact_id
            for item in artifacts
            if not item.datasets or dataset in item.datasets
        )
        inputs.append(
            DatasetEvidenceInput(
                dataset=dataset,
                current_classification=_classification(
                    pit.get("classification")
                    or gap_row.get("current_classification")
                    or "unsuitable"
                ),
                current_readiness_score=_number(pit.get("readiness_score")) or 0,
                trust_level=_trust(readiness.get("trust_level") or "unknown"),
                availability_precision=_precision(
                    readiness.get("availability_precision") or "unknown"
                ),
                coverage_percent=_number(readiness.get("coverage_percent")),
                historical_continuity_score=_number(
                    readiness.get("historical_continuity_score")
                ),
                provider_consistency_score=_number(
                    readiness.get("provider_consistency_score")
                ),
                required_field_completeness=_ratio_percent(
                    quality_row.get("required_field_completeness")
                ),
                date_validity=_ratio_percent(quality_row.get("date_validity")),
                primary_records=_integer(readiness.get("primary_records")),
                secondary_status=str(readiness.get("secondary_status") or "unknown"),
                capability_status=str(capability_row.get("status") or "unknown"),
                evidence_artifact_ids=evidence_ids,
                limitations=_strings(
                    readiness.get("known_limitations"),
                    quality_row.get("limitations"),
                    capability_row.get("reason"),
                ),
                missing_requirements=_strings(gap_row.get("missing_requirements")),
                operational=operational_row,
            )
        )
    return tuple(inputs)


def _artifact(
    *,
    role: EvidenceArtifactRole,
    path: Path,
    status: EvidenceArtifactStatus,
    content_hash: str,
    observed_at: datetime | None,
    model_versions: tuple[str, ...],
    datasets: tuple[str, ...],
    limitations: tuple[str, ...],
) -> EvidenceArtifact:
    source_path = _portable_source_path(path)
    artifact_id = stable_evidence_hash(
        {
            "role": role.value,
            "source_path": source_path,
            "status": status.value,
            "content_hash": content_hash,
            "observed_at": observed_at.isoformat() if observed_at else None,
        }
    )
    return EvidenceArtifact(
        artifact_id=artifact_id,
        role=role,
        source_path=source_path,
        status=status,
        content_hash=content_hash,
        observed_at=observed_at,
        model_versions=tuple(sorted(set(model_versions))),
        datasets=tuple(sorted(set(datasets))),
        limitations=limitations,
    )


def _missing_artifact(path: Path, role: EvidenceArtifactRole) -> EvidenceArtifact:
    return _artifact(
        role=role,
        path=path,
        status=EvidenceArtifactStatus.MISSING,
        content_hash="",
        observed_at=None,
        model_versions=(),
        datasets=(),
        limitations=("Required evidence source is missing",),
    )


def _rows_by_dataset(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = document.get("datasets", [])
    if not isinstance(rows, list):
        raise ValueError("evidence datasets must be a list")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        mapped = _mapping(row)
        dataset = mapped.get("dataset")
        if not isinstance(dataset, str) or not dataset.strip():
            raise ValueError("evidence dataset row requires a dataset")
        if dataset in result:
            raise ValueError(f"duplicate evidence dataset: {dataset}")
        result[dataset] = mapped
    return result


def _dataset_names(document: dict[str, Any]) -> set[str]:
    return set(_rows_by_dataset(document)) if "datasets" in document else set()


def _model_versions(document: dict[str, Any]) -> set[str]:
    versions: set[str] = set()
    value = document.get("model_version")
    if isinstance(value, str) and value:
        versions.add(value)
    for row in document.get("datasets", []):
        if not isinstance(row, dict):
            continue
        for key in ("model_version",):
            nested = row.get(key)
            if isinstance(nested, str) and nested:
                versions.add(nested)
        pit = row.get("pit_readiness")
        if isinstance(pit, dict):
            nested = pit.get("model_version")
            if isinstance(nested, str) and nested:
                versions.add(nested)
    return versions


def _optional_datetime(value: object, path: Path) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"evidence generated_at must be an ISO timestamp: {path}")
    parsed = datetime.fromisoformat(value)
    require_timezone(parsed, f"evidence generated_at for {path}")
    return parsed


def _mapping(value: object) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("evidence value must be an object")
    return value


def _number(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("evidence score must be numeric")
    return float(value)


def _ratio_percent(value: object) -> float | None:
    number = _number(value)
    if number is None:
        return None
    return number * 100 if 0 <= number <= 1 else number


def _integer(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("evidence record count must be an integer")
    return value


def _strings(*values: object) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, str):
            if value.strip():
                result.append(value)
            continue
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ValueError("evidence limitations must be strings")
        result.extend(item for item in value if item.strip())
    return tuple(dict.fromkeys(result))


def _classification(value: object) -> PITReadinessClassification:
    try:
        return PITReadinessClassification(str(value))
    except ValueError as error:
        raise ValueError(f"unknown PIT readiness classification: {value}") from error


def _trust(value: object) -> DataTrustLevel:
    try:
        return DataTrustLevel(str(value))
    except ValueError as error:
        raise ValueError(f"unknown data trust level: {value}") from error


def _precision(value: object) -> AvailabilityPrecision:
    try:
        return AvailabilityPrecision(str(value))
    except ValueError as error:
        raise ValueError(f"unknown availability precision: {value}") from error


def _canonical_dataset(dataset: str) -> str:
    return {
        "china_disclosures": "financial_publication_dates",
        "daily_bars": "global_daily_bars",
    }.get(dataset, dataset)


def _document_datasets(filename: str) -> tuple[str, ...]:
    if "cninfo" in filename:
        return ("financial_publication_dates",)
    if "yahoo" in filename:
        return ("global_daily_bars",)
    return ()


def _portable_source_path(path: Path) -> str:
    if not path.is_absolute():
        return path.as_posix()
    for marker in ("docs", "data", "config", "src", "scripts"):
        if marker in path.parts:
            index = path.parts.index(marker)
            return Path(*path.parts[index:]).as_posix()
    return path.as_posix()


def _table_names(connection: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }


def _latest_operational_time(connection_path: Path) -> datetime | None:
    uri = f"file:{connection_path.resolve()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        connection.row_factory = sqlite3.Row
        tables = _table_names(connection)
        candidates: list[datetime] = []
        for table, column in (
            ("provider_contract_checks", "checked_at"),
            ("provider_baseline_manifests", "generated_at"),
            ("provider_artifact_observations", "retrieved_at"),
            ("provider_calibration_attempts", "as_of"),
            ("provider_conflicts", "detected_at"),
        ):
            if table not in tables:
                continue
            row = connection.execute(
                f"SELECT MAX({column}) FROM {table}"  # noqa: S608 - fixed identifiers
            ).fetchone()
            if row is not None and row[0]:
                value = datetime.fromisoformat(str(row[0]))
                require_timezone(value, f"operational timestamp {table}.{column}")
                candidates.append(value)
        return max(candidates, default=None)


def _operational_database_hash(
    connection: sqlite3.Connection,
    tables: set[str],
) -> str:
    relevant = (
        "provider_contract_runs",
        "provider_contract_checks",
        "provider_baseline_manifests",
        "provider_baseline_entries",
        "provider_baseline_inputs",
        "provider_artifacts",
        "provider_artifact_observations",
        "provider_calibration_attempts",
        "provider_consistency_reports",
        "provider_conflicts",
        "dataset_confidence_assessments",
    )
    document: dict[str, list[dict[str, object]]] = {}
    for table in relevant:
        if table not in tables:
            continue
        rows = [dict(row) for row in connection.execute(f"SELECT * FROM {table}")]
        rows.sort(key=lambda row: json.dumps(row, sort_keys=True, separators=(",", ":")))
        document[table] = rows
    return stable_evidence_hash(document)


__all__ = [
    "EvidenceSourcePaths",
    "LoadedEvidence",
    "load_evidence_sources",
]
