import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path

from tong_quant.core.security import reject_sensitive_structure
from tong_quant.domain.models import require_timezone
from tong_quant.version import (
    DATABASE_SCHEMA_VERSION,
    FRAMEWORK_VERSION,
    PROVIDER_EVIDENCE_BUNDLE_VERSION,
)

type JsonScalar = str | int | float | None

_TABLE_SPECS: tuple[tuple[str, str | None], ...] = (
    ("schema_metadata", "updated_at"),
    ("schema_migrations", "applied_at"),
    ("schema_fingerprints", "recorded_at"),
    ("ingestion_batches", "completed_at"),
    ("provider_limitations", "documented_at"),
    ("provider_evidence_records", "retrieved_at"),
    ("provider_contract_runs", "completed_at"),
    ("provider_contract_checks", "checked_at"),
    ("provider_baseline_manifests", "generated_at"),
    ("provider_baseline_entries", None),
    ("provider_baseline_inputs", None),
    ("provider_artifacts", "first_retrieved_at"),
    ("provider_artifact_observations", "retrieved_at"),
    ("provider_calibration_attempts", "as_of"),
    ("provider_consistency_reports", "compared_at"),
    ("provider_conflicts", "detected_at"),
    ("dataset_confidence_assessments", "assessed_at"),
    ("historical_coverage_assessments", "assessed_at"),
    ("pit_readiness_assessments", "assessed_at"),
)
_REQUIRED_TABLES = frozenset(name for name, _ in _TABLE_SPECS)
_EXCLUDED_COLUMNS = frozenset({"storage_key"})
_WINDOWS_PATH = re.compile(r"^[A-Za-z]:[\\/]")


@dataclass(frozen=True, slots=True)
class EvidenceTableSnapshot:
    table: str
    columns: tuple[str, ...]
    rows: tuple[tuple[JsonScalar, ...], ...]
    rows_hash: str

    def __post_init__(self) -> None:
        if not self.table.strip() or not self.columns:
            raise ValueError("evidence table snapshot requires identity and columns")
        if len(self.columns) != len(set(self.columns)):
            raise ValueError("evidence table columns must be unique")
        if any(len(row) != len(self.columns) for row in self.rows):
            raise ValueError("evidence table rows do not match declared columns")
        if self.rows != tuple(sorted(self.rows, key=_canonical_row)):
            raise ValueError("evidence table rows must be canonically sorted")
        if self.rows_hash != _stable_hash(
            {"columns": list(self.columns), "rows": [list(row) for row in self.rows]}
        ):
            raise ValueError("evidence table hash does not match its rows")

    @property
    def row_count(self) -> int:
        return len(self.rows)


@dataclass(frozen=True, slots=True)
class DatasetEvidenceBundleSummary:
    dataset: str
    first_observed_at: str | None
    last_observed_at: str | None
    observation_days: float
    contract_check_count: int
    baseline_count: int
    baseline_continuity_ratio: float | None
    baseline_field_coverage_ratio: float | None
    baseline_success_ratio: float | None
    artifact_observation_count: int
    artifact_failure_count: int
    calibration_completed_count: int
    calibration_unavailable_count: int
    calibration_incompatible_count: int
    provider_conflict_count: int
    high_conflict_count: int

    def __post_init__(self) -> None:
        if not self.dataset.strip() or self.observation_days < 0:
            raise ValueError("dataset evidence summary is invalid")
        counts = (
            self.contract_check_count,
            self.baseline_count,
            self.artifact_observation_count,
            self.artifact_failure_count,
            self.calibration_completed_count,
            self.calibration_unavailable_count,
            self.calibration_incompatible_count,
            self.provider_conflict_count,
            self.high_conflict_count,
        )
        if min(counts) < 0 or self.high_conflict_count > self.provider_conflict_count:
            raise ValueError("dataset evidence counts are invalid")
        for value in (
            self.baseline_continuity_ratio,
            self.baseline_field_coverage_ratio,
            self.baseline_success_ratio,
        ):
            if value is not None and not 0 <= value <= 1:
                raise ValueError("dataset evidence ratios must be between zero and one")


