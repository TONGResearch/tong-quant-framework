import json
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum

from tong_quant.data.calibration.models import CalibrationDataset
from tong_quant.data.calibration.readiness_report import (
    DatasetReadinessReport,
    FrameworkDataReadinessDashboard,
)
from tong_quant.data.providers.tushare_capabilities import (
    DatasetCapability,
    DatasetCapabilityStatus,
    TushareCapabilityReport,
)
from tong_quant.data.readiness import PITReadinessEvaluator, PITReadinessInput
from tong_quant.domain.enums import (
    AvailabilityPrecision,
    DataTrustLevel,
    PITReadinessClassification,
)
from tong_quant.domain.models import require_timezone
from tong_quant.version import DATA_READINESS_GAP_VERSION


@dataclass(frozen=True, slots=True)
class DatasetReadinessGap:
    dataset: CalibrationDataset
    current_classification: PITReadinessClassification
    best_case_after_dual_validation: PITReadinessClassification
    historical_replay_ready: bool
    future_paper_research_ready: bool
    missing_requirements: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DataReadinessGapReport:
    generated_at: datetime
    datasets: tuple[DatasetReadinessGap, ...]
    historical_replay_ready: bool
    future_paper_research_ready: bool
    critical_next_actions: tuple[str, ...]
    model_version: str = DATA_READINESS_GAP_VERSION

    def __post_init__(self) -> None:
        require_timezone(self.generated_at, "readiness gap report generated_at")


def build_readiness_gap_report(
    dashboard: FrameworkDataReadinessDashboard,
    capability_report: TushareCapabilityReport,
) -> DataReadinessGapReport:
    capabilities = {item.dataset: item for item in capability_report.datasets}
    gaps = tuple(
        _dataset_gap(report, capabilities[report.dataset])
        for report in dashboard.datasets
    )
    replay_ready = bool(gaps) and all(item.historical_replay_ready for item in gaps)
    paper_ready = bool(gaps) and all(item.future_paper_research_ready for item in gaps)
    actions = _critical_actions(gaps)
    return DataReadinessGapReport(
        generated_at=dashboard.generated_at,
        datasets=gaps,
        historical_replay_ready=replay_ready,
        future_paper_research_ready=paper_ready,
        critical_next_actions=actions,
    )


def render_gap_markdown(report: DataReadinessGapReport) -> str:
    lines = [
        "# PIT Readiness Gap Report",
        "",
        f"Generated at: {report.generated_at.isoformat()}",
        f"Historical Replay reliable: **{_yes_no(report.historical_replay_ready)}**",
        "Future Paper Trading research reliable: "
        f"**{_yes_no(report.future_paper_research_ready)}**",
        "",
        "`best_case_after_dual_validation` assumes 100% cross-provider coverage "
        "and consistency while preserving current trust, availability precision, "
        "revision, and continuity evidence. It is not an observed result.",
        "",
        "## Dataset Gaps",
        "",
        "| Dataset | Current | Perfect-dual ceiling | Missing requirements |",
        "|---|---|---|---|",
    ]
    for item in report.datasets:
        lines.append(
            f"| {item.dataset.value} | {item.current_classification.value} | "
            f"{item.best_case_after_dual_validation.value} | "
            f"{'<br>'.join(item.missing_requirements) or 'None'} |"
        )
    lines.extend(("", "## Critical Next Actions", ""))
    lines.extend(f"- {action}" for action in report.critical_next_actions)
    return "\n".join(lines).rstrip() + "\n"


def gap_report_json(report: DataReadinessGapReport) -> str:
    return json.dumps(asdict(report), default=_json_default, indent=2, sort_keys=True)


