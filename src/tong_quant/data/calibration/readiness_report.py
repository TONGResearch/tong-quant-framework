import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum

from tong_quant.core.security import redact_sensitive_text
from tong_quant.data.calibration.base import ProviderCalibrationSource
from tong_quant.data.calibration.coordinator import ProviderCalibrationCoordinator
from tong_quant.data.calibration.models import (
    DEFAULT_CALIBRATION_FIELDS,
    CalibrationDataset,
    CalibrationQuery,
    ProviderCalibrationSnapshot,
)
from tong_quant.data.models import PITReadinessAssessment
from tong_quant.data.readiness import (
    PITReadinessEvaluator,
    PITReadinessInput,
    apply_provider_confidence,
)
from tong_quant.domain.enums import (
    AvailabilityPrecision,
    DataTrustLevel,
    PITReadinessClassification,
)
from tong_quant.domain.models import require_timezone
from tong_quant.version import DATA_READINESS_VERSION


class ProviderAccessStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class PhaseThreeQuerySpec:
    query: CalibrationQuery
    framework_areas: tuple[str, ...]
    availability_precision: AvailabilityPrecision
    primary_trust_level: DataTrustLevel
    historical_continuity_score: float
    revision_score: float = 0.0
    expected_records: int | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.historical_continuity_score <= 100:
            raise ValueError("historical continuity score must be between zero and 100")
        if not 0 <= self.revision_score <= 100:
            raise ValueError("revision score must be between zero and 100")
        if self.expected_records is not None and self.expected_records <= 0:
            raise ValueError("expected records must be positive when provided")


@dataclass(frozen=True, slots=True)
class DatasetReadinessReport:
    dataset: CalibrationDataset
    assessed_at: datetime
    query_parameters: dict[str, str]
    primary_status: ProviderAccessStatus
    secondary_status: ProviderAccessStatus
    primary_records: int
    secondary_records: int | None
    coverage_percent: float | None
    trust_level: DataTrustLevel
    availability_precision: AvailabilityPrecision
    provider_consistency_score: float | None
    historical_continuity_score: float
    known_limitations: tuple[str, ...]
    recommended_usage: str
    pit_readiness: PITReadinessAssessment
    model_version: str = DATA_READINESS_VERSION

    def __post_init__(self) -> None:
        require_timezone(self.assessed_at, "dataset readiness assessed_at")
        if self.coverage_percent is not None and not 0 <= self.coverage_percent <= 100:
            raise ValueError("coverage percent must be between zero and 100")


@dataclass(frozen=True, slots=True)
class FrameworkAreaReadiness:
    area: str
    datasets: tuple[str, ...]
    classification: PITReadinessClassification
    known_gaps: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FrameworkDataReadinessDashboard:
    generated_at: datetime
    datasets: tuple[DatasetReadinessReport, ...]
    framework_areas: tuple[FrameworkAreaReadiness, ...]
    overall_classification: PITReadinessClassification
    model_version: str = DATA_READINESS_VERSION

    def __post_init__(self) -> None:
        require_timezone(self.generated_at, "dashboard generated_at")


