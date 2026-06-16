from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import (
    AssetType,
    AvailabilityPrecision,
    DataTrustLevel,
    InvestmentAssessmentStatus,
    Market,
    SecurityStatus,
    SignalAction,
    SignalStage,
)
from tong_quant.domain.models import (
    FundamentalFact,
    Instrument,
    InstrumentStatus,
    Signal,
    UniverseMembership,
)


def test_sqlite_initializes_required_tables(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "test.sqlite3")
    store.initialize()

    assert store.table_count("instruments") == 0
    assert store.table_count("daily_bars") == 0
    assert store.table_count("trading_calendar") == 0
    assert store.table_count("fundamental_facts") == 0
    assert store.table_count("instrument_status_history") == 0
    assert store.table_count("universe_memberships") == 0
    assert store.table_count("corporate_actions") == 0
    assert store.table_count("ingestion_batches") == 0
    assert store.table_count("raw_dataset_fingerprints") == 0
    assert store.table_count("data_availability_warnings") == 0
    assert store.table_count("provider_limitations") == 0
    assert store.table_count("pit_readiness_assessments") == 0
    assert store.table_count("historical_replay_manifests") == 0
    assert store.table_count("historical_replay_samples") == 0
    assert store.table_count("signals") == 0
    assert store.table_count("screening_results") == 0
    assert store.table_count("research_queue") == 0
    assert store.table_count("screening_scorecards") == 0
    assert store.table_count("research_runs") == 0
    assert store.table_count("research_evidence") == 0
    assert store.table_count("research_assessments") == 0
    assert store.table_count("research_reports") == 0
    assert store.table_count("investment_assessments") == 0
    assert store.table_count("investment_scores") == 0
    assert store.table_count("schema_metadata") == 1
    assert store.schema_version() == "0.6.3"
    assert store.table_count("validation_runs") == 0
    assert store.table_count("validation_oos_usage") == 0
    assert store.table_count("validation_splits") == 0
    assert store.table_count("validation_observations") == 0
    assert store.table_count("validation_outcomes") == 0
    assert store.table_count("validation_outcome_definitions") == 0
    assert store.table_count("decision_journal") == 0
    assert store.table_count("validation_assessments") == 0
    assert store.table_count("validation_reports") == 0
    assert store.table_count("validation_factor_contributions") == 0
    assert store.table_count("validation_accuracy_history") == 0
    assert store.table_count("validation_integrity_checks") == 0
    assert store.table_count("validation_portfolio_risk") == 0


def test_investment_assessment_tables_store_status_and_score(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "test.sqlite3")
    store.initialize()
    now = datetime(2026, 1, 2, tzinfo=UTC)

    assessment_id = store.save_investment_assessment(
        report_id="report-1",
        instrument_id_value="china_a:equity:600000",
        status=InvestmentAssessmentStatus.LOW_CONFIDENCE,
        assessed_at=now,
        score=92,
        confidence=42,
        components=[
            {
                "name": "value",
                "score": 95,
                "confidence": 40,
                "weight": 1,
                "contribution": 95,
                "reasons": ["high growth but weak evidence"],
            }
        ],
        reasons=("High score but low confidence",),
        limitations=("Investment Score confidence is below threshold",),
        market_regime=None,
        model_version="investment-score-v0.6.1",
    )

    assert assessment_id
    assert store.table_count("investment_assessments") == 1
    assert store.table_count("investment_scores") == 1


def test_point_in_time_queries_require_aware_timestamp(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "test.sqlite3")
    store.initialize()

    try:
        store.trading_days(
            market="china_a",  # type: ignore[arg-type]
            start=datetime(2024, 1, 1, tzinfo=UTC).date(),
            end=datetime(2024, 1, 2, tzinfo=UTC).date(),
            as_of=datetime(2024, 1, 2),
        )
    except ValueError as error:
        assert "timezone-aware" in str(error)
    else:
        raise AssertionError("naive point-in-time query should fail")