def _dataset_gap(
    report: DatasetReadinessReport,
    capability: DatasetCapability,
) -> DatasetReadinessGap:
    status = capability.status
    missing = []
    if status is not DatasetCapabilityStatus.AVAILABLE:
        missing.append(f"Tushare dataset capability is {status.value}")
    if report.coverage_percent is None:
        missing.append("cross-provider coverage is unmeasured")
    elif report.coverage_percent < 95:
        missing.append(f"cross-provider coverage is {report.coverage_percent:.2f}%, below 95%")
    if report.provider_consistency_score is None:
        missing.append("cross-provider consistency is unmeasured")
    elif report.provider_consistency_score < 80:
        missing.append(
            f"provider consistency is {report.provider_consistency_score:.2f}, below 80"
        )
    if report.trust_level in {DataTrustLevel.LOW, DataTrustLevel.UNKNOWN}:
        missing.append(f"trust level remains {report.trust_level.value}")
    if report.availability_precision in {
        AvailabilityPrecision.RETRIEVAL_TIME,
        AvailabilityPrecision.UNKNOWN,
    }:
        missing.append(
            f"availability precision remains {report.availability_precision.value}"
        )
    if report.historical_continuity_score < 80:
        missing.append(
            "historical continuity is "
            f"{report.historical_continuity_score:.2f}, below the 80 target"
        )
    if report.pit_readiness.missing_critical_fields:
        missing.append(
            "critical fields missing: "
            + ", ".join(report.pit_readiness.missing_critical_fields)
        )
    best_case = _best_case_classification(report)
    current_ready = (
        report.pit_readiness.classification is PITReadinessClassification.USABLE
    )
    return DatasetReadinessGap(
        dataset=report.dataset,
        current_classification=report.pit_readiness.classification,
        best_case_after_dual_validation=best_case,
        historical_replay_ready=current_ready,
        future_paper_research_ready=current_ready,
        missing_requirements=tuple(dict.fromkeys(missing)),
    )


def _best_case_classification(
    report: DatasetReadinessReport,
) -> PITReadinessClassification:
    components = report.pit_readiness.score_components
    assessment = PITReadinessEvaluator().evaluate(
        PITReadinessInput(
            dataset=report.dataset.value,
            expected_records=100,
            observed_records=100,
            trust_level=report.trust_level,
            availability_score=components.get("availability", 0),
            revision_score=components.get("revision", 0),
            continuity_score=components.get("continuity", 0),
            provider_consistency_score=100,
            provider_consistency_required=True,
        ),
        assessed_at=report.assessed_at,
    )
    return assessment.classification


def _critical_actions(
    gaps: tuple[DatasetReadinessGap, ...],
) -> tuple[str, ...]:
    actions = []
    if any(
        any("capability" in requirement for requirement in item.missing_requirements)
        for item in gaps
    ):
        actions.append(
            "Configure and validate TUSHARE_TOKEN permissions for every required endpoint"
        )
    if any(
        any("coverage" in requirement for requirement in item.missing_requirements)
        for item in gaps
    ):
        actions.append("Run date-aligned AKShare/Tushare comparisons across multiple periods")
    if any(
        any("continuity" in requirement for requirement in item.missing_requirements)
        for item in gaps
    ):
        actions.append(
            "Backfill dated history or collect forward snapshots until continuity is measurable"
        )
    if any(
        any("availability precision" in requirement for requirement in item.missing_requirements)
        for item in gaps
    ):
        actions.append(
            "Acquire announcement-time or effective-time evidence for retrieval-time datasets"
        )
    if any(
        item.best_case_after_dual_validation is not PITReadinessClassification.USABLE
        for item in gaps
    ):
        actions.append(
            "Do not treat dual-provider agreement alone as sufficient for Historical Replay"
        )
    return tuple(actions)


def _yes_no(value: bool) -> str:
    return "YES" if value else "NO"


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, StrEnum):
        return value.value
    raise TypeError(f"unsupported gap-report JSON type: {type(value).__name__}")


__all__ = [
    "DataReadinessGapReport",
    "DatasetReadinessGap",
    "build_readiness_gap_report",
    "gap_report_json",
    "render_gap_markdown",
]