@dataclass(frozen=True, slots=True)
class ProviderScopeEvidenceSummary:
    provider: str
    dataset: str
    market: str
    subject: str
    first_observed_at: str | None
    last_observed_at: str | None
    observation_days: float
    contract_check_count: int
    baseline_manifest_id: str | None
    expected_periods: int | None
    observed_periods: int | None
    successful_observation_ratio: float | None
    field_coverage_ratio: float | None
    continuity_ratio: float | None

    def __post_init__(self) -> None:
        identity = self.provider, self.dataset, self.market, self.subject
        if not all(item.strip() for item in identity):
            raise ValueError("provider evidence scope requires complete identity")
        if self.observation_days < 0 or self.contract_check_count < 0:
            raise ValueError("provider evidence scope counts are invalid")
        if self.expected_periods is not None and self.expected_periods < 1:
            raise ValueError("provider evidence scope expected periods are invalid")
        if self.observed_periods is not None and self.observed_periods < 0:
            raise ValueError("provider evidence scope observed periods are invalid")
        for value in (
            self.successful_observation_ratio,
            self.field_coverage_ratio,
            self.continuity_ratio,
        ):
            if value is not None and not 0 <= value <= 1:
                raise ValueError("provider evidence scope ratios must be between zero and one")

    @property
    def identity(self) -> tuple[str, str, str, str]:
        return self.provider, self.dataset, self.market, self.subject


@dataclass(frozen=True, slots=True)
class ProviderEvidenceBundle:
    bundle_id: str
    as_of: datetime
    tables: tuple[EvidenceTableSnapshot, ...]
    scope_summaries: tuple[ProviderScopeEvidenceSummary, ...]
    dataset_summaries: tuple[DatasetEvidenceBundleSummary, ...]
    missing_tables: tuple[str, ...]
    model_versions: tuple[str, ...]
    limitations: tuple[str, ...]
    framework_version: str = FRAMEWORK_VERSION
    database_schema_version: str = DATABASE_SCHEMA_VERSION
    implementation_version: str = PROVIDER_EVIDENCE_BUNDLE_VERSION

    def __post_init__(self) -> None:
        require_timezone(self.as_of, "provider evidence bundle as_of")
        if len(self.bundle_id) != 64:
            raise ValueError("provider evidence bundle ID must be a SHA-256 digest")
        if tuple(item.table for item in self.tables) != tuple(
            sorted(item.table for item in self.tables)
        ):
            raise ValueError("provider evidence tables must be sorted")
        if tuple(item.dataset for item in self.dataset_summaries) != tuple(
            sorted(item.dataset for item in self.dataset_summaries)
        ):
            raise ValueError("provider evidence summaries must be sorted")
        if tuple(item.identity for item in self.scope_summaries) != tuple(
            sorted(item.identity for item in self.scope_summaries)
        ):
            raise ValueError("provider evidence scope summaries must be sorted")
        if tuple(sorted(set(self.missing_tables))) != self.missing_tables:
            raise ValueError("provider evidence missing tables must be sorted and unique")
        if tuple(sorted(set(self.model_versions))) != self.model_versions:
            raise ValueError("provider evidence versions must be sorted and unique")
        expected = _stable_hash(_bundle_content(self, include_bundle_id=False))
        if expected != self.bundle_id:
            raise ValueError("provider evidence bundle hash does not match content")