def test_signal_and_screening_result_tables_accept_future_engine_outputs(
    tmp_path: Path,
) -> None:
    store = SQLiteStore(tmp_path / "test.sqlite3")
    store.initialize()
    now = datetime(2024, 1, 2, tzinfo=UTC)
    instrument = Instrument(
        "600000",
        Market.CHINA_A,
        "Example",
        available_at=now,
        source="test",
    )
    store.upsert_instruments([instrument])
    signal = Signal(
        source="screening.survival",
        stage=SignalStage.SCREENING,
        instrument=instrument,
        generated_at=now,
        effective_at=now,
        action=SignalAction.INCLUDE,
        strength=0.8,
        reasons=("passed",),
    )

    store.save_signal(signal)
    store.save_screening_result(
        instrument=instrument,
        dimension="survival",
        evaluated_at=now,
        available_at=now,
        passed=True,
        score=0.8,
        reasons=("passed",),
        features={"cash_flow_quality": 0.9},
        source="screening.survival",
        model_version="v0",
    )

    assert store.table_count("signals") == 1
    assert store.table_count("screening_results") == 1


def test_fundamental_facts_hide_future_revisions(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "test.sqlite3")
    store.initialize()
    instrument = Instrument(
        "600000",
        Market.CHINA_A,
        "Example",
        available_at=datetime(2024, 1, 2, tzinfo=UTC),
        source="test",
    )
    original = FundamentalFact(
        instrument=instrument,
        metric="revenue",
        period_end=date(2023, 12, 31),
        published_at=datetime(2024, 3, 20, tzinfo=UTC),
        available_at=datetime(2024, 3, 20, 18, tzinfo=UTC),
        value=Decimal("100"),
        currency="CNY",
        revision=0,
        source="test",
    )
    restated = FundamentalFact(
        instrument=instrument,
        metric="revenue",
        period_end=date(2023, 12, 31),
        published_at=datetime(2024, 4, 15, tzinfo=UTC),
        available_at=datetime(2024, 4, 15, 18, tzinfo=UTC),
        value=Decimal("80"),
        currency="CNY",
        revision=1,
        source="test",
    )
    store.upsert_instruments([instrument])
    store.upsert_fundamental_facts([original, restated])

    before_restatement = store.fundamental_facts(
        "600000",
        Market.CHINA_A,
        AssetType.EQUITY,
        "revenue",
        as_of=datetime(2024, 4, 1, tzinfo=UTC),
    )
    after_restatement = store.fundamental_facts(
        "600000",
        Market.CHINA_A,
        AssetType.EQUITY,
        "revenue",
        as_of=datetime(2024, 4, 16, tzinfo=UTC),
    )

    assert [fact.value for fact in before_restatement] == [Decimal("100")]
    assert [fact.value for fact in after_restatement] == [Decimal("80")]
    assert after_restatement[0].revision == 1

    history_before = store.fundamental_revision_history(
        "600000",
        Market.CHINA_A,
        AssetType.EQUITY,
        "revenue",
        as_of=datetime(2024, 4, 1, tzinfo=UTC),
    )
    history_after = store.fundamental_revision_history(
        "600000",
        Market.CHINA_A,
        AssetType.EQUITY,
        "revenue",
        as_of=datetime(2024, 4, 16, tzinfo=UTC),
    )
    assert [fact.revision for fact in history_before] == [0]
    assert [fact.revision for fact in history_after] == [0, 1]


def test_fundamental_raw_hash_conflict_requires_explicit_revision(
    tmp_path: Path,
) -> None:
    store = SQLiteStore(tmp_path / "test.sqlite3")
    store.initialize()
    instrument = Instrument(
        "600000",
        Market.CHINA_A,
        "Example",
        available_at=datetime(2024, 1, 2, tzinfo=UTC),
        source="test",
    )
    store.upsert_instruments([instrument])
    first = FundamentalFact(
        instrument=instrument,
        metric="revenue",
        period_end=date(2023, 12, 31),
        published_at=datetime(2024, 3, 20, tzinfo=UTC),
        available_at=datetime(2024, 3, 20, 18, tzinfo=UTC),
        value=Decimal("100"),
        source="test",
        raw_data_hash="a" * 64,
        availability_precision=AvailabilityPrecision.EXACT,
        trust_level=DataTrustLevel.HIGH,
    )
    conflicting = FundamentalFact(
        instrument=instrument,
        metric="revenue",
        period_end=date(2023, 12, 31),
        published_at=datetime(2024, 3, 20, tzinfo=UTC),
        available_at=datetime(2024, 3, 20, 18, tzinfo=UTC),
        value=Decimal("101"),
        source="test",
        raw_data_hash="b" * 64,
        availability_precision=AvailabilityPrecision.EXACT,
        trust_level=DataTrustLevel.HIGH,
    )

    store.upsert_fundamental_facts([first])

    try:
        store.upsert_fundamental_facts([conflicting])
    except ValueError as error:
        assert "raw hash conflict" in str(error)
    else:
        raise AssertionError("conflicting raw payload should require a new revision")