@dataclass(frozen=True, slots=True)
class PhaseThreeCalibrationRunner:
    coordinator: ProviderCalibrationCoordinator
    readiness_evaluator: PITReadinessEvaluator = PITReadinessEvaluator()

    def run(
        self,
        primary: ProviderCalibrationSource,
        secondary: ProviderCalibrationSource | None,
        specs: tuple[PhaseThreeQuerySpec, ...],
        *,
        secondary_unavailable_reason: str = "secondary provider is not configured",
    ) -> FrameworkDataReadinessDashboard:
        reports = tuple(
            self._run_dataset(
                primary,
                secondary,
                spec,
                secondary_unavailable_reason=secondary_unavailable_reason,
            )
            for spec in specs
        )
        areas = _area_readiness(specs, reports)
        return FrameworkDataReadinessDashboard(
            generated_at=max(
                (report.assessed_at for report in reports),
                default=datetime.now(UTC),
            ),
            datasets=reports,
            framework_areas=areas,
            overall_classification=_worst_classification(
                tuple(area.classification for area in areas)
            ),
        )

    def _run_dataset(
        self,
        primary: ProviderCalibrationSource,
        secondary: ProviderCalibrationSource | None,
        spec: PhaseThreeQuerySpec,
        *,
        secondary_unavailable_reason: str,
    ) -> DatasetReadinessReport:
        try:
            primary_snapshot = primary.calibration_snapshot(spec.query)
        except Exception as error:
            return self._unavailable_report(
                spec,
                primary_error=redact_sensitive_text(str(error)),
                secondary_error=secondary_unavailable_reason,
            )
        if secondary is None:
            return self._single_source_report(
                spec,
                primary_snapshot,
                secondary_unavailable_reason,
            )
        try:
            secondary_snapshot = secondary.calibration_snapshot(spec.query)
        except Exception as error:
            return self._single_source_report(
                spec,
                primary_snapshot,
                redact_sensitive_text(str(error)),
            )
        result = self.coordinator.run_snapshots(
            primary_snapshot,
            secondary_snapshot,
            fields=DEFAULT_CALIBRATION_FIELDS[spec.query.dataset],
            compared_at=spec.query.as_of,
        )
        expected = max(
            len(primary_snapshot.records),
            len(secondary_snapshot.records),
            spec.expected_records or 0,
            1,
        )
        observed = result.report.matched_count
        coverage = observed / expected * 100
        trust = _weaker_trust(spec.primary_trust_level, result.report.trust_level)
        readiness_input = PITReadinessInput(
            dataset=spec.query.dataset.value,
            expected_records=expected,
            observed_records=observed,
            trust_level=trust,
            availability_score=_availability_score(spec.availability_precision),
            revision_score=spec.revision_score,
            continuity_score=spec.historical_continuity_score,
            provider_consistency_required=True,
            assumptions=("Coverage is matched records divided by expected records",),
        )
        readiness = self.readiness_evaluator.evaluate(
            apply_provider_confidence(readiness_input, result.confidence),
            assessed_at=spec.query.as_of,
        )
        limitations = tuple(
            dict.fromkeys(
                (
                    *primary_snapshot.limitations,
                    *secondary_snapshot.limitations,
                    *result.report.limitations,
                    *readiness.warnings,
                )
            )
        )
        return DatasetReadinessReport(
            dataset=spec.query.dataset,
            assessed_at=spec.query.as_of,
            query_parameters=spec.query.parameters,
            primary_status=ProviderAccessStatus.AVAILABLE,
            secondary_status=ProviderAccessStatus.AVAILABLE,
            primary_records=len(primary_snapshot.records),
            secondary_records=len(secondary_snapshot.records),
            coverage_percent=round(coverage, 2),
            trust_level=trust,
            availability_precision=spec.availability_precision,
            provider_consistency_score=result.report.consistency_score,
            historical_continuity_score=spec.historical_continuity_score,
            known_limitations=limitations,
            recommended_usage=_recommendation(readiness.classification),
            pit_readiness=readiness,
        )

    def _single_source_report(
        self,
        spec: PhaseThreeQuerySpec,
        primary_snapshot: ProviderCalibrationSnapshot,
        secondary_error: str,
    ) -> DatasetReadinessReport:
        expected = spec.expected_records or 1
        observed = min(len(primary_snapshot.records), expected) if spec.expected_records else 0
        readiness = self.readiness_evaluator.evaluate(
            PITReadinessInput(
                dataset=spec.query.dataset.value,
                expected_records=expected,
                observed_records=observed,
                trust_level=spec.primary_trust_level,
                coverage_known=False,
                availability_score=_availability_score(spec.availability_precision),
                revision_score=spec.revision_score,
                continuity_score=spec.historical_continuity_score,
                provider_consistency_required=True,
                warnings=(f"secondary provider unavailable: {secondary_error}",),
                assumptions=(
                    "Cross-provider coverage and consistency are unmeasurable",
                ),
            ),
            assessed_at=spec.query.as_of,
        )
        return DatasetReadinessReport(
            dataset=spec.query.dataset,
            assessed_at=spec.query.as_of,
            query_parameters=spec.query.parameters,
            primary_status=ProviderAccessStatus.AVAILABLE,
            secondary_status=ProviderAccessStatus.UNAVAILABLE,
            primary_records=len(primary_snapshot.records),
            secondary_records=None,
            coverage_percent=None,
            trust_level=spec.primary_trust_level,
            availability_precision=spec.availability_precision,
            provider_consistency_score=None,
            historical_continuity_score=spec.historical_continuity_score,
            known_limitations=tuple(
                dict.fromkeys(
                    (
                        *primary_snapshot.limitations,
                        f"secondary provider unavailable: {secondary_error}",
                        *readiness.warnings,
                    )
                )
            ),
            recommended_usage=_recommendation(readiness.classification),
            pit_readiness=readiness,
        )

    def _unavailable_report(
        self,
        spec: PhaseThreeQuerySpec,
        *,
        primary_error: str,
        secondary_error: str,
    ) -> DatasetReadinessReport:
        readiness = self.readiness_evaluator.evaluate(
            PITReadinessInput(
                dataset=spec.query.dataset.value,
                expected_records=1,
                observed_records=0,
                trust_level=DataTrustLevel.UNKNOWN,
                missing_critical_fields=("primary_provider_data",),
                provider_consistency_required=True,
                warnings=(f"primary provider unavailable: {primary_error}",),
            ),
            assessed_at=spec.query.as_of,
        )
        return DatasetReadinessReport(
            dataset=spec.query.dataset,
            assessed_at=spec.query.as_of,
            query_parameters=spec.query.parameters,
            primary_status=ProviderAccessStatus.UNAVAILABLE,
            secondary_status=ProviderAccessStatus.UNAVAILABLE,
            primary_records=0,
            secondary_records=None,
            coverage_percent=None,
            trust_level=DataTrustLevel.UNKNOWN,
            availability_precision=AvailabilityPrecision.UNKNOWN,
            provider_consistency_score=None,
            historical_continuity_score=0,
            known_limitations=(
                f"primary provider unavailable: {primary_error}",
                f"secondary provider unavailable: {secondary_error}",
            ),
            recommended_usage=_recommendation(readiness.classification),
            pit_readiness=readiness,
        )