@dataclass(frozen=True, slots=True)
class ProviderEvidenceBundleExporter:
    def export(self, database: Path, *, as_of: datetime) -> ProviderEvidenceBundle:
        require_timezone(as_of, "provider evidence export as_of")
        if database.is_symlink() or not database.is_file():
            raise ValueError("provider evidence database must be a regular file")
        uri = f"file:{database.resolve()}?mode=ro"
        try:
            with sqlite3.connect(uri, uri=True) as connection:
                connection.row_factory = sqlite3.Row
                existing = _table_names(connection)
                snapshots = _snapshots(connection, existing, as_of)
        except sqlite3.DatabaseError as error:
            raise ValueError("provider evidence database is invalid") from error
        summaries = reconstruct_dataset_summaries(snapshots)
        scope_summaries = reconstruct_provider_scope_summaries(snapshots)
        missing = tuple(sorted(_REQUIRED_TABLES - existing))
        versions = _model_versions(snapshots)
        limitations = (
            *(f"Missing operational evidence table: {table}" for table in missing),
            "Bundle excludes provider artifact storage_key values and artifact bytes",
            "Contract health and provider agreement do not promote trust or PIT readiness",
        )
        content = _bundle_values_content(
            bundle_id="",
            include_bundle_id=False,
            as_of=as_of,
            tables=snapshots,
            scope_summaries=scope_summaries,
            dataset_summaries=summaries,
            missing_tables=missing,
            model_versions=versions,
            limitations=limitations,
            framework_version=FRAMEWORK_VERSION,
            database_schema_version=DATABASE_SCHEMA_VERSION,
            implementation_version=PROVIDER_EVIDENCE_BUNDLE_VERSION,
        )
        _reject_local_paths(content)
        reject_sensitive_structure(content, path="provider_evidence_bundle")
        return ProviderEvidenceBundle(
            bundle_id=_stable_hash(content),
            as_of=as_of,
            tables=snapshots,
            scope_summaries=scope_summaries,
            dataset_summaries=summaries,
            missing_tables=missing,
            model_versions=versions,
            limitations=limitations,
        )


def provider_evidence_bundle_json(bundle: ProviderEvidenceBundle) -> dict[str, object]:
    return _bundle_content(bundle, include_bundle_id=True)


def serialize_provider_evidence_bundle(bundle: ProviderEvidenceBundle) -> str:
    return json.dumps(provider_evidence_bundle_json(bundle), indent=2, sort_keys=True)


