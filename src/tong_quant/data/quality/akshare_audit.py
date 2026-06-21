import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum

import akshare as ak

from tong_quant.core.security import redact_sensitive_text
from tong_quant.data.calibration.base import ProviderCalibrationSource
from tong_quant.data.calibration.models import (
    CalibrationDataset,
    CalibrationRecord,
    ProviderCalibrationSnapshot,
)
from tong_quant.data.calibration.readiness_report import PhaseThreeQuerySpec
from tong_quant.domain.models import require_timezone
from tong_quant.version import AKSHARE_QUALITY_AUDIT_VERSION


class AkShareAccessStatus(StrEnum):
    AVAILABLE = "available"
    EMPTY = "empty"
    ERROR = "error"


class HistoricalEvidenceScope(StrEnum):
    DATE_SCOPED = "date_scoped"
    PARTIAL_HISTORY = "partial_history"
    CURRENT_SNAPSHOT = "current_snapshot"
    TERMINAL_RECORDS = "terminal_records"


@dataclass(frozen=True, slots=True)
class AkShareDatasetAudit:
    dataset: CalibrationDataset
    query_parameters: dict[str, str]
    access_status: AkShareAccessStatus
    record_count: int
    expected_record_coverage: float | None
    required_field_completeness: float | None
    date_validity: float | None
    key_uniqueness: float | None
    evidence_scope: HistoricalEvidenceScope
    snapshot_hash: str | None
    limitations: tuple[str, ...]
    recommended_usage: str

    def __post_init__(self) -> None:
        scores = (
            self.expected_record_coverage,
            self.required_field_completeness,
            self.date_validity,
            self.key_uniqueness,
        )
        if any(score is not None and not 0 <= score <= 100 for score in scores):
            raise ValueError("AKShare audit scores must be between zero and 100")
        if self.snapshot_hash is not None and len(self.snapshot_hash) != 64:
            raise ValueError("AKShare audit snapshot_hash must be a SHA-256 digest")


@dataclass(frozen=True, slots=True)
class AkShareQualityAuditReport:
    generated_at: datetime
    akshare_version: str
    datasets: tuple[AkShareDatasetAudit, ...]
    model_version: str = AKSHARE_QUALITY_AUDIT_VERSION

    def __post_init__(self) -> None:
        require_timezone(self.generated_at, "AKShare quality audit generated_at")


_REQUIRED_FIELDS: dict[CalibrationDataset, tuple[str, ...]] = {
    CalibrationDataset.SECURITY_LIFECYCLE: ("event_type", "effective_date"),
    CalibrationDataset.ST_STATUS: ("is_st", "effective_date"),
    CalibrationDataset.SUSPENSION_STATUS: ("event_type", "effective_date"),
    CalibrationDataset.DELISTING_RECORDS: ("delist_date",),
    CalibrationDataset.FINANCIAL_PUBLICATION_DATES: ("actual_date",),
    CalibrationDataset.FUNDAMENTAL_REVISIONS: (
        "published_at",
        "report_type",
        "update_flag",
    ),
    CalibrationDataset.CORPORATE_ACTIONS: ("effective_date",),
    CalibrationDataset.UNIVERSE_COVERAGE: ("listed",),
    CalibrationDataset.CSI300_MEMBERSHIP: ("member",),
    CalibrationDataset.CSI500_MEMBERSHIP: ("member",),
    CalibrationDataset.CSI1000_MEMBERSHIP: ("member",),
}

_DATE_FIELDS: dict[CalibrationDataset, tuple[str, ...]] = {
    CalibrationDataset.SECURITY_LIFECYCLE: ("effective_date", "delist_date"),
    CalibrationDataset.ST_STATUS: ("effective_date", "effective_to", "ann_date"),
    CalibrationDataset.SUSPENSION_STATUS: ("effective_date",),
    CalibrationDataset.DELISTING_RECORDS: ("delist_date",),
    CalibrationDataset.FINANCIAL_PUBLICATION_DATES: (
        "actual_date",
        "ann_date",
        "modify_date",
    ),
    CalibrationDataset.FUNDAMENTAL_REVISIONS: ("published_at",),
    CalibrationDataset.CORPORATE_ACTIONS: ("effective_date", "ann_date"),
    CalibrationDataset.UNIVERSE_COVERAGE: (),
    CalibrationDataset.CSI300_MEMBERSHIP: ("effective_date",),
    CalibrationDataset.CSI500_MEMBERSHIP: ("effective_date",),
    CalibrationDataset.CSI1000_MEMBERSHIP: ("effective_date",),
}