def render_dashboard_markdown(dashboard: FrameworkDataReadinessDashboard) -> str:
    lines = [
        "# Framework Data Readiness Dashboard",
        "",
        f"Generated at: {dashboard.generated_at.isoformat()}",
        f"Overall: **{dashboard.overall_classification.value.upper()}**",
        "",
        "## Dataset Readiness",
        "",
        "| Dataset | Primary | Secondary | Coverage | Trust | Precision | "
        "Consistency | Continuity | PIT | Usage |",
        "|---|---:|---:|---:|---|---|---:|---:|---|---|",
    ]
    for report in dashboard.datasets:
        coverage = (
            "N/A"
            if report.coverage_percent is None
            else f"{report.coverage_percent:.2f}%"
        )
        consistency = (
            "N/A"
            if report.provider_consistency_score is None
            else f"{report.provider_consistency_score:.2f}"
        )
        lines.append(
            "| "
            + " | ".join(
                (
                    report.dataset.value,
                    str(report.primary_records),
                    (
                        "N/A"
                        if report.secondary_records is None
                        else str(report.secondary_records)
                    ),
                    coverage,
                    report.trust_level.value,
                    report.availability_precision.value,
                    consistency,
                    f"{report.historical_continuity_score:.2f}",
                    report.pit_readiness.classification.value,
                    report.recommended_usage,
                )
            )
            + " |"
        )
    lines.extend(("", "## Framework Areas", "", "| Area | PIT | Datasets | Gaps |"))
    lines.append("|---|---|---|---|")
    for area in dashboard.framework_areas:
        lines.append(
            f"| {area.area} | {area.classification.value} | "
            f"{', '.join(area.datasets)} | {', '.join(area.known_gaps) or 'None'} |"
        )
    lines.extend(("", "## Query Scope", ""))
    for report in dashboard.datasets:
        parameters = ", ".join(
            f"{key}={value}" for key, value in sorted(report.query_parameters.items())
        )
        lines.append(f"- `{report.dataset.value}`: {parameters or 'no parameters'}")
    lines.extend(("", "## Known Limitations", ""))
    for report in dashboard.datasets:
        lines.append(f"### {report.dataset.value}")
        lines.extend(f"- {limitation}" for limitation in report.known_limitations)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def dashboard_json(dashboard: FrameworkDataReadinessDashboard) -> str:
    return json.dumps(asdict(dashboard), default=_json_default, indent=2, sort_keys=True)