def render_provider_evidence_bundle_markdown(bundle: ProviderEvidenceBundle) -> str:
    lines = [
        "# Provider Operational Evidence Bundle",
        "",
        f"- Bundle ID: `{bundle.bundle_id}`",
        f"- As of: `{bundle.as_of.isoformat()}`",
        f"- Framework/schema: `{bundle.framework_version}` / "
        f"`{bundle.database_schema_version}`",
        f"- Implementation: `{bundle.implementation_version}`",
        f"- Missing required tables: `{list(bundle.missing_tables)}`",
        "",
        "## Provider Scope Summary",
        "",
        "| Provider | Dataset | Market | Subject | Checks | Days | "
        "Observed/expected | Continuity | Field coverage |",
        "|---|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for scope_summary in bundle.scope_summaries:
        periods = (
            "N/A"
            if scope_summary.observed_periods is None
            or scope_summary.expected_periods is None
            else f"{scope_summary.observed_periods}/{scope_summary.expected_periods}"
        )
        lines.append(
            f"| {scope_summary.provider} | {scope_summary.dataset} | "
            f"{scope_summary.market} | {scope_summary.subject} | "
            f"{scope_summary.contract_check_count} | "
            f"{scope_summary.observation_days:.1f} | {periods} | "
            f"{_ratio_text(scope_summary.continuity_ratio)} | "
            f"{_ratio_text(scope_summary.field_coverage_ratio)} |"
        )
    lines.extend(
        [
            "",
            "## Dataset Summary",
            "",
            "| Dataset | Checks | Days | Baselines | Continuity | Field coverage | "
            "Calibrations | Conflicts |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for dataset_summary in bundle.dataset_summaries:
        continuity = _ratio_text(dataset_summary.baseline_continuity_ratio)
        coverage = _ratio_text(dataset_summary.baseline_field_coverage_ratio)
        lines.append(
            f"| {dataset_summary.dataset} | "
            f"{dataset_summary.contract_check_count} | "
            f"{dataset_summary.observation_days:.1f} | "
            f"{dataset_summary.baseline_count} | {continuity} | {coverage} | "
            f"{dataset_summary.calibration_completed_count} | "
            f"{dataset_summary.provider_conflict_count} |"
        )
    lines.extend(["", "## Table Inventory", ""])
    for table in bundle.tables:
        lines.append(
            f"- `{table.table}`: {table.row_count} rows; hash `{table.rows_hash}`"
        )
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in bundle.limitations)
    lines.extend(
        [
            "",
            "This is a credential-free data-governance artifact. It is not an "
            "investment recommendation, execution instruction, or readiness promotion.",
            "",
        ]
    )
    return "\n".join(lines)


def verify_provider_evidence_document(document: dict[str, object]) -> None:
    reject_sensitive_structure(document, path="provider_evidence_bundle")
    _reject_local_paths(document)
    bundle_id = document.get("bundle_id")
    if not isinstance(bundle_id, str) or len(bundle_id) != 64:
        raise ValueError("provider evidence document requires a bundle ID")
    without_id = dict(document)
    without_id.pop("bundle_id")
    if _stable_hash(without_id) != bundle_id:
        raise ValueError("provider evidence document hash does not match content")
    table_documents = document.get("tables")
    if not isinstance(table_documents, list):
        raise ValueError("provider evidence document tables must be a list")
    snapshots = tuple(_snapshot_from_document(item) for item in table_documents)
    expected_summaries = [
        _summary_document(item) for item in reconstruct_dataset_summaries(snapshots)
    ]
    if document.get("dataset_summaries") != expected_summaries:
        raise ValueError("provider evidence dataset summaries cannot be reconstructed")
    expected_scope_summaries = [
        _scope_summary_document(item)
        for item in reconstruct_provider_scope_summaries(snapshots)
    ]
    if document.get("scope_summaries") != expected_scope_summaries:
        raise ValueError("provider evidence scope summaries cannot be reconstructed")


def reconstruct_provider_scope_summaries(
    snapshots: tuple[EvidenceTableSnapshot, ...],
) -> tuple[ProviderScopeEvidenceSummary, ...]:
    tables = {item.table: _row_documents(item) for item in snapshots}
    scope_times: dict[tuple[str, str, str, str], list[datetime]] = {}
    for row in tables.get("provider_contract_checks", []):
        scope = _scope_identity(row)
        scope_times.setdefault(scope, []).append(
            _timestamp(row.get("checked_at"), "checked_at")
        )

    manifest_times = {
        _required_string(row, "manifest_id"): _timestamp(
            row.get("generated_at"), "generated_at"
        )
        for row in tables.get("provider_baseline_manifests", [])
    }
    baseline_rows: dict[tuple[str, str, str, str], list[dict[str, JsonScalar]]] = {}
    for row in tables.get("provider_baseline_entries", []):
        baseline_rows.setdefault(_scope_identity(row), []).append(row)

    identities = set(scope_times) | set(baseline_rows)
    summaries = []
    for identity in sorted(identities):
        times = sorted(scope_times.get(identity, []))
        baseline = _latest_baseline_row(baseline_rows.get(identity, []), manifest_times)
        summaries.append(
            ProviderScopeEvidenceSummary(
                provider=identity[0],
                dataset=identity[1],
                market=identity[2],
                subject=identity[3],
                first_observed_at=times[0].isoformat() if times else None,
                last_observed_at=times[-1].isoformat() if times else None,
                observation_days=(
                    round((times[-1] - times[0]).total_seconds() / 86_400, 6)
                    if times
                    else 0.0
                ),
                contract_check_count=len(times),
                baseline_manifest_id=(
                    _required_string(baseline, "manifest_id") if baseline else None
                ),
                expected_periods=_optional_int(baseline, "expected_periods"),
                observed_periods=_optional_int(baseline, "observed_periods"),
                successful_observation_ratio=_optional_float(
                    baseline, "successful_observation_ratio"
                ),
                field_coverage_ratio=_optional_float(
                    baseline, "field_coverage_ratio"
                ),
                continuity_ratio=_optional_float(baseline, "continuity_ratio"),
            )
        )
    return tuple(summaries)


def reconstruct_dataset_summaries(
    snapshots: tuple[EvidenceTableSnapshot, ...],
) -> tuple[DatasetEvidenceBundleSummary, ...]:
    tables = {item.table: _row_documents(item) for item in snapshots}
    values: dict[str, dict[str, object]] = {}
    check_times: dict[str, list[datetime]] = {}
    for row in tables.get("provider_contract_checks", []):
        dataset = _canonical_dataset(_required_string(row, "dataset"))
        checked_at = _timestamp(row.get("checked_at"), "checked_at")
        dataset_times = check_times.setdefault(dataset, [])
        dataset_times.append(checked_at)
        _increment(values, dataset, "contract_check_count")
    manifest_times = {
        _required_string(row, "manifest_id"): _timestamp(
            row.get("generated_at"), "generated_at"
        )
        for row in tables.get("provider_baseline_manifests", [])
    }
    baseline_rows: dict[str, list[dict[str, JsonScalar]]] = {}
    for row in tables.get("provider_baseline_entries", []):
        dataset = _canonical_dataset(_required_string(row, "dataset"))
        baseline_rows.setdefault(dataset, []).append(row)
    for dataset, rows in baseline_rows.items():
        candidate_times = [
            observed
            for row in rows
            if (
                observed := manifest_times.get(
                    _required_string(row, "manifest_id")
                )
            )
            is not None
        ]
        latest = max(candidate_times, default=None)
        selected = [
            row
            for row in rows
            if manifest_times.get(_required_string(row, "manifest_id")) == latest
        ]
        summary_values = values.setdefault(dataset, {})
        summary_values["baseline_count"] = len(selected)
        summary_values["baseline_continuity_ratio"] = _average(
            selected, "continuity_ratio"
        )
        summary_values["baseline_field_coverage_ratio"] = _average(
            selected, "field_coverage_ratio"
        )
        summary_values["baseline_success_ratio"] = _average(
            selected, "successful_observation_ratio"
        )
    for row in tables.get("provider_artifact_observations", []):
        dataset = _canonical_dataset(_required_string(row, "dataset"))
        _increment(values, dataset, "artifact_observation_count")
        if row.get("status") != "captured":
            _increment(values, dataset, "artifact_failure_count")
    for row in tables.get("provider_calibration_attempts", []):
        dataset = _canonical_dataset(_required_string(row, "dataset"))
        status = _required_string(row, "status")
        if status in {"completed", "unavailable", "incompatible"}:
            _increment(values, dataset, f"calibration_{status}_count")
    for row in tables.get("provider_conflicts", []):
        dataset = _canonical_dataset(_required_string(row, "dataset"))
        _increment(values, dataset, "provider_conflict_count")
        if row.get("severity") in {"high", "critical"}:
            _increment(values, dataset, "high_conflict_count")
    datasets = set(values) | set(check_times)
    summaries = []
    for dataset in sorted(datasets):
        summary_values = values.get(dataset, {})
        times = sorted(check_times.get(dataset, []))
        summaries.append(
            DatasetEvidenceBundleSummary(
                dataset=dataset,
                first_observed_at=times[0].isoformat() if times else None,
                last_observed_at=times[-1].isoformat() if times else None,
                observation_days=(
                    round((times[-1] - times[0]).total_seconds() / 86_400, 6)
                    if times
                    else 0.0
                ),
                contract_check_count=_bucket_int(
                    summary_values, "contract_check_count"
                ),
                baseline_count=_bucket_int(summary_values, "baseline_count"),
                baseline_continuity_ratio=_bucket_optional_float(
                    summary_values, "baseline_continuity_ratio"
                ),
                baseline_field_coverage_ratio=_bucket_optional_float(
                    summary_values, "baseline_field_coverage_ratio"
                ),
                baseline_success_ratio=_bucket_optional_float(
                    summary_values, "baseline_success_ratio"
                ),
                artifact_observation_count=_bucket_int(
                    summary_values, "artifact_observation_count"
                ),
                artifact_failure_count=_bucket_int(
                    summary_values, "artifact_failure_count"
                ),
                calibration_completed_count=_bucket_int(
                    summary_values, "calibration_completed_count"
                ),
                calibration_unavailable_count=_bucket_int(
                    summary_values, "calibration_unavailable_count"
                ),
                calibration_incompatible_count=_bucket_int(
                    summary_values, "calibration_incompatible_count"
                ),
                provider_conflict_count=_bucket_int(
                    summary_values, "provider_conflict_count"
                ),
                high_conflict_count=_bucket_int(
                    summary_values, "high_conflict_count"
                ),
            )
        )
    return tuple(summaries)


def _snapshots(
    connection: sqlite3.Connection,
    existing: set[str],
    as_of: datetime,
) -> tuple[EvidenceTableSnapshot, ...]:
    snapshots: dict[str, EvidenceTableSnapshot] = {}
    for table, time_column in _TABLE_SPECS:
        if table not in existing or table in {
            "provider_baseline_entries",
            "provider_baseline_inputs",
        }:
            continue
        snapshots[table] = _snapshot(connection, table, time_column, as_of)
    selected_manifests = {
        str(row[0])
        for row in snapshots.get(
            "provider_baseline_manifests", _empty_snapshot("missing")
        ).rows
    }
    for table in ("provider_baseline_entries", "provider_baseline_inputs"):
        if table in existing:
            snapshots[table] = _snapshot(
                connection,
                table,
                None,
                as_of,
                allowed_manifest_ids=selected_manifests,
            )
    return tuple(snapshots[name] for name in sorted(snapshots))


def _snapshot(
    connection: sqlite3.Connection,
    table: str,
    time_column: str | None,
    as_of: datetime,
    *,
    allowed_manifest_ids: set[str] | None = None,
) -> EvidenceTableSnapshot:
    columns = tuple(
        str(row[1])
        for row in connection.execute(f"PRAGMA table_info({table})")
        if str(row[1]) not in _EXCLUDED_COLUMNS
    )
    rows: list[tuple[JsonScalar, ...]] = []
    for row in connection.execute(f"SELECT {', '.join(columns)} FROM {table}"):
        document = dict(zip(columns, row, strict=True))
        if (
            time_column is not None
            and time_column in document
            and (
                document[time_column] is None
                or _timestamp(document[time_column], f"{table}.{time_column}") > as_of
            )
        ):
            continue
        if allowed_manifest_ids is not None:
            manifest_id = document.get("manifest_id")
            if not isinstance(manifest_id, str) or manifest_id not in allowed_manifest_ids:
                continue
        rows.append(tuple(_scalar(document[column]) for column in columns))
    ordered = tuple(sorted(rows, key=_canonical_row))
    rows_hash = _stable_hash(
        {"columns": list(columns), "rows": [list(row) for row in ordered]}
    )
    return EvidenceTableSnapshot(table, columns, ordered, rows_hash)


def _empty_snapshot(table: str) -> EvidenceTableSnapshot:
    columns = ("manifest_id",)
    rows: tuple[tuple[JsonScalar, ...], ...] = ()
    return EvidenceTableSnapshot(
        table,
        columns,
        rows,
        _stable_hash({"columns": list(columns), "rows": []}),
    )


def _snapshot_from_document(value: object) -> EvidenceTableSnapshot:
    if not isinstance(value, dict):
        raise ValueError("provider evidence table must be an object")
    table = value.get("table")
    columns = value.get("columns")
    rows = value.get("rows")
    rows_hash = value.get("rows_hash")
    row_count = value.get("row_count")
    if not isinstance(table, str) or not isinstance(rows_hash, str):
        raise ValueError("provider evidence table identity is invalid")
    if not isinstance(columns, list) or not all(isinstance(item, str) for item in columns):
        raise ValueError("provider evidence columns are invalid")
    if not isinstance(rows, list) or not all(isinstance(item, list) for item in rows):
        raise ValueError("provider evidence rows are invalid")
    converted = tuple(tuple(_scalar(item) for item in row) for row in rows)
    if row_count != len(converted):
        raise ValueError("provider evidence row count does not match rows")
    return EvidenceTableSnapshot(table, tuple(columns), converted, rows_hash)


def _row_documents(snapshot: EvidenceTableSnapshot) -> list[dict[str, JsonScalar]]:
    return [dict(zip(snapshot.columns, row, strict=True)) for row in snapshot.rows]


def _model_versions(snapshots: tuple[EvidenceTableSnapshot, ...]) -> tuple[str, ...]:
    versions: set[str] = set()
    for snapshot in snapshots:
        for row in _row_documents(snapshot):
            for column, value in row.items():
                if (
                    column in {"model_version", "implementation_version"}
                    and isinstance(value, str)
                    and value
                ):
                    versions.add(value)
    return tuple(sorted(versions))


def _bundle_content(
    bundle: ProviderEvidenceBundle,
    *,
    include_bundle_id: bool,
) -> dict[str, object]:
    return _bundle_values_content(
        bundle_id=bundle.bundle_id,
        include_bundle_id=include_bundle_id,
        as_of=bundle.as_of,
        tables=bundle.tables,
        scope_summaries=bundle.scope_summaries,
        dataset_summaries=bundle.dataset_summaries,
        missing_tables=bundle.missing_tables,
        model_versions=bundle.model_versions,
        limitations=bundle.limitations,
        framework_version=bundle.framework_version,
        database_schema_version=bundle.database_schema_version,
        implementation_version=bundle.implementation_version,
    )


def _bundle_values_content(
    *,
    bundle_id: str,
    include_bundle_id: bool,
    as_of: datetime,
    tables: tuple[EvidenceTableSnapshot, ...],
    scope_summaries: tuple[ProviderScopeEvidenceSummary, ...],
    dataset_summaries: tuple[DatasetEvidenceBundleSummary, ...],
    missing_tables: tuple[str, ...],
    model_versions: tuple[str, ...],
    limitations: tuple[str, ...],
    framework_version: str,
    database_schema_version: str,
    implementation_version: str,
) -> dict[str, object]:
    document: dict[str, object] = {
        "as_of": as_of.isoformat(),
        "framework_version": framework_version,
        "database_schema_version": database_schema_version,
        "implementation_version": implementation_version,
        "tables": [_table_document(item) for item in tables],
        "scope_summaries": [
            _scope_summary_document(item) for item in scope_summaries
        ],
        "dataset_summaries": [_summary_document(item) for item in dataset_summaries],
        "missing_tables": list(missing_tables),
        "model_versions": list(model_versions),
        "limitations": list(limitations),
    }
    if include_bundle_id:
        document["bundle_id"] = bundle_id
    return document


def _table_document(item: EvidenceTableSnapshot) -> dict[str, object]:
    return {
        "table": item.table,
        "columns": list(item.columns),
        "row_count": item.row_count,
        "rows_hash": item.rows_hash,
        "rows": [list(row) for row in item.rows],
    }


def _summary_document(item: DatasetEvidenceBundleSummary) -> dict[str, object]:
    return {
        "dataset": item.dataset,
        "first_observed_at": item.first_observed_at,
        "last_observed_at": item.last_observed_at,
        "observation_days": item.observation_days,
        "contract_check_count": item.contract_check_count,
        "baseline_count": item.baseline_count,
        "baseline_continuity_ratio": item.baseline_continuity_ratio,
        "baseline_field_coverage_ratio": item.baseline_field_coverage_ratio,
        "baseline_success_ratio": item.baseline_success_ratio,
        "artifact_observation_count": item.artifact_observation_count,
        "artifact_failure_count": item.artifact_failure_count,
        "calibration_completed_count": item.calibration_completed_count,
        "calibration_unavailable_count": item.calibration_unavailable_count,
        "calibration_incompatible_count": item.calibration_incompatible_count,
        "provider_conflict_count": item.provider_conflict_count,
        "high_conflict_count": item.high_conflict_count,
    }


def _scope_summary_document(item: ProviderScopeEvidenceSummary) -> dict[str, object]:
    return {
        "provider": item.provider,
        "dataset": item.dataset,
        "market": item.market,
        "subject": item.subject,
        "first_observed_at": item.first_observed_at,
        "last_observed_at": item.last_observed_at,
        "observation_days": item.observation_days,
        "contract_check_count": item.contract_check_count,
        "baseline_manifest_id": item.baseline_manifest_id,
        "expected_periods": item.expected_periods,
        "observed_periods": item.observed_periods,
        "successful_observation_ratio": item.successful_observation_ratio,
        "field_coverage_ratio": item.field_coverage_ratio,
        "continuity_ratio": item.continuity_ratio,
    }


def _table_names(connection: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }


def _timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"provider evidence timestamp is missing: {field}")
    parsed = datetime.fromisoformat(value)
    require_timezone(parsed, f"provider evidence timestamp {field}")
    return parsed


def _scalar(value: object) -> JsonScalar:
    if value is None or isinstance(value, (str, int, float)) and not isinstance(value, bool):
        return value
    raise ValueError("provider evidence contains a non-scalar SQLite value")


def _canonical_row(row: tuple[JsonScalar, ...]) -> str:
    return json.dumps(row, sort_keys=True, separators=(",", ":"))


def _stable_hash(value: object) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _canonical_dataset(dataset: str) -> str:
    return {
        "china_disclosures": "financial_publication_dates",
        "daily_bars": "global_daily_bars",
    }.get(dataset, dataset)


def _required_string(row: dict[str, JsonScalar], field: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"provider evidence row requires {field}")
    return value


def _scope_identity(row: dict[str, JsonScalar]) -> tuple[str, str, str, str]:
    return (
        _required_string(row, "provider"),
        _canonical_dataset(_required_string(row, "dataset")),
        _required_string(row, "market"),
        _required_string(row, "subject"),
    )


def _latest_baseline_row(
    rows: list[dict[str, JsonScalar]],
    manifest_times: dict[str, datetime],
) -> dict[str, JsonScalar] | None:
    visible = [
        row
        for row in rows
        if _required_string(row, "manifest_id") in manifest_times
    ]
    if not visible:
        return None
    return max(
        visible,
        key=lambda row: (
            manifest_times[_required_string(row, "manifest_id")],
            _required_string(row, "manifest_id"),
        ),
    )


def _optional_int(row: dict[str, JsonScalar] | None, field: str) -> int | None:
    if row is None:
        return None
    value = row.get(field)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"provider evidence scope metric {field} is invalid")
    return value


