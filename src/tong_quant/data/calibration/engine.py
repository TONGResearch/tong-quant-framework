import json
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256

from tong_quant.data.calibration.models import (
    CalibrationValue,
    DatasetConfidenceAssessment,
    ProviderCalibrationSnapshot,
    ProviderConflict,
    ProviderConflictSeverity,
    ProviderConflictType,
    ProviderConsistencyReport,
)
from tong_quant.domain.enums import DataTrustLevel
from tong_quant.version import PROVIDER_CALIBRATION_VERSION


@dataclass(frozen=True, slots=True)
class ProviderCalibrationEngine:
    model_version: str = PROVIDER_CALIBRATION_VERSION

    def compare(
        self,
        primary: ProviderCalibrationSnapshot,
        secondary: ProviderCalibrationSnapshot,
        *,
        fields: tuple[str, ...],
        compared_at: datetime | None = None,
    ) -> ProviderConsistencyReport:
        if primary.dataset != secondary.dataset:
            raise ValueError("provider calibration requires the same dataset")
        if primary.provider == secondary.provider:
            raise ValueError("provider calibration requires distinct providers")
        primary_records = {record.key: record for record in primary.records}
        secondary_records = {record.key: record for record in secondary.records}
        primary_keys = set(primary_records)
        secondary_keys = set(secondary_records)
        common = primary_keys & secondary_keys
        denominator = len(primary_keys) + len(secondary_keys)
        key_overlap = 100.0 if denominator == 0 else 200 * len(common) / denominator
        field_scores: dict[str, float] = {}
        for field in fields:
            comparable = 0
            matched = 0
            for key in common:
                left = primary_records[key].fields.get(field)
                right = secondary_records[key].fields.get(field)
                if left is None and right is None:
                    continue
                comparable += 1
                if _canonical_value(left) == _canonical_value(right):
                    matched += 1
            field_scores[field] = (
                0.0 if comparable == 0 else matched / comparable * 100
            )
        field_agreement = (
            sum(field_scores.values()) / len(field_scores)
            if field_scores
            else key_overlap
        )
        consistency = key_overlap * 0.60 + field_agreement * 0.40
        limitations = (*primary.limitations, *secondary.limitations)
        if not fields:
            limitations = (*limitations, "No field-level comparisons were requested")
        compared = compared_at or datetime.now(UTC)
        payload = {
            "dataset": primary.dataset,
            "primary": primary.provider,
            "secondary": secondary.provider,
            "primary_as_of": primary.as_of.isoformat(),
            "secondary_as_of": secondary.as_of.isoformat(),
            "primary_records": [
                {"key": record.key, "fields": record.fields}
                for record in sorted(primary.records, key=lambda item: item.key)
            ],
            "secondary_records": [
                {"key": record.key, "fields": record.fields}
                for record in sorted(secondary.records, key=lambda item: item.key)
            ],
            "fields": fields,
            "model_version": self.model_version,
        }
        comparison_hash = sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return ProviderConsistencyReport(
            report_id=comparison_hash,
            dataset=primary.dataset,
            primary_provider=primary.provider,
            secondary_provider=secondary.provider,
            compared_at=compared,
            primary_count=len(primary_keys),
            secondary_count=len(secondary_keys),
            matched_count=len(common),
            primary_only_count=len(primary_keys - secondary_keys),
            secondary_only_count=len(secondary_keys - primary_keys),
            key_overlap_score=round(key_overlap, 2),
            field_match_scores={
                key: round(value, 2) for key, value in field_scores.items()
            },
            consistency_score=round(consistency, 2),
            trust_level=_trust_for_consistency(consistency),
            limitations=tuple(dict.fromkeys(limitations)),
            comparison_hash=comparison_hash,
            model_version=self.model_version,
        )

    def detect_conflicts(
        self,
        primary: ProviderCalibrationSnapshot,
        secondary: ProviderCalibrationSnapshot,
        report: ProviderConsistencyReport,
        *,
        fields: tuple[str, ...],
    ) -> tuple[ProviderConflict, ...]:
        primary_records = {record.key: record for record in primary.records}
        secondary_records = {record.key: record for record in secondary.records}
        conflicts: list[ProviderConflict] = []
        for key in sorted(set(primary_records) | set(secondary_records)):
            left = primary_records.get(key)
            right = secondary_records.get(key)
            if left is None:
                conflicts.append(
                    _conflict(
                        report,
                        key=key,
                        field_name="__record__",
                        conflict_type=ProviderConflictType.MISSING_PRIMARY,
                        primary_value=None,
                        secondary_value="present",
                        severity=ProviderConflictSeverity.HIGH,
                    )
                )
                continue
            if right is None:
                conflicts.append(
                    _conflict(
                        report,
                        key=key,
                        field_name="__record__",
                        conflict_type=ProviderConflictType.MISSING_SECONDARY,
                        primary_value="present",
                        secondary_value=None,
                        severity=ProviderConflictSeverity.HIGH,
                    )
                )
                continue
            for field_name in fields:
                left_value = left.fields.get(field_name)
                right_value = right.fields.get(field_name)
                if _canonical_value(left_value) == _canonical_value(right_value):
                    continue
                conflicts.append(
                    _conflict(
                        report,
                        key=key,
                        field_name=field_name,
                        conflict_type=ProviderConflictType.VALUE_MISMATCH,
                        primary_value=left_value,
                        secondary_value=right_value,
                        severity=(
                            ProviderConflictSeverity.HIGH
                            if field_name
                            in {
                                "event_type",
                                "effective_date",
                                "delist_date",
                                "actual_date",
                                "published_at",
                                "is_st",
                            }
                            else ProviderConflictSeverity.MEDIUM
                        ),
                    )
                )
        return tuple(conflicts)

    def assess_confidence(
        self,
        report: ProviderConsistencyReport,
        conflicts: tuple[ProviderConflict, ...],
        *,
        temporal_alignment_score: float,
    ) -> DatasetConfidenceAssessment:
        if not 0 <= temporal_alignment_score <= 100:
            raise ValueError("temporal alignment must be between zero and 100")
        denominator = max(report.primary_count + report.secondary_count, 1)
        conflict_free = max(0.0, 100.0 - len(conflicts) / denominator * 100)
        components = {
            "provider_consistency": report.consistency_score,
            "conflict_free": conflict_free,
            "temporal_alignment": temporal_alignment_score,
        }
        score = (
            components["provider_consistency"] * 0.60
            + components["conflict_free"] * 0.25
            + components["temporal_alignment"] * 0.15
        )
        critical = sum(
            conflict.severity is ProviderConflictSeverity.HIGH
            for conflict in conflicts
        )
        if critical:
            score = min(score, 79.0)
        warnings = tuple(
            warning
            for warning, include in (
                (f"{len(conflicts)} provider conflicts detected", bool(conflicts)),
                (f"{critical} high-severity conflicts require review", bool(critical)),
                (
                    "provider snapshots are not aligned to the same as_of",
                    temporal_alignment_score < 100,
                ),
            )
            if include
        )
        payload = {
            "report_id": report.report_id,
            "score": round(score, 2),
            "components": components,
            "conflicts": [conflict.conflict_id for conflict in conflicts],
        }
        assessment_id = sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return DatasetConfidenceAssessment(
            assessment_id=assessment_id,
            report_id=report.report_id,
            dataset=report.dataset,
            assessed_at=report.compared_at,
            confidence_score=round(score, 2),
            trust_level=_trust_for_consistency(score),
            component_scores={
                key: round(value, 2) for key, value in components.items()
            },
            conflict_count=len(conflicts),
            critical_conflict_count=critical,
            warnings=warnings,
        )


