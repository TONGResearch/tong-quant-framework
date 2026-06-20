from datetime import UTC, date, datetime
from pathlib import Path

from tong_quant.data.calibration import (
    CalibrationRecord,
    ProviderCalibrationEngine,
    ProviderCalibrationSnapshot,
)
from tong_quant.data.coverage import (
    FundamentalPublicationQualityInput,
    HistoricalCoverageEvaluator,
    SecurityTimelineQualityInput,
    UniverseMembershipQualityInput,
)
from tong_quant.data.models import FundamentalPublicationEvent, SecurityLifecycleEvent
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import (
    AssetType,
    AvailabilityPrecision,
    DataTrustLevel,
    LifecycleEventType,
    Market,
    PITReadinessClassification,
)
from tong_quant.domain.models import Instrument, UniverseMembership

NOW = datetime(2026, 1, 2, tzinfo=UTC)


def test_provider_calibration_is_deterministic_and_persistable(tmp_path: Path) -> None:
    primary = ProviderCalibrationSnapshot(
        provider="akshare",
        dataset="daily_bars",
        as_of=NOW,
        records=(
            CalibrationRecord("600000:2026-01-01", {"close": 10.0}),
            CalibrationRecord("000001:2026-01-01", {"close": 12.0}),
        ),
        limitations=("retrieval-time correction history unavailable",),
    )
    secondary = ProviderCalibrationSnapshot(
        provider="secondary-test",
        dataset="daily_bars",
        as_of=NOW,
        records=(
            CalibrationRecord("600000:2026-01-01", {"close": 10.0}),
            CalibrationRecord("000001:2026-01-01", {"close": 12.5}),
            CalibrationRecord("600001:2026-01-01", {"close": 8.0}),
        ),
    )
    engine = ProviderCalibrationEngine()

    first = engine.compare(primary, secondary, fields=("close",), compared_at=NOW)
    second = engine.compare(primary, secondary, fields=("close",), compared_at=NOW)

    assert first.comparison_hash == second.comparison_hash
    assert first.matched_count == 2
    assert first.primary_only_count == 0
    assert first.secondary_only_count == 1
    assert first.field_match_scores["close"] == 50
    assert first.consistency_score == 68

    store = SQLiteStore(tmp_path / "calibration.sqlite3")
    store.initialize()
    store.save_provider_consistency_report(first)
    stored = store.latest_provider_consistency(
        "daily_bars", "akshare", "secondary-test"
    )
    assert stored == first
    assert store.table_count("provider_consistency_reports") == 1


def test_security_timeline_partial_evidence_is_caution() -> None:
    instrument = _instrument("000001")
    events = (
        _lifecycle_event(
            instrument,
            LifecycleEventType.SUSPENSION_STARTED,
            date(2025, 1, 2),
        ),
        _lifecycle_event(
            instrument,
            LifecycleEventType.TRADING_RESUMED,
            date(2025, 1, 3),
        ),
    )

    assessment = HistoricalCoverageEvaluator().security_timeline(
        SecurityTimelineQualityInput(
            instrument_id="china_a:equity:000001",
            period_start=date(2025, 1, 1),
            period_end=date(2025, 12, 31),
            events=events,
            expected_event_types=(
                LifecycleEventType.ST_ENTER,
                LifecycleEventType.ST_EXIT,
                LifecycleEventType.SUSPENSION_STARTED,
                LifecycleEventType.TRADING_RESUMED,
            ),
        ),
        assessed_at=NOW,
    )

    assert assessment.classification is PITReadinessClassification.CAUTION
    assert "st_enter" in " ".join(assessment.warnings)