def _optional_float(row: dict[str, JsonScalar] | None, field: str) -> float | None:
    if row is None:
        return None
    value = row.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"provider evidence scope metric {field} is invalid")
    return float(value)


def _increment(values: dict[str, dict[str, object]], dataset: str, key: str) -> None:
    bucket = values.setdefault(dataset, {})
    current = bucket.get(key, 0)
    if isinstance(current, bool) or not isinstance(current, int):
        raise ValueError(f"provider evidence summary metric {key} is invalid")
    bucket[key] = current + 1


def _average(rows: list[dict[str, JsonScalar]], field: str) -> float | None:
    values = [row.get(field) for row in rows]
    if not values:
        return None
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in values):
        raise ValueError(f"provider evidence baseline metric {field} is invalid")
    numeric = [float(value) for value in values if isinstance(value, (int, float))]
    return round(sum(numeric) / len(numeric), 6)


def _bucket_int(bucket: dict[str, object], key: str) -> int:
    value = bucket.get(key, 0)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"provider evidence summary count {key} is invalid")
    return value


def _bucket_optional_float(bucket: dict[str, object], key: str) -> float | None:
    value = bucket.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"provider evidence summary ratio {key} is invalid")
    return float(value)


def _ratio_text(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.1%}"


def _reject_local_paths(value: object, *, path: str = "bundle") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            _reject_local_paths(nested, path=f"{path}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            _reject_local_paths(nested, path=f"{path}[{index}]")
        return
    if isinstance(value, str) and (
        value.startswith(("/Users/", "/home/", "file://", "~/"))
        or _WINDOWS_PATH.match(value)
    ):
        raise ValueError(f"{path} contains a local filesystem path")


__all__ = [
    "DatasetEvidenceBundleSummary",
    "EvidenceTableSnapshot",
    "ProviderEvidenceBundle",
    "ProviderEvidenceBundleExporter",
    "ProviderScopeEvidenceSummary",
    "provider_evidence_bundle_json",
    "reconstruct_dataset_summaries",
    "reconstruct_provider_scope_summaries",
    "render_provider_evidence_bundle_markdown",
    "serialize_provider_evidence_bundle",
    "verify_provider_evidence_document",
]
