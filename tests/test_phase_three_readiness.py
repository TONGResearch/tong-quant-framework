import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tong_quant.data.calibration import (
    CalibrationDataset,
    CalibrationQuery,
    CalibrationRecord,
    MemoizedCalibrationSource,
    PhaseThreeCalibrationRunner,
    PhaseThreeQuerySpec,
    ProviderCalibrationCoordinator,
    ProviderCalibrationSnapshot,
    dashboard_json,
    render_dashboard_markdown,
)
from tong_quant.data.providers.tushare_capabilities import (
    CapabilityProbeContext,
    TushareCapabilityDetector,
    validate_tushare_environment,
)
from tong_quant.data.readiness_gap import (
    build_readiness_gap_report,
    gap_report_json,
    render_gap_markdown,
)
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import (
    AvailabilityPrecision,
    DataTrustLevel,
    PITReadinessClassification,
)

NOW = datetime(2026, 6, 20, tzinfo=UTC)


class _StaticSource:
    def __init__(self, source_id: str) -> None:
        self.source_id = source_id

    def calibration_snapshot(
        self, query: CalibrationQuery
    ) -> ProviderCalibrationSnapshot:
        return ProviderCalibrationSnapshot(
            provider=self.source_id,
            dataset=query.dataset.value,
            as_of=query.as_of,
            records=(CalibrationRecord("600000", {"listed": True}),),
            limitations=(f"{self.source_id} test limitation",),
        )


class _UnavailableSource:
    source_id = "unavailable"

    def calibration_snapshot(
        self, query: CalibrationQuery
    ) -> ProviderCalibrationSnapshot:
        del query
        raise RuntimeError("permission unavailable")


def _spec() -> PhaseThreeQuerySpec:
    return PhaseThreeQuerySpec(
        query=CalibrationQuery(CalibrationDataset.UNIVERSE_COVERAGE, NOW),
        framework_areas=(
            "Fundamentals",
            "Security Lifecycle",
            "Universe Membership",
            "Corporate Actions",
            "Market Regime Inputs",
            "Research Inputs",
            "Validation Inputs",
        ),
        availability_precision=AvailabilityPrecision.EXACT,
        primary_trust_level=DataTrustLevel.HIGH,
        historical_continuity_score=100,
        revision_score=100,
        expected_records=1,
    )


def test_phase_three_dashboard_with_two_consistent_providers(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "phase-three.sqlite3")
    store.initialize()
    dashboard = PhaseThreeCalibrationRunner(
        ProviderCalibrationCoordinator(store)
    ).run(
        _StaticSource("akshare"),
        _StaticSource("tushare"),
        (_spec(),),
    )

    report = dashboard.datasets[0]
    assert report.coverage_percent == 100
    assert report.provider_consistency_score == 100
    assert report.pit_readiness.classification is PITReadinessClassification.USABLE
    assert len(dashboard.framework_areas) == 7
    assert dashboard.overall_classification is PITReadinessClassification.CAUTION
    assert store.table_count("provider_consistency_reports") == 1

    markdown = render_dashboard_markdown(dashboard)
    payload = json.loads(dashboard_json(dashboard))
    assert "Framework Data Readiness Dashboard" in markdown
    assert payload["datasets"][0]["coverage_percent"] == 100


def test_phase_three_dashboard_preserves_unmeasurable_secondary(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "single-source.sqlite3")
    store.initialize()
    dashboard = PhaseThreeCalibrationRunner(
        ProviderCalibrationCoordinator(store)
    ).run(
        _StaticSource("akshare"),
        None,
        (_spec(),),
        secondary_unavailable_reason="TUSHARE_TOKEN is not configured",
    )

    report = dashboard.datasets[0]
    assert report.coverage_percent is None
    assert report.provider_consistency_score is None
    assert report.pit_readiness.classification is PITReadinessClassification.CAUTION
    assert "unmeasurable" in " ".join(report.pit_readiness.assumptions)
    assert "coverage is unmeasurable" in report.pit_readiness.warnings
    assert "N/A" in render_dashboard_markdown(dashboard)


def test_phase_three_dashboard_marks_primary_failure_unsuitable(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "primary-failure.sqlite3")
    store.initialize()
    dashboard = PhaseThreeCalibrationRunner(
        ProviderCalibrationCoordinator(store)
    ).run(
        _UnavailableSource(),
        None,
        (_spec(),),
    )

    report = dashboard.datasets[0]
    assert report.pit_readiness.classification is PITReadinessClassification.UNSUITABLE
    assert report.primary_records == 0
    assert "permission unavailable" in " ".join(report.known_limitations)


def test_gap_report_separates_current_readiness_from_perfect_dual_ceiling(
    tmp_path: Path,
) -> None:
    store = SQLiteStore(tmp_path / "gap-report.sqlite3")
    store.initialize()
    dashboard = PhaseThreeCalibrationRunner(
        ProviderCalibrationCoordinator(store)
    ).run(
        _StaticSource("akshare"),
        None,
        (_spec(),),
        secondary_unavailable_reason="TUSHARE_TOKEN is not configured",
    )
    environment = validate_tushare_environment({})
    capabilities = TushareCapabilityDetector(
        client=None, clock=lambda: NOW
    ).detect(
        environment,
        CapabilityProbeContext(
            as_of=NOW,
            ts_code="600000.SH",
            trade_date="20260619",
            period_end="20251231",
            start_date="20260601",
            end_date="20260620",
        ),
    )

    gap_report = build_readiness_gap_report(dashboard, capabilities)
    gap = gap_report.datasets[0]

    assert gap.current_classification is PITReadinessClassification.CAUTION
    assert (
        gap.best_case_after_dual_validation
        is PITReadinessClassification.USABLE
    )
    assert gap_report.historical_replay_ready is False
    assert "cross-provider coverage is unmeasured" in gap.missing_requirements
    assert "Perfect-dual ceiling" in render_gap_markdown(gap_report)
    assert json.loads(gap_report_json(gap_report))["historical_replay_ready"] is False


def test_memoized_calibration_source_caches_success_and_failure() -> None:
    success = _CountingSource(fail=False)
    cached_success = MemoizedCalibrationSource(success)
    query = CalibrationQuery(CalibrationDataset.UNIVERSE_COVERAGE, NOW)

    assert cached_success.calibration_snapshot(query) == cached_success.calibration_snapshot(
        query
    )
    assert success.calls == 1

    failure = _CountingSource(fail=True)
    cached_failure = MemoizedCalibrationSource(failure)
    for _ in range(2):
        with pytest.raises(RuntimeError, match="expected failure"):
            cached_failure.calibration_snapshot(query)
    assert failure.calls == 1


class _CountingSource:
    source_id = "counting"

    def __init__(self, *, fail: bool) -> None:
        self.fail = fail
        self.calls = 0

    def calibration_snapshot(
        self, query: CalibrationQuery
    ) -> ProviderCalibrationSnapshot:
        self.calls += 1
        if self.fail:
            raise RuntimeError("expected failure")
        return ProviderCalibrationSnapshot(
            provider=self.source_id,
            dataset=query.dataset.value,
            as_of=query.as_of,
            records=(CalibrationRecord("600000", {"listed": True}),),
        )