def test_universe_snapshot_history_does_not_claim_entry_exit_coverage() -> None:
    instrument = _instrument("600000")
    memberships = tuple(
        UniverseMembership(
            universe="index:000300",
            instrument=instrument,
            effective_from=snapshot_date,
            available_at=datetime.combine(snapshot_date, datetime.min.time(), tzinfo=UTC),
            source="akshare:index_stock_cons_csindex",
            availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
            trust_level=DataTrustLevel.MEDIUM,
        )
        for snapshot_date in (date(2025, 1, 1), date(2025, 4, 1))
    )

    assessment = HistoricalCoverageEvaluator().universe_membership(
        UniverseMembershipQualityInput(
            universe="index:000300",
            period_start=date(2025, 1, 1),
            period_end=date(2025, 6, 30),
            memberships=memberships,
            expected_snapshot_dates=(date(2025, 1, 1), date(2025, 4, 1)),
            has_entry_exit_history=False,
        ),
        assessed_at=NOW,
    )

    assert assessment.classification is PITReadinessClassification.CAUTION
    assert assessment.score_components["snapshot_coverage"] == 100
    assert assessment.score_components["entry_exit_history"] == 0


def test_exact_publication_and_revision_evidence_can_be_usable() -> None:
    instrument = _instrument("600000")
    publications = (
        _publication(instrument, date(2024, 12, 31), revision=0),
        _publication(instrument, date(2024, 12, 31), revision=1),
        _publication(instrument, date(2025, 3, 31), revision=0),
    )

    assessment = HistoricalCoverageEvaluator().fundamental_publication(
        FundamentalPublicationQualityInput(
            instrument_id="china_a:equity:600000",
            period_start=date(2024, 12, 31),
            period_end=date(2025, 3, 31),
            publications=publications,
            expected_period_ends=(date(2024, 12, 31), date(2025, 3, 31)),
        ),
        assessed_at=NOW,
    )

    assert assessment.classification is PITReadinessClassification.USABLE
    assert assessment.score_components["revision_observability"] == 100


def test_high_coverage_with_unknown_trust_is_not_usable() -> None:
    instrument = _instrument("600000")
    publication = FundamentalPublicationEvent(
        instrument=instrument,
        period_end=date(2024, 12, 31),
        report_type="annual",
        published_at=NOW,
        available_at=NOW,
        title="2024 annual report",
        revision=1,
        source="unverified-provider",
        availability_precision=AvailabilityPrecision.EXACT,
        trust_level=DataTrustLevel.UNKNOWN,
    )

    assessment = HistoricalCoverageEvaluator().fundamental_publication(
        FundamentalPublicationQualityInput(
            instrument_id="china_a:equity:600000",
            period_start=date(2024, 12, 31),
            period_end=date(2024, 12, 31),
            publications=(publication,),
            expected_period_ends=(date(2024, 12, 31),),
        ),
        assessed_at=NOW,
    )

    assert assessment.confidence_score >= 80
    assert assessment.classification is PITReadinessClassification.CAUTION
    assert "unknown trust" in " ".join(assessment.warnings)


def _instrument(symbol: str) -> Instrument:
    return Instrument(
        symbol=symbol,
        market=Market.CHINA_A,
        name=symbol,
        asset_type=AssetType.EQUITY,
        available_at=datetime(2025, 1, 1, tzinfo=UTC),
        source="test",
    )


def _lifecycle_event(
    instrument: Instrument,
    event_type: LifecycleEventType,
    effective_date: date,
) -> SecurityLifecycleEvent:
    return SecurityLifecycleEvent(
        instrument=instrument,
        event_type=event_type,
        effective_date=effective_date,
        available_at=NOW,
        source="akshare",
        availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
        trust_level=DataTrustLevel.MEDIUM,
    )


def _publication(
    instrument: Instrument,
    period_end: date,
    *,
    revision: int,
) -> FundamentalPublicationEvent:
    return FundamentalPublicationEvent(
        instrument=instrument,
        period_end=period_end,
        report_type="annual",
        published_at=NOW,
        available_at=NOW,
        title=f"{period_end.year} report revision {revision}",
        revision=revision,
        source="cninfo",
        availability_precision=AvailabilityPrecision.EXACT,
        trust_level=DataTrustLevel.HIGH,
    )
