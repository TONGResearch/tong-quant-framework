from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import (
    AssetType,
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
    assert store.table_count("signals") == 0
    assert store.table_count("screening_results") == 0
    assert store.table_count("research_queue") == 0
    assert store.table_count("screening_scorecards") == 0
    assert store.table_count("research_runs") == 0
    assert store.table_count("research_evidence") == 0
    assert store.table_count("research_assessments") == 0
    assert store.table_count("research_reports") == 0
    assert store.table_count("schema_metadata") == 1
    assert store.schema_version() == "0.6.0"
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