_EVIDENCE_SCOPE: dict[CalibrationDataset, HistoricalEvidenceScope] = {
    CalibrationDataset.SECURITY_LIFECYCLE: HistoricalEvidenceScope.PARTIAL_HISTORY,
    CalibrationDataset.ST_STATUS: HistoricalEvidenceScope.PARTIAL_HISTORY,
    CalibrationDataset.SUSPENSION_STATUS: HistoricalEvidenceScope.DATE_SCOPED,
    CalibrationDataset.DELISTING_RECORDS: HistoricalEvidenceScope.TERMINAL_RECORDS,
    CalibrationDataset.FINANCIAL_PUBLICATION_DATES: (
        HistoricalEvidenceScope.DATE_SCOPED
    ),
    CalibrationDataset.FUNDAMENTAL_REVISIONS: HistoricalEvidenceScope.DATE_SCOPED,
    CalibrationDataset.CORPORATE_ACTIONS: HistoricalEvidenceScope.PARTIAL_HISTORY,
    CalibrationDataset.UNIVERSE_COVERAGE: HistoricalEvidenceScope.CURRENT_SNAPSHOT,
    CalibrationDataset.CSI300_MEMBERSHIP: HistoricalEvidenceScope.CURRENT_SNAPSHOT,
    CalibrationDataset.CSI500_MEMBERSHIP: HistoricalEvidenceScope.CURRENT_SNAPSHOT,
    CalibrationDataset.CSI1000_MEMBERSHIP: HistoricalEvidenceScope.CURRENT_SNAPSHOT,
}


@dataclass(frozen=True, slots=True)
class AkShareQualityAuditor:
    def audit(
        self,
        source: ProviderCalibrationSource,
        specs: tuple[PhaseThreeQuerySpec, ...],
        *,
        generated_at: datetime,
    ) -> AkShareQualityAuditReport:
        return AkShareQualityAuditReport(
            generated_at=generated_at,
            akshare_version=str(ak.__version__),
            datasets=tuple(self._audit_dataset(source, spec) for spec in specs),
        )

    def _audit_dataset(
        self,
        source: ProviderCalibrationSource,
        spec: PhaseThreeQuerySpec,
    ) -> AkShareDatasetAudit:
        dataset = spec.query.dataset
        try:
            snapshot = source.calibration_snapshot(spec.query)
        except Exception as error:
            return AkShareDatasetAudit(
                dataset=dataset,
                query_parameters=spec.query.parameters,
                access_status=AkShareAccessStatus.ERROR,
                record_count=0,
                expected_record_coverage=0 if spec.expected_records else None,
                required_field_completeness=None,
                date_validity=None,
                key_uniqueness=None,
                evidence_scope=_EVIDENCE_SCOPE[dataset],
                snapshot_hash=None,
                limitations=(
                    f"provider call failed: {redact_sensitive_text(str(error))}",
                ),
                recommended_usage="Unavailable until provider access is restored",
            )
        records = snapshot.records
        return AkShareDatasetAudit(
            dataset=dataset,
            query_parameters=spec.query.parameters,
            access_status=(
                AkShareAccessStatus.AVAILABLE
                if records
                else AkShareAccessStatus.EMPTY
            ),
            record_count=len(records),
            expected_record_coverage=_expected_coverage(records, spec.expected_records),
            required_field_completeness=_required_field_completeness(
                dataset, records
            ),
            date_validity=_date_validity(records, _DATE_FIELDS[dataset]),
            key_uniqueness=_key_uniqueness(records),
            evidence_scope=_EVIDENCE_SCOPE[dataset],
            snapshot_hash=_snapshot_hash(snapshot),
            limitations=snapshot.limitations,
            recommended_usage=_recommendation(_EVIDENCE_SCOPE[dataset]),
        )