def _canonical_value(value: object) -> str:
    if isinstance(value, float):
        return format(value, ".12g")
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _trust_for_consistency(score: float) -> DataTrustLevel:
    if score >= 95:
        return DataTrustLevel.HIGH
    if score >= 80:
        return DataTrustLevel.MEDIUM
    if score >= 50:
        return DataTrustLevel.LOW
    return DataTrustLevel.UNKNOWN


def _conflict(
    report: ProviderConsistencyReport,
    *,
    key: str,
    field_name: str,
    conflict_type: ProviderConflictType,
    primary_value: CalibrationValue,
    secondary_value: CalibrationValue,
    severity: ProviderConflictSeverity,
) -> ProviderConflict:
    fingerprint_payload = {
        "dataset": report.dataset,
        "primary": report.primary_provider,
        "secondary": report.secondary_provider,
        "key": key,
        "field": field_name,
        "type": conflict_type.value,
    }
    fingerprint = sha256(
        json.dumps(
            fingerprint_payload, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    conflict_id = sha256(f"{report.report_id}:{fingerprint}".encode()).hexdigest()
    return ProviderConflict(
        conflict_id=conflict_id,
        conflict_fingerprint=fingerprint,
        report_id=report.report_id,
        dataset=report.dataset,
        record_key=key,
        field_name=field_name,
        conflict_type=conflict_type,
        primary_provider=report.primary_provider,
        secondary_provider=report.secondary_provider,
        primary_value=primary_value,
        secondary_value=secondary_value,
        severity=severity,
        detected_at=report.compared_at,
    )


__all__ = ["ProviderCalibrationEngine"]