def test_status_raw_hash_conflict_requires_new_version(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "test.sqlite3")
    store.initialize()
    instrument = Instrument(
        "600000",
        Market.CHINA_A,
        "Example",
        available_at=datetime(2024, 1, 2, tzinfo=UTC),
        source="test",
    )
    store.upsert_instruments([instrument])
    first = InstrumentStatus(
        instrument,
        effective_from=date(2024, 1, 2),
        status=SecurityStatus.LISTED,
        is_tradable=True,
        available_at=datetime(2024, 1, 2, tzinfo=UTC),
        source="test",
        raw_data_hash="a" * 64,
        availability_precision=AvailabilityPrecision.EXACT,
        trust_level=DataTrustLevel.HIGH,
    )
    conflicting = InstrumentStatus(
        instrument,
        effective_from=date(2024, 1, 2),
        status=SecurityStatus.SUSPENDED,
        is_tradable=False,
        available_at=datetime(2024, 1, 2, tzinfo=UTC),
        source="test",
        raw_data_hash="b" * 64,
        availability_precision=AvailabilityPrecision.EXACT,
        trust_level=DataTrustLevel.HIGH,
    )

    store.upsert_instrument_statuses([first])

    try:
        store.upsert_instrument_statuses([conflicting])
    except ValueError as error:
        assert "raw hash conflict" in str(error)
    else:
        raise AssertionError("conflicting status payload should require a new version")


def test_universe_raw_hash_conflict_requires_new_version(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "test.sqlite3")
    store.initialize()
    instrument = Instrument(
        "600000",
        Market.CHINA_A,
        "Example",
        available_at=datetime(2024, 1, 2, tzinfo=UTC),
        source="test",
    )
    store.upsert_instruments([instrument])
    first = UniverseMembership(
        "china_a_all",
        instrument,
        effective_from=date(2024, 1, 2),
        available_at=datetime(2024, 1, 2, tzinfo=UTC),
        source="test",
        raw_data_hash="a" * 64,
        availability_precision=AvailabilityPrecision.EXACT,
        trust_level=DataTrustLevel.HIGH,
    )
    conflicting = UniverseMembership(
        "china_a_all",
        instrument,
        effective_from=date(2024, 1, 2),
        available_at=datetime(2024, 1, 2, tzinfo=UTC),
        source="test",
        raw_data_hash="b" * 64,
        availability_precision=AvailabilityPrecision.EXACT,
        trust_level=DataTrustLevel.HIGH,
    )

    store.upsert_universe_memberships([first])

    try:
        store.upsert_universe_memberships([conflicting])
    except ValueError as error:
        assert "raw hash conflict" in str(error)
    else:
        raise AssertionError("conflicting universe payload should require a new version")