def render_akshare_audit_markdown(report: AkShareQualityAuditReport) -> str:
    lines = [
        "# AKShare Data Quality Audit",
        "",
        f"Generated at: {report.generated_at.isoformat()}",
        f"AKShare version: `{report.akshare_version}`",
        "",
        "Quality metrics describe the observed normalized response. They do not "
        "upgrade point-in-time trust or prove historical continuity.",
        "",
        "| Dataset | Access | Records | Expected coverage | Field completeness | "
        "Date validity | Unique keys | Evidence scope |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for audit in report.datasets:
        lines.append(
            f"| {audit.dataset.value} | {audit.access_status.value} | "
            f"{audit.record_count} | {_score(audit.expected_record_coverage)} | "
            f"{_score(audit.required_field_completeness)} | "
            f"{_score(audit.date_validity)} | {_score(audit.key_uniqueness)} | "
            f"{audit.evidence_scope.value} |"
        )
    lines.extend(("", "## Dataset Guidance", ""))
    for audit in report.datasets:
        lines.append(f"### {audit.dataset.value}")
        lines.append(f"- Usage: {audit.recommended_usage}")
        lines.append(
            "- Query scope: "
            + (
                ", ".join(
                    f"{key}={value}"
                    for key, value in sorted(audit.query_parameters.items())
                )
                or "no parameters"
            )
        )
        lines.extend(f"- Limitation: {item}" for item in audit.limitations)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def akshare_audit_json(report: AkShareQualityAuditReport) -> str:
    return json.dumps(asdict(report), default=_json_default, indent=2, sort_keys=True)


def _field_completeness(
    records: tuple[CalibrationRecord, ...],
    fields: tuple[str, ...],
) -> float | None:
    if not records or not fields:
        return None
    total = len(records) * len(fields)
    present = sum(
        not _is_missing(record.fields.get(field))
        for record in records
        for field in fields
    )
    return round(present / total * 100, 2)


def _required_field_completeness(
    dataset: CalibrationDataset,
    records: tuple[CalibrationRecord, ...],
) -> float | None:
    if dataset is not CalibrationDataset.SECURITY_LIFECYCLE:
        return _field_completeness(records, _REQUIRED_FIELDS[dataset])
    if not records:
        return None
    valid = sum(_valid_lifecycle_record(record) for record in records)
    return round(valid / len(records) * 100, 2)


def _valid_lifecycle_record(record: CalibrationRecord) -> bool:
    fields = record.fields
    if not _is_missing(fields.get("event_type")):
        return not _is_missing(fields.get("effective_date"))
    if not _is_missing(fields.get("is_st")):
        return not _is_missing(fields.get("effective_date"))
    return not _is_missing(fields.get("delist_date"))


def _date_validity(
    records: tuple[CalibrationRecord, ...],
    fields: tuple[str, ...],
) -> float | None:
    values = [
        record.fields.get(field)
        for record in records
        for field in fields
        if not _is_missing(record.fields.get(field))
    ]
    if not values:
        return None
    valid = sum(
        isinstance(value, str) and len(value) == 8 and value.isdigit()
        for value in values
    )
    return round(valid / len(values) * 100, 2)


def _key_uniqueness(records: tuple[CalibrationRecord, ...]) -> float | None:
    if not records:
        return None
    return round(len({record.key for record in records}) / len(records) * 100, 2)


def _expected_coverage(
    records: tuple[CalibrationRecord, ...],
    expected_records: int | None,
) -> float | None:
    if expected_records is None:
        return None
    return round(min(len(records) / expected_records, 1) * 100, 2)


def _snapshot_hash(snapshot: ProviderCalibrationSnapshot) -> str:
    payload = {
        "provider": snapshot.provider,
        "dataset": snapshot.dataset,
        "records": [asdict(record) for record in snapshot.records],
        "limitations": snapshot.limitations,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _recommendation(scope: HistoricalEvidenceScope) -> str:
    return {
        HistoricalEvidenceScope.DATE_SCOPED: (
            "Use with explicit dates and provider limitations; backfill multiple periods"
        ),
        HistoricalEvidenceScope.PARTIAL_HISTORY: (
            "Use as incomplete historical evidence; never infer missing intervals"
        ),
        HistoricalEvidenceScope.CURRENT_SNAPSHOT: (
            "Use for forward snapshot collection only, not backward reconstruction"
        ),
        HistoricalEvidenceScope.TERMINAL_RECORDS: (
            "Use for terminal-event evidence; warning-period history remains separate"
        ),
    }[scope]


def _is_missing(value: object) -> bool:
    return value is None or value == ""


def _score(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f}%"


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, StrEnum):
        return value.value
    raise TypeError(f"unsupported AKShare audit JSON type: {type(value).__name__}")


__all__ = [
    "AkShareAccessStatus",
    "AkShareDatasetAudit",
    "AkShareQualityAuditReport",
    "AkShareQualityAuditor",
    "HistoricalEvidenceScope",
    "akshare_audit_json",
    "render_akshare_audit_markdown",
]