def _area_readiness(
    specs: tuple[PhaseThreeQuerySpec, ...],
    reports: tuple[DatasetReadinessReport, ...],
) -> tuple[FrameworkAreaReadiness, ...]:
    report_by_dataset = {report.dataset: report for report in reports}
    area_datasets: dict[str, list[CalibrationDataset]] = {}
    for spec in specs:
        for area in spec.framework_areas:
            area_datasets.setdefault(area, []).append(spec.query.dataset)
    area_gaps = {
        "Market Regime Inputs": (
            "price trend, breadth, turnover, volatility, and relative strength "
            "are not calibrated here",
        ),
        "Research Inputs": ("news, policy, and industry datasets remain outside Phase III",),
        "Validation Inputs": ("market bars and outcome labels require a separate audit",),
    }
    areas = []
    for area, datasets in area_datasets.items():
        classifications = tuple(
            report_by_dataset[dataset].pit_readiness.classification
            for dataset in datasets
        )
        classification = _worst_classification(classifications)
        if area_gaps.get(area) and classification is PITReadinessClassification.USABLE:
            classification = PITReadinessClassification.CAUTION
        areas.append(
            FrameworkAreaReadiness(
                area=area,
                datasets=tuple(dataset.value for dataset in datasets),
                classification=classification,
                known_gaps=area_gaps.get(area, ()),
            )
        )
    return tuple(sorted(areas, key=lambda item: item.area))


def _worst_classification(
    classifications: tuple[PITReadinessClassification, ...],
) -> PITReadinessClassification:
    rank = {
        PITReadinessClassification.USABLE: 0,
        PITReadinessClassification.CAUTION: 1,
        PITReadinessClassification.UNSUITABLE: 2,
    }
    return max(classifications, key=rank.__getitem__, default=PITReadinessClassification.UNSUITABLE)


def _availability_score(precision: AvailabilityPrecision) -> float:
    return {
        AvailabilityPrecision.EXACT: 100,
        AvailabilityPrecision.DATE_ONLY: 80,
        AvailabilityPrecision.ESTIMATED: 50,
        AvailabilityPrecision.RETRIEVAL_TIME: 25,
        AvailabilityPrecision.UNKNOWN: 0,
    }[precision]


def _weaker_trust(
    left: DataTrustLevel,
    right: DataTrustLevel,
) -> DataTrustLevel:
    levels = (
        DataTrustLevel.UNKNOWN,
        DataTrustLevel.LOW,
        DataTrustLevel.MEDIUM,
        DataTrustLevel.HIGH,
        DataTrustLevel.VERIFIED,
    )
    return levels[min(levels.index(left), levels.index(right))]


def _recommendation(classification: PITReadinessClassification) -> str:
    return {
        PITReadinessClassification.USABLE: "Historical research with recorded limitations",
        PITReadinessClassification.CAUTION: "Research and shadow validation only",
        PITReadinessClassification.UNSUITABLE: "Diagnostics only; exclude from historical claims",
    }[classification]


def _json_default(value: object) -> str:
    if isinstance(value, (datetime, StrEnum)):
        return value.isoformat() if isinstance(value, datetime) else value.value
    raise TypeError(f"unsupported dashboard JSON type: {type(value).__name__}")


__all__ = [
    "DatasetReadinessReport",
    "FrameworkAreaReadiness",
    "FrameworkDataReadinessDashboard",
    "PhaseThreeCalibrationRunner",
    "PhaseThreeQuerySpec",
    "ProviderAccessStatus",
    "dashboard_json",
    "render_dashboard_markdown",
]