def test_historical_universe_retains_delisted_members(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "test.sqlite3")
    store.initialize()
    known_at = datetime(2024, 1, 1, tzinfo=UTC)
    active = Instrument(
        "600000",
        Market.CHINA_A,
        "Active",
        available_at=known_at,
        source="test",
    )
    delisted = Instrument(
        "600001",
        Market.CHINA_A,
        "Later Delisted",
        delisting_date=date(2024, 4, 1),
        available_at=known_at,
        source="test",
    )
    store.upsert_instruments([active, delisted])
    store.upsert_universe_memberships(
        [
            UniverseMembership(
                "china_a_all",
                active,
                effective_from=date(2024, 1, 1),
                available_at=known_at,
                source="test",
            ),
            UniverseMembership(
                "china_a_all",
                delisted,
                effective_from=date(2024, 1, 1),
                effective_to=date(2024, 3, 31),
                available_at=known_at,
                source="test",
            ),
        ]
    )
    store.upsert_instrument_statuses(
        [
            InstrumentStatus(
                active,
                effective_from=date(2024, 1, 1),
                status=SecurityStatus.LISTED,
                is_tradable=True,
                available_at=known_at,
                source="test",
            ),
            InstrumentStatus(
                delisted,
                effective_from=date(2024, 1, 1),
                effective_to=date(2024, 3, 31),
                status=SecurityStatus.LISTED,
                is_tradable=True,
                available_at=known_at,
                source="test",
            ),
            InstrumentStatus(
                delisted,
                effective_from=date(2024, 4, 1),
                status=SecurityStatus.DELISTED,
                is_tradable=False,
                available_at=datetime(2024, 4, 1, tzinfo=UTC),
                source="test",
            ),
        ]
    )

    march = store.universe_as_of(
        "china_a_all",
        Market.CHINA_A,
        on_date=date(2024, 3, 15),
        as_of=datetime(2024, 3, 15, tzinfo=UTC),
        tradable_only=True,
    )
    april = store.universe_as_of(
        "china_a_all",
        Market.CHINA_A,
        on_date=date(2024, 4, 15),
        as_of=datetime(2024, 4, 15, tzinfo=UTC),
        tradable_only=True,
    )

    assert [instrument.symbol for instrument in march] == ["600000", "600001"]
    assert [instrument.symbol for instrument in april] == ["600000"]


def test_historical_status_hides_future_status_changes(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "test.sqlite3")
    store.initialize()
    instrument = Instrument(
        "600000",
        Market.CHINA_A,
        "Example",
        available_at=datetime(2024, 1, 1, tzinfo=UTC),
        source="test",
    )
    store.upsert_instruments([instrument])
    store.upsert_instrument_statuses(
        [
            InstrumentStatus(
                instrument,
                effective_from=date(2024, 1, 1),
                status=SecurityStatus.LISTED,
                is_tradable=True,
                available_at=datetime(2024, 1, 1, tzinfo=UTC),
                source="test",
            ),
            InstrumentStatus(
                instrument,
                effective_from=date(2024, 2, 1),
                status=SecurityStatus.SUSPENDED,
                is_tradable=False,
                available_at=datetime(2024, 2, 1, 9, tzinfo=UTC),
                source="test",
            ),
        ]
    )

    before_announcement = store.instrument_status(
        "600000",
        Market.CHINA_A,
        AssetType.EQUITY,
        on_date=date(2024, 2, 1),
        as_of=datetime(2024, 2, 1, 8, tzinfo=UTC),
    )
    after_announcement = store.instrument_status(
        "600000",
        Market.CHINA_A,
        AssetType.EQUITY,
        on_date=date(2024, 2, 1),
        as_of=datetime(2024, 2, 1, 10, tzinfo=UTC),
    )

    assert before_announcement is not None
    assert before_announcement.status is SecurityStatus.LISTED
    assert after_announcement is not None
    assert after_announcement.status is SecurityStatus.SUSPENDED


def test_universe_membership_uses_latest_visible_correction(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "test.sqlite3")
    store.initialize()
    instrument = Instrument(
        "600000",
        Market.CHINA_A,
        "Example",
        available_at=datetime(2024, 1, 1, tzinfo=UTC),
        source="test",
    )
    store.upsert_instruments([instrument])
    store.upsert_universe_memberships(
        [
            UniverseMembership(
                "china_a_all",
                instrument,
                effective_from=date(2024, 1, 1),
                available_at=datetime(2024, 1, 1, tzinfo=UTC),
                source="test",
            ),
            UniverseMembership(
                "china_a_all",
                instrument,
                effective_from=date(2024, 1, 1),
                effective_to=date(2024, 2, 29),
                available_at=datetime(2024, 3, 5, tzinfo=UTC),
                source="corrected",
            ),
        ]
    )

    before_correction = store.universe_as_of(
        "china_a_all",
        Market.CHINA_A,
        on_date=date(2024, 3, 1),
        as_of=datetime(2024, 3, 1, tzinfo=UTC),
    )
    after_correction = store.universe_as_of(
        "china_a_all",
        Market.CHINA_A,
        on_date=date(2024, 3, 1),
        as_of=datetime(2024, 3, 6, tzinfo=UTC),
    )

    assert [item.symbol for item in before_correction] == ["600000"]
    assert after_correction == []
